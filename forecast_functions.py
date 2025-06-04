import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

class LinearRegressionForecaster:
    def __init__(self, lags=[1, 24, 168]):
        self.lags = lags
        self.model = None
        self.feature_names = []

    def create_features(self, df, target_code):
        # Assumes df is indexed by datetime, columns are codes
        df_feat = df[[target_code]].copy()
        for lag in self.lags:
            df_feat[f"lag_{lag}"] = df_feat[target_code].shift(lag)
        df_feat["hour"] = df_feat.index.hour
        df_feat["dayofweek"] = df_feat.index.dayofweek
        df_feat["month"] = df_feat.index.month
        df_feat = df_feat.dropna()  # Drop rows with NaNs caused by shifting
        return df_feat

    def train(self, df, target_code, forecast_start):
        df_feat = self.create_features(df, target_code)
        forecast_start = pd.to_datetime(forecast_start)
        if df_feat.index.tz is not None and forecast_start.tzinfo is None:
            forecast_start = forecast_start.tz_localize(df_feat.index.tz)
        elif df_feat.index.tz is not None and forecast_start.tzinfo != df_feat.index.tz:
            forecast_start = forecast_start.tz_convert(df_feat.index.tz)
        train_df = df_feat[df_feat.index < forecast_start]
        if train_df.empty:
            raise ValueError("Training set is empty. Please select a forecast start date that leaves enough history for training.")
        X = train_df.drop(columns=[target_code])
        y = train_df[target_code]
        self.feature_names = X.columns.tolist()
        self.model = LinearRegression()
        self.model.fit(X, y)

    def predict(self, df, target_code):
        df_feat = self.create_features(df, target_code)
        X = df_feat[self.feature_names]
        preds = self.model.predict(X)
        result = df_feat.copy()
        result["prediction"] = preds
        return result

    def forecast(self, df, target_code, forecast_start, forecast_end):
        """
        Forecast values from forecast_start to forecast_end (inclusive).
        Returns a DataFrame with predictions for each step.
        """
        df_feat = self.create_features(df, target_code)
        # Ensure forecast_start and forecast_end are Timestamps with correct tz
        forecast_start = pd.to_datetime(forecast_start)
        forecast_end = pd.to_datetime(forecast_end)
        if df_feat.index.tz is not None:
            if forecast_start.tzinfo is None:
                forecast_start = forecast_start.tz_localize(df_feat.index.tz)
            else:
                forecast_start = forecast_start.tz_convert(df_feat.index.tz)
            if forecast_end.tzinfo is None:
                forecast_end = forecast_end.tz_localize(df_feat.index.tz)
            else:
                forecast_end = forecast_end.tz_convert(df_feat.index.tz)

        # Prepare a copy of the original df to append predictions
        df_extended = df.copy()
        predictions = []

        current_time = forecast_start
        while current_time <= forecast_end:
            # Create features for the current time
            features = {}
            for lag in self.lags:
                lag_time = current_time - pd.Timedelta(hours=lag)
                if lag_time in df_extended.index:
                    features[f"lag_{lag}"] = df_extended.loc[lag_time, target_code]
                else:
                    features[f"lag_{lag}"] = np.nan
            features["hour"] = current_time.hour
            features["dayofweek"] = current_time.dayofweek
            features["month"] = current_time.month

            X_pred = pd.DataFrame([features], index=[current_time])
            if X_pred.isnull().any(axis=1).iloc[0]:
                # Not enough history to predict
                pred = np.nan
            else:
                X_pred = X_pred[self.feature_names]
                pred = self.model.predict(X_pred)[0]

            predictions.append({"time": current_time, "prediction": pred})

            # Add prediction to df_extended for next lags
            df_extended.loc[current_time, target_code] = pred

            # Move to next hour (or your data's frequency)
            current_time += pd.Timedelta(hours=1)

        forecast_df = pd.DataFrame(predictions).set_index("time")
        return forecast_df

if __name__ == "__main__":
    from gql_client import GraphQLClient
    from methods import Methods

    # --- Fetch data using your GraphQLClient ---
    client = GraphQLClient(
        url="http://gtw.core-tst.aks.e21/graphql/",
        schema="POWERNL",
        api_key="3C0262DE-027E-48E8-B8BB-397B4CB54CF8"
    )

    response = client.fetch_time_series(
        codes=["GAS_METER_V2"],
        start_period="2025-03-01T00:00:00.000Z",
        end_period="2025-03-07T23:00:00.000Z"
    )

    if response:
        df = client.to_dataframe(response)
        print("Fetched DataFrame:")
        print(df.head())

        # --- Handle NaNs for debugging only ---
        df_debug = Methods(df).nan_handling(method='mean')
        print("DataFrame after NaN handling (mean):")
        print(df_debug.head())

        # --- Forecasting ---
        target_code = df_debug.columns[0]  # or specify your code
        forecast_start = df_debug.index.max()  # or set a custom forecast start

        # Check if enough data remains after NaN handling
        if df_debug.empty or df_debug[target_code].isnull().all():
            print("No data available for forecasting after NaN handling. Exiting.")
        else:
            forecaster = LinearRegressionForecaster()
            try:
                forecaster.train(df_debug, target_code, forecast_start)
                forecast_df = forecaster.predict(df_debug, target_code)
                print("Forecast results (last 10 rows):")
                print(forecast_df.tail(10))
            except Exception as e:
                print(f"Forecasting failed: {e}")
    else:
        print("Failed to retrieve data.")



