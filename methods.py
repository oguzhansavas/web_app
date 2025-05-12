import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Methods:
    def __init__(self, data: pd.DataFrame):
        """
        Initialize the Methods class with a DataFrame.
        
        Args:
            data (pd.DataFrame): DataFrame to be processed.
        """
        if not isinstance(data, pd.DataFrame):
            logger.error("Provided data is not a valid DataFrame.")
            raise ValueError("Data must be a pandas DataFrame.")
        
        self.data = data


    def nan_handling(self, method='forward-fill'):
        """
        Handles NaN values in numerical columns based on the specified method.
        
        Args:
            data    (pd.DataFrame): DataFrame with potential NaN values.
            method  (str): Method to handle NaNs. Options:
                           'forward-fill', 'backward-fill', 'mean', 'median'

        Returns:
            pd.DataFrame: DataFrame with NaNs handled.
        """
        numeric_cols = self.data.select_dtypes(include='number').columns
        data = self.data.copy()

        for col in numeric_cols:
            if data[col].isnull().any():
                logger.info(f"Handling NaNs in column '{col}' using method '{method}'.")

                if method == 'forward-fill':
                    data[col] = data[col].fillna(method='ffill')
                elif method == 'backward-fill':
                    data[col] = data[col].fillna(method='bfill')
                elif method == 'mean':
                    data[col] = data[col].fillna(data[col].mean())
                elif method == 'median':
                    data[col] = data[col].fillna(data[col].median())
                else:
                    logger.error(f"Unsupported NaN handling method: {method}")
                    return None

        return data
