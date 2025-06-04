import streamlit as st
import pandas as pd
from methods import Methods
from datetime import datetime, timedelta
import pytz

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
        # Get the current dataframe (with or without NaN handling)
        df = st.session_state.get('df', st.session_state.original_df)
        
        # Check if there are any NaN values
        if df.isna().any().any():
            st.warning("Please handle NaN values in the Time Series Viewer tab before proceeding with forecasting.")
        else:
            st.write("Please select which time series you would like to forecast.")
            st.selectbox("Select Time Series", df.columns.tolist())

def sidebar_query_params():
    st.sidebar.header("Query Parameters")
    codes_input = st.sidebar.text_input("Time Series Codes (comma-separated)", value="GAS_METER_V2")

    st.sidebar.subheader("Date and Time Selection")
    today = datetime.now()
    next_week = today + timedelta(days=7)

    start_date = st.sidebar.date_input("Start Date", value=today, min_value=today - timedelta(days=730), max_value=today + timedelta(days=730))
    end_date = st.sidebar.date_input("End Date", value=next_week, min_value=start_date, max_value=today + timedelta(days=365))

    start_time = st.sidebar.time_input("Start Time", value=datetime.strptime("00:00", "%H:%M").time(), step=timedelta(minutes=60))
    end_time = st.sidebar.time_input("End Time", value=datetime.strptime("23:00", "%H:%M").time(), step=timedelta(minutes=60))

    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)

    utc = pytz.UTC
    start_iso = start_datetime.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_iso = end_datetime.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    st.sidebar.text(f"Start: {start_iso}")
    st.sidebar.text(f"End: {end_iso}")

    fetch = st.sidebar.button("Fetch Data")

    return {
        "codes_input": codes_input,
        "start_iso": start_iso,
        "end_iso": end_iso,
        "fetch": fetch
    }