# scripts/batch_forecast.py
import pandas as pd
import os
from prophet import Prophet
from tqdm import tqdm

DATA_DIR = r"D:\Downloads\FYP CHINA\data\daily_cities"
OUT_DIR = r"D:\Downloads\FYP CHINA\data\predictions"
os.makedirs(OUT_DIR, exist_ok=True)

# 合并 daily_cities（或从 master_daily.csv 读取）
files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
if not files:
    print("未找到 daily_cities 文件，请先生成 daily_cities")
    raise SystemExit(1)

dfs = []
for f in files:
    df = pd.read_csv(f, encoding="utf-8")
    dfs.append(df)
master = pd.concat(dfs, ignore_index=True)
master["date"] = pd.to_datetime(master["date"], errors="coerce")

cities = master["city"].unique()
print("城市数量:", len(cities))

for city in tqdm(cities):
    dfc = master[master["city"] == city].sort_values("date")
    if dfc.shape[0] < 60:
        # 数据太少，跳过
        print("跳过 (数据少于60):", city)
        continue
    ts = dfc[["date", "AQI"]].rename(columns={"date": "ds", "AQI": "y"}).dropna()
    m = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=True)
    try:
        m.fit(ts)
        future = m.make_future_dataframe(periods=30)
        forecast = m.predict(future)
        out = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]
        out.to_csv(os.path.join(OUT_DIR, f"{city}.csv"), index=False, encoding="utf-8-sig")
    except Exception as e:
        print("训练失败：", city, e)

print("全部预测完成，文件保存在:", OUT_DIR)
