# Batch-train Prophet for all cities and save models + forecasts
import pandas as pd
import os
from src.prophet_model import train_prophet
from src.data_loader import create_master_if_missing
from src.config import MODEL_DIR, PREDICT_DIR


os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(PREDICT_DIR, exist_ok=True)


master = create_master_if_missing()
if master.empty:
    print('no master data')
    exit(1)


cities = master['city'].unique()
print('cities:', len(cities))
for c in cities:
    print('training', c)
    df = master[master['city'] == c].sort_values('date')
    try:
        m, forecast = train_prophet(df[['date','AQI']].rename(columns={'date':'date','AQI':'AQI'}), col='AQI', periods=30, model_name=c)
        forecast.to_csv(os.path.join(PREDICT_DIR, f"{c}_forecast.csv"), index=False)
    except Exception as e:
        print('failed', c, e)