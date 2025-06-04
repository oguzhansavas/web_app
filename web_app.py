import streamlit as st
import pandas as pd
from gql_client import GraphQLClient
<<<<<<< HEAD
from rest_client import RestClient
=======
>>>>>>> 183353e30ae445f1ffa0b3b239495cbef6e01eb3
from pages import time_series_viewer, forecasting_page, sidebar_query_params

st.set_page_config(layout="wide")

def main():
    # Sidebar logic moved to pages.py
    params = sidebar_query_params()
    codes_input = params["codes_input"]
    start_iso = params["start_iso"]
    end_iso = params["end_iso"]
    fetch = params["fetch"]

    if fetch:
        codes = [code.strip() for code in codes_input.split(",")]

        # client = GraphQLClient(
        #     url="http://gtw.core-tst.aks.e21/graphql/",
        #     schema="POWERNL",
        #     api_key="3C0262DE-027E-48E8-B8BB-397B4CB54CF8"
        # )

        client = RestClient(
            url="http://gtw.core-tst.aks.e21/time-series/api/v1.0",
            schema="powernl",
            api_key="3C0262DE-027E-48E8-B8BB-397B4CB54CF8"
        )

        with st.spinner("Fetching data..."):
            response = client.fetch_time_series(codes=codes, start_period=start_iso, end_period=end_iso)

        if response:
            df = client.to_dataframe(response)
            if df is not None and not df.empty:
                st.sidebar.success("Data fetched successfully!")
                st.session_state.original_df = df.copy()
                st.session_state.df = df.copy()
            else:
                st.sidebar.warning("No data returned for given parameters.")
        else:
            st.sidebar.error("Failed to retrieve data.")
    
    tab1, tab2 = st.tabs(["Time Series Viewer", "Forecasting"])
    
    with tab1:
        time_series_viewer()
    
    with tab2:
        forecasting_page()

if __name__ == "__main__":
    main()