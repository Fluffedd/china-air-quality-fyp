import pandas as pd
from prophet import Prophet
import os
from .config import MODEL_DIR
import joblib




def train_prophet(ts_df, col='AQI', periods=30, model_name=None):
# ts_df: columns ['date', col]
    df = ts_df[['date', col]].rename(columns={'date':'ds', col:'y'}).dropna()
    if df.empty:
        raise ValueError('empty timeseries')
    m = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True)
    m.fit(df)
    future = m.make_future_dataframe(periods=periods)
    forecast = m.predict(future)
    # save model if requested
    if model_name:
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(m, os.path.join(MODEL_DIR, f"{model_name}.joblib"))
        forecast.to_csv(os.path.join(MODEL_DIR, f"{model_name}_forecast.csv"), index=False)
    return m, forecast