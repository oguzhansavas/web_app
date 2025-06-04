import requests
import logging
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RestClient:
    def __init__(self, base_url: str, username: str = None, password: str = None, api_key: str = None):
        """
        Initialize the REST client.
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        if username and password:
            self.session.auth = (username, password)

    def fetch_time_series(self, codes, start_period, end_period):
        """
        Fetch time series data from the REST API.
        Args:
            codes (list): List of time series codes
            start_period (str): Start period in ISO format
            end_period (str): End period in ISO format
        Returns:
            dict: The time series data if successful, None otherwise
        """
        endpoint = f"{self.base_url}/time_series"
        params = {
            "codes": ",".join(codes),
            "start_period": start_period,
            "end_period": end_period
        }
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
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

    def execute_get(self, endpoint, params=None):
        """
        Execute a GET request to the REST API.
        Args:
            endpoint (str): The endpoint path (relative to base_url)
            params (dict, optional): Query parameters
        Returns:
            dict: The response data if successful, None otherwise
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error executing GET request: {e}")
            return None

# Example usecase
if __name__ == "__main__":
    client = RestClient(
        base_url="http://gtw.core-dev.aks.e21/masterdata/api/v1/core-dev/POWERNL",
        username="admin1",
        password="admin1"
    )

    response = client.fetch_time_series(
        codes=["GAS_METER_V2"],
        start_period="2024-10-26T22:00:00.000Z",
        end_period="2024-10-30T23:00:00.000Z"
    )

    if response:
        df = client.to_dataframe(response)
        print(df)
    else:
        print("Failed to retrieve data.")