import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
 
# Make sure to import other scripts:
from gql_client import GraphQLClient
from methods import nan_handling
 
def main():
    st.title("Time Series Viewer")
 
    # Section for user inputs
    st.sidebar.header("Query Parameters")
    codes_input = st.sidebar.text_input("Time Series Codes (comma-separated)", value="GAS_METER_V2")

    # Date and time selection
    st.sidebar.subheader("Date and Time Selection")
    
    # Default dates (today and 7 days from today)
    today = datetime.now()
    next_week = today + timedelta(days=7)
    
    # Date pickers
    start_date = st.sidebar.date_input(
        "Start Date",
        value=today,
        min_value=today - timedelta(days=365),
        max_value=today + timedelta(days=365)
    )
    
    end_date = st.sidebar.date_input(
        "End Date",
        value=next_week,
        min_value=start_date,
        max_value=today + timedelta(days=365)
    )
    
    # Time selection
    start_time = st.sidebar.time_input("Start Time", value=datetime.strptime("00:00", "%H:%M").time(),step=timedelta(minutes=60))
    end_time = st.sidebar.time_input("End Time", value=datetime.strptime("23:00", "%H:%M").time(),step=timedelta(minutes=60))
    
    # Format dates in ISO8601
    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)
    
    # Convert to UTC and format as ISO8601
    utc = pytz.UTC
    start_iso = start_datetime.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_iso = end_datetime.astimezone(utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    # Display the formatted ISO8601 strings
    st.sidebar.text(f"Start: {start_iso}")
    st.sidebar.text(f"End: {end_iso}")
 
    # Button to trigger the query
    if st.sidebar.button("Fetch Data"):
        codes = [code.strip() for code in codes_input.split(",")]
 
        # Initialize your client
        client = GraphQLClient(
            url="http://gtw.core-tst.aks.e21/graphql/",
            schema="POWERNL",
            api_key="3C0262DE-027E-48E8-B8BB-397B4CB54CF8"
        )
 
        with st.spinner("Fetching data..."):
            response = client.fetch_time_series(
                codes=codes,
                start_period=start_iso,
                end_period=end_iso
            )
 
        if response:
            df = client.to_dataframe(response)
            if df is not None and not df.empty:
                st.success("Data fetched successfully!")
                # Display the DataFrame in a table
                st.dataframe(df)

                # Nan handling
                nan_method = st.selectbox("Choose method to handle nan values.",
                             ("forward-fill", "backward-fill", "mean", "median"))
                nan_handling(data=df, method=nan_method)
                # Display the updated df
                st.dataframe(df)

            else:
                st.warning("No data returned for given parameters.")
        else:
            st.error("Failed to retrieve data.")
 
if __name__ == "__main__":
    main()