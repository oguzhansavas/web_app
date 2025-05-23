import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error

class LightGBMQuantileForecaster:
    def __init__(self, target_column, quantiles=[0.1, 0.5, 0.9], lags=[1, 24, 168]):
        self.target_column = target_column
        self.quantiles = quantiles
        self.models = {}
        self.lags = lags
        self.features = []


    def prepare_data(self, df):
        """Create a new dataframe with only target column and datetime index"""
        forecast_df = pd.DataFrame(index=df.index)
        forecast_df[self.target_column] = df[self.target_column]
        return forecast_df


    def create_features(self, df):
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        # Create time-based features
        df['hour'] = df.index.hour
        df['dayofweek'] = df.index.dayofweek
        df['month'] = df.index.month
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
        
        # Create lag features for target column
        for lag in self.lags:
            df[f'{self.target_column}_lag_{lag}'] = df[self.target_column].shift(lag)
        df[f'{self.target_column}_rolling_mean_24'] = df[self.target_column].shift(1).rolling(window=24).mean()
        
        return df


    def train(self, df, forecast_start):
        # Create new dataframe with only target column
        forecast_df = self.prepare_data(df)
        
        # Add features
        forecast_df = self.create_features(forecast_df)
        forecast_df.dropna(inplace=True)
        
        # Split data
        train_df = forecast_df[forecast_df.index < forecast_start]
        
        # Get all feature columns (excluding target column)
        self.features = [col for col in forecast_df.columns if col != self.target_column]

        for q in self.quantiles:
            params = {
                "objective": "quantile",
                "metric": "quantile",
                "alpha": q,
                "learning_rate": 0.05,
                "num_leaves": 31,
                "verbose": -1
            }
            lgb_train = lgb.Dataset(train_df[self.features], label=train_df['demand'])
            model = lgb.train(params, lgb_train, num_boost_round=200)
            self.models[q] = model


    def predict(self, df):
        df = self.create_features(df)
        df.dropna(inplace=True)
        predictions = {}
        for q, model in self.models.items():
            predictions[f'q{int(q*100)}'] = model.predict(df[self.features])
        df['forecast_p10'] = predictions.get('q10')
        df['forecast_p50'] = predictions.get('q50')
        df['forecast_p90'] = predictions.get('q90')
        return df


    def plot_forecast(self, df):
        # Optional function
        import matplotlib.pyplot as plt
        plt.figure(figsize=(15, 5))
        plt.plot(df.index, df["demand"], label="Actual", color="black")
        plt.plot(df.index, df["forecast_p50"], label="Forecast (Median)", color="blue")
        plt.fill_between(df.index, df["forecast_p10"], df["forecast_p90"], color="blue", alpha=0.3, label="80% PI")
        plt.legend()
        plt.title("Probabilistic Forecast")
        plt.show()
