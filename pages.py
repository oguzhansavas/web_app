import streamlit as st
import pandas as pd
from methods import Methods
from datetime import datetime, timedelta
import pytz
import tzlocal
from lgb_forecast import LightGBMQuantileForecaster 

def time_series_viewer():
    st.title("Time Series Viewer")
    
    # Main interface if data is available
    if "original_df" in st.session_state:
        original_df = st.session_state.original_df

        # Layout columns
        col1, col2 = st.columns([3, 3])

        with col1:
            # Show current DataFrame (will update on NaN method change)
            df = st.session_state.df
            st.subheader("DataFrame")
            st.dataframe(df, width=1000, height=500, use_container_width=True)

            # Nan handling below the DataFrame
            nan_method = st.selectbox("NaN Handling Method (optional):",
                                      ("None", "forward-fill", "backward-fill", "mean", "median"))

            # Always apply transformation to a fresh copy of the original
            if nan_method != "None":
                df_processor = Methods(data=original_df.copy())
                df = df_processor.nan_handling(method=nan_method)
            else:
                df = original_df.copy()

            st.session_state.df = df  # Update current df in session

            st.markdown("---")

        # Visualization options toggle
        show_viz = st.checkbox("Show Visualization Options", value=False)

        if show_viz:
            with col2:
                st.subheader("Visualization")
                numeric_columns = df.select_dtypes(include='number').columns.tolist()
                selected_columns = st.multiselect("Line Chart Columns", numeric_columns)

                if st.button("Create Line Chart"):
                    if selected_columns:
                        df_line_chart = df[selected_columns]
                        if df_line_chart.dropna(how="all").empty:
                            st.warning("Selected columns contain only NaN values.")
                        else:
                            st.line_chart(df_line_chart, height=400, use_container_width=True)
                    else:
                        st.warning("Please select at least one numeric column.")

def forecasting_page():
    st.title("Forecasting")
    
    if "original_df" not in st.session_state:
        st.warning("Please fetch data from the Time Series Viewer tab first.")
    else:
        df = st.session_state.get('df', st.session_state.original_df)
        
        if df.isna().any().any():
            st.warning("Please handle NaN values in the Time Series Viewer tab before proceeding with forecasting.")
        else:
            st.write("Please select which time series you would like to forecast.")
            target_column = st.selectbox("Select Time Series", df.columns.tolist())
            
            # Let user pick forecast start date
            min_date = df.index.min()
            max_date = df.index.max()
            min_forecast_start = min_date + pd.Timedelta(hours=168)
            if min_forecast_start > max_date:
                st.warning("Not enough data for forecasting (need at least 7 days of history).")
                return
            # Calculate forecastable period: start is the day after max_date, end is up to 7 days after max_date
            forecast_min = (min_date + pd.Timedelta(days=7)).to_pydatetime()
            forecast_max = (max_date + pd.Timedelta(days=7)).to_pydatetime()

            # Ensure default value is within bounds
            default_start = max(forecast_min.date(), min(forecast_min.date(), forecast_max.date()))
            default_end = max(default_start, min(forecast_max.date(), forecast_max.date()))

            forecast_start = st.date_input(
                "Select Forecast Start Date",
                value=default_start,
                min_value=forecast_min.date(),
                max_value=forecast_max.date()
            )
            forecast_end = st.date_input(
                "Select Forecast End Date",
                value=default_end,
                min_value=forecast_start,
                max_value=forecast_max.date()
            )
            # Combine with time if needed, or default to 00:00
            forecast_start_dt = pd.Timestamp.combine(forecast_start, pd.Timestamp("00:00").time())
            forecast_end_dt = pd.Timestamp.combine(forecast_end, pd.Timestamp("23:00").time())

            # Ensure timezone consistency
            if df.index.tz is not None:
                if forecast_start_dt.tzinfo is None:
                    forecast_start_dt = forecast_start_dt.tz_localize(df.index.tz)
                else:
                    forecast_start_dt = forecast_start_dt.tz_convert(df.index.tz)
                if forecast_end_dt.tzinfo is None:
                    forecast_end_dt = forecast_end_dt.tz_localize(df.index.tz)
                else:
                    forecast_end_dt = forecast_end_dt.tz_convert(df.index.tz)

            if st.button("Run Forecast"):
                forecaster = LightGBMQuantileForecaster()
                try:
                    # Train on all available data up to forecast_start_dt
                    forecaster.fit(df, target_column, forecast_start_dt)
                    # Predict for the entire DataFrame (including future, if appended)
                    df_pred = forecaster.create_features(df, target_column)
                    df_pred = df_pred.dropna()
                    for q in forecaster.quantiles:
                        df_pred[f"forecast_p{int(q*100)}"] = forecaster.models[q].predict(df_pred[forecaster.features])
                    # Show only the forecast period
                    forecast_df = df_pred[df_pred.index >= forecast_start_dt]
                    st.success("Forecast completed!")
                    fig = forecaster.plot_forecast_plotly(forecast_df, target_column, forecaster.quantiles)
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(forecast_df)
                except Exception as e:
                    st.error(f"Forecasting failed: {e}")

def sidebar_query_params():
    st.sidebar.header("Query Parameters")
    codes_input = st.sidebar.text_input("Time Series Codes (comma-separated)", value="NOMINT_3515000000044_GSEGLTTF")

    st.sidebar.subheader("Date and Time Selection")
    today = datetime.now()
    next_week = today + timedelta(days=7)

    start_date = st.sidebar.date_input("Start Date", value=today, min_value=today - timedelta(days=730), max_value=today + timedelta(days=730))
    end_date = st.sidebar.date_input("End Date", value=next_week, min_value=start_date, max_value=today + timedelta(days=365))

    start_time = st.sidebar.time_input("Start Time", value=datetime.strptime("00:00", "%H:%M").time(), step=timedelta(minutes=60))
    end_time = st.sidebar.time_input("End Time", value=datetime.strptime("23:00", "%H:%M").time(), step=timedelta(minutes=60))

    # Combine and localize to local timezone based on selected date, then convert to UTC
    local_tz = tzlocal.get_localzone()
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)

    start_datetime = start_datetime.replace(tzinfo=local_tz)
    end_datetime = end_datetime.replace(tzinfo=local_tz)

    start_datetime_utc = start_datetime.astimezone(pytz.utc)
    end_datetime_utc = end_datetime.astimezone(pytz.utc)

    start_iso = start_datetime_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end_datetime_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    st.sidebar.text(f"Start (UTC): {start_iso}")
    st.sidebar.text(f"End (UTC): {end_iso}")

    fetch = st.sidebar.button("Fetch Data")

    return {
        "codes_input": codes_input,
        "start_iso": start_iso,
        "end_iso": end_iso,
        "fetch": fetch
    }
