import pandas as pd
import numpy as np
import holidays
import lightgbm as lgb
    # def plot_forecast(self, df):
    #     # Optional function
    #     import matplotlib.pyplot as plt
    #     plt.figure(figsize=(15, 5))
    #     plt.plot(df.index, df["demand"], label="Actual", color="black")
    #     plt.plot(df.index, df["forecast_p50"], label="Forecast (Median)", color="blue")
    #     plt.fill_between(df.index, df["forecast_p10"], df["forecast_p90"], color="blue", alpha=0.3, label="80% PI")
    #     plt.legend()
    #     plt.title("Probabilistic Forecast")
    #     plt.show()

class LightGBMQuantileForecaster:
    def __init__(self, quantiles=[0.1, 0.5, 0.9], lags=[1, 24, 168]):
        self.quantiles = quantiles
        self.lags = lags
        self.models = {}
        self.feature_names = []

    def create_features(self, df, target_code):
        # Assumes df is indexed by datetime, columns are codes
        df_feat = df[[target_code]].copy()
        for lag in self.lags:
            df_feat[f"lag_{lag}"] = df_feat[target_code].shift(lag)
        df_feat["hour"] = df_feat.index.hour
        df_feat["dayofweek"] = df_feat.index.dayofweek
        df_feat["month"] = df_feat.index.month
        df_feat.dropna(inplace=True)
        return df_feat

    def train(self, df, target_code, forecast_start):
        df_feat = self.create_features(df, target_code)
        # Ensure forecast_start is timezone-aware (UTC) if df_feat.index is
        if df_feat.index.tz is not None and pd.Timestamp(forecast_start).tzinfo is None:
            forecast_start = pd.Timestamp(forecast_start).tz_localize('UTC')
        elif df_feat.index.tz is None and pd.Timestamp(forecast_start).tzinfo is not None:
            forecast_start = pd.Timestamp(forecast_start).tz_convert(None)
        else:
            forecast_start = pd.Timestamp(forecast_start)
        train_df = df_feat[df_feat.index < forecast_start]
        X = train_df.drop(columns=[target_code])
        y = train_df[target_code]
        self.feature_names = X.columns.tolist()
        for q in self.quantiles:
            params = {
                "objective": "quantile",
                "metric": "quantile",
                "alpha": q,
                "learning_rate": 0.05,
                "num_leaves": 31,
                "verbose": -1
            }
            lgb_train = lgb.Dataset(X, label=y)
            model = lgb.train(params, lgb_train, num_boost_round=100)
            self.models[q] = model

    def predict(self, df, target_code):
        df_feat = self.create_features(df, target_code)
        X = df_feat[self.feature_names]
        preds = {}
        for q, model in self.models.items():
            preds[f"q{int(q*100)}"] = model.predict(X)
        result = df_feat.copy()
        for k, v in preds.items():
            result[k] = v
        return result

# Example usage:
# df = client.to_dataframe(response)  # DataFrame with datetime index, columns as codes
# forecaster = SimpleLightGBMQuantileForecaster()
# forecaster.train(df, target_code="NOMINT_3515000000044_GSEGLTTF", forecast_start="2024-01-09T00:00:00Z")
# forecast_df = forecaster.predict(df, target_code="NOMINT_3515000000044_GSEGLTTF")
