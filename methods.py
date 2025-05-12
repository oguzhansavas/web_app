import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class methods():
    def __init__(self) -> None:
        pass


    def nan_handling(self, data, method):
        """
        NaN handling based on user preference.
        Args:
            data    (df) : Dataframe containing fetched time series data.
            method  (str): Prefered method to handle nans. 
        Returns:
            pd.DataFrame: DataFrame with all the nans handled.
        """
        if not data:
            logger.error("Invalid dataframe.")
            return None
        
        