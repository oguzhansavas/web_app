from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import logging
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphQLClient:
    def __init__(self, url: str, schema: str, api_key: str):
        """
        Initialize the GraphQL client.
        """
        self.url = url
        self.schema = schema
        self.api_key = api_key
        self.headers = {
            "e-schema": self.schema,
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Initialize transport
        self.transport = RequestsHTTPTransport(
            url=self.url,
            headers=self.headers
        )
        
        # Initialize client
        self.client = Client(transport=self.transport, fetch_schema_from_transport=True)


    def fetch_time_series(self, codes, start_period, end_period):
        """ 
        Fetch time series data.
        Args:
            codes (list): List of time series codes
            start_period (str): Start period in ISO format
            end_period (str): End period in ISO format
        Returns:
            dict: The time series data if successful, None otherwise
        """
        # Define GraphQL query
        query = gql("""
            query timeSeries($codes: [String!]!, $startPeriod: DateTime!, $endPeriod: DateTime!) {
                timeSeries(
                    codes: $codes
                    startPeriod: $startPeriod
                    endPeriod: $endPeriod
                ) {
                    code
                    type
                    version
                    interval
                    unit
                    points {
                        time
                        value
                    }
                }
            }
        """)
        
        # Define parameters
        params = {
            "codes": codes,
            "startPeriod": start_period,
            "endPeriod": end_period
        }
        
        try:
            # Execute the query safely using a context manager
            with Client(transport=self.transport, fetch_schema_from_transport=False) as session_client:
                response = session_client.execute(query, variable_values=params)
            return response
        except Exception as e:
            logger.error(f"Error fetching time series data: {e}")
            return None


    def to_dataframe(self, data):
        """
        Convert fetched time series data into a pandas DataFrame.
        Args:
            data (dict): Time series data fetched from the API.
        Returns:
            pd.DataFrame: A DataFrame with timestamps as index and values as columns.
        """
        if not data or "timeSeries" not in data:
            logger.error("Invalid or empty data received.")
            return None

        records = []
        for series in data["timeSeries"]:
            code = series["code"]
            for point in series["points"]:
                records.append({
                    "time": point["time"],
                    "value": point["value"],
                    "code": code
                })
        
        df = pd.DataFrame(records)
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        return df.pivot(columns="code", values="value")


    def execute_query(self, query_string, variables=None):
        """
        Execute GraphQL query.
        Args:
            query_string (str): The GraphQL query string
            variables (dict, optional): Variables for the query
        Returns:
            dict: The query response if successful, None otherwise
        """
        try:
            query = gql(query_string)
            with Client(transport=self.transport, fetch_schema_from_transport=False) as session_client:
                response = session_client.execute(query, variable_values=variables)
            return response
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return None


# Example usecase
if __name__ == "__main__":

    client = GraphQLClient(
        url="http://gtw.core-tst.aks.e21/graphql/",
        schema="POWERNL",
        api_key="3C0262DE-027E-48E8-B8BB-397B4CB54CF8"
    )
    
    response = client.fetch_time_series(
        codes=["NOMINT_3515000000044_GSEGLTTF"],
        start_period="2024-01-06T00:00:00.000Z",
        end_period="2024-01-09T23:00:00.000Z"
    )
    
    if response:
        df = client.to_dataframe(response)
        print(df)
    else:
        print("Failed to retrieve data.")