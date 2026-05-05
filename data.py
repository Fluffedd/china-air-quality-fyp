from pathlib import Path
import sys
import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# 可直接运行的 Prophet 训练脚本
CITY = "北京"
TEST_RATIO = 0.2
MASTER_PATH = Path(r"D:\Downloads\FYP CHINA\data\tempo\master_daily.csv")

if not MASTER_PATH.exists():
    raise FileNotFoundError(f"未找到数据文件：{MASTER_PATH}")

df = pd.read_csv(MASTER_PATH)
required_cols = {"city", "date", "AQI"}
if not required_cols.issubset(df.columns):
    raise ValueError(f"数据缺少必要列：{required_cols}")

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["AQI"] = pd.to_numeric(df["AQI"], errors="coerce")
df = df.dropna(subset=["city", "date", "AQI"])

city_df = df[df["city"] == CITY].copy().sort_values("date")
if city_df.empty:
    raise ValueError(f"城市 {CITY} 不存在或无有效数据。")

# 同城市同日期多条记录时先聚合
city_df = city_df.groupby("date", as_index=False)["AQI"].mean()

split_idx = int(len(city_df) * (1 - TEST_RATIO))
train_df = city_df.iloc[:split_idx].copy()
test_df = city_df.iloc[split_idx:].copy()
if train_df.empty or test_df.empty:
    raise ValueError("训练集或测试集为空，请检查数据量或 TEST_RATIO。")

# Prophet 训练数据格式：ds / y
prophet_train = train_df.rename(columns={"date": "ds", "AQI": "y"})
prophet_test = test_df.rename(columns={"date": "ds", "AQI": "y"})

model = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False,
    changepoint_prior_scale=0.05,
)
model.fit(prophet_train)

future = model.make_future_dataframe(periods=len(prophet_test), freq="D", include_history=True)
forecast = model.predict(future)

prophet_pred = forecast["yhat"].iloc[-len(prophet_test):].values
prophet_true = prophet_test["y"].values

mae = mean_absolute_error(prophet_true, prophet_pred)
rmse = np.sqrt(mean_squared_error(prophet_true, prophet_pred))
r2 = r2_score(prophet_true, prophet_pred)

print("Prophet 模型训练完成。")
print(f"城市：{CITY}")
print(f"总样本：{len(city_df)} | 训练：{len(train_df)} | 测试：{len(test_df)}")
print(f"MAE: {mae:.3f}")
print(f"RMSE: {rmse:.3f}")
print(f"R2: {r2:.3f}")

# 基线模型：移动平均、线性回归（用于对比）
# 1）移动平均基线：用训练集最后 7 天均值预测测试集
ma_window = 7
ma_value = train_df["AQI"].tail(ma_window).mean()
ma_pred = np.full(shape=len(test_df), fill_value=ma_value)

# 2）线性回归基线
lr_train = train_df.copy()
lr_test = test_df.copy()

origin_date = city_df["date"].min()
lr_train["t"] = (lr_train["date"] - origin_date).dt.days
lr_test["t"] = (lr_test["date"] - origin_date).dt.days

lr = LinearRegression()
lr.fit(lr_train[["t"]], lr_train["AQI"])
lr_pred = lr.predict(lr_test[["t"]])

# 评估函数
def eval_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return mae, rmse, r2

rows = []
for name, pred in [
    ("Prophet", prophet_pred),
    ("移动平均（7天）", ma_pred),
    ("线性回归", lr_pred),
]:
    mae, rmse, r2 = eval_metrics(test_df["AQI"].values, pred)
    rows.append({"模型": name, "MAE": mae, "RMSE": rmse, "R²": r2})

metrics_df = pd.DataFrame(rows).sort_values("RMSE")
metrics_df = metrics_df.copy()
for c in ["MAE", "RMSE", "R²"]:
    metrics_df[c] = metrics_df[c].round(3)

print("\n=== 模型对比结果 ===")
print(metrics_df.to_string(index=False))

best_model = metrics_df.iloc[0]["模型"]
print("按 RMSE 最优模型：", best_model)

# 可选：保存结果，方便答辩留档
out_dir = Path(r"D:\Downloads\FYP CHINA\data\tempo\model_outputs")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / f"{CITY}_model_compare.csv"
metrics_df.to_csv(out_file, index=False, encoding="utf-8-sig")
print("模型对比结果已保存：", out_file)