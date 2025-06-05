import pandas as pd
import numpy as np
import lightgbm as lgb
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

class LightGBMQuantileForecaster:
    def __init__(self, quantiles=[0.1, 0.5, 0.9], lags=[1, 24, 168]):
        self.quantiles = quantiles
        self.lags = lags
        self.models = {}
        self.features = []
        self.target = None

    def create_features(self, df, target_code):
        df = df[[target_code]].copy()
        df['hour'] = df.index.hour
        df['dayofweek'] = df.index.dayofweek
        df['month'] = df.index.month
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
        for lag in self.lags:
            df[f'lag_{lag}'] = df[target_code].shift(lag)
        df['rolling_mean_24'] = df[target_code].shift(1).rolling(window=24).mean()
        df['rolling_std_24'] = df[target_code].shift(1).rolling(window=24).std()
        return df

    def fit(self, df, target_code, forecast_start):

        self.target = target_code
        df = self.create_features(df, target_code)
        df = df.dropna()
        train = df[df.index < forecast_start]
        self.features = [col for col in df.columns if col != target_code]

        # Simple hyperparameter grid
        param_grid = {
            "num_leaves": [15, 31],
            "learning_rate": [0.01, 0.05],
            "min_data_in_leaf": [10, 20]
        }

        for q in self.quantiles:
            best_mae = float("inf")
            best_params = {}
            X_train, X_val, y_train, y_val = train_test_split(
                train[self.features], train[target_code], test_size=0.2, random_state=42
            )
            for num_leaves in param_grid["num_leaves"]:
                for lr in param_grid["learning_rate"]:
                    for min_data in param_grid["min_data_in_leaf"]:
                        params = {
                            "objective": "quantile",
                            "metric": "quantile",
                            "alpha": q,
                            "boosting_type": "gbdt",
                            "learning_rate": lr,
                            "num_leaves": num_leaves,
                            "min_data_in_leaf": min_data,
                            "verbose": -1
                        }
                        lgb_train = lgb.Dataset(X_train, label=y_train)
                        lgb_val = lgb.Dataset(X_val, label=y_val, reference=lgb_train)
                        model = lgb.train(
                            params,
                            lgb_train,
                            num_boost_round=200,
                            valid_sets=[lgb_val]
                        )
                        preds = model.predict(X_val)
                        mae = mean_absolute_error(y_val, preds)
                        if mae < best_mae:
                            best_mae = mae
                            best_params = params.copy()
                            best_model = model

            # Retrain on full train set with best params
            lgb_train_full = lgb.Dataset(train[self.features], label=train[target_code])
            final_model = lgb.train(
                best_params,
                lgb_train_full,
                num_boost_round=best_model.best_iteration or 200
            )
            self.models[q] = final_model

    def predict(self, df, target_code):
        df_feat = self.create_features(df, target_code)
        df_feat = df_feat.dropna()
        for q in self.quantiles:
            df_feat[f"forecast_p{int(q*100)}"] = self.models[q].predict(df_feat[self.features])
        return df_feat

    def plot_forecast_plotly(self, df, target_col, quantiles):
        low_q, median_q, high_q = quantiles
        lower = f'forecast_p{int(low_q * 100):02d}'
        median = f'forecast_p{int(median_q * 100):02d}'
        upper = f'forecast_p{int(high_q * 100):02d}'

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df.index, y=df[upper],
            mode='lines',
            line=dict(width=0),
            name=f'P{int(high_q*100)}',
            showlegend=False
        ))

        fig.add_trace(go.Scatter(
            x=df.index, y=df[lower],
            fill='tonexty',
            fillcolor='rgba(0,100,250,0.2)',
            line=dict(width=0),
            name=f'{int((high_q - low_q)*100)}% Interval'
        ))

        fig.add_trace(go.Scatter(
            x=df.index, y=df[median],
            mode='lines',
            line=dict(color='cyan', width=2),
            name='Median Forecast'
        ))

        fig.add_trace(go.Scatter(
            x=df.index, y=df[target_col],
            mode='lines',
            line=dict(color='green', dash='dash'),
            name='Actual'
        ))

        fig.update_layout(title="Forecast with Quantile Interval",
                        xaxis_title="Time", yaxis_title=target_col)
        return fig


if __name__ == "__main__":
    df = pd.read_csv("df_for_debug.csv", parse_dates=["timestamp"])
    df.set_index("timestamp", inplace=True)
    forecast_start = '2024-04-22'
    forecaster = LightGBMQuantileForecaster()
    forecaster.fit(df, "your_target_column", forecast_start)
    df_pred = forecaster.predict(df, "your_target_column")
    forecaster.plot(df_pred, forecast_start)
