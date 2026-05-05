# scripts/geo_builder.py
import pandas as pd
import json
import os

SRC_XLSX = r"D:\Downloads\FYP CHINA\data\_站点列表\站点列表-2020.12.06起.xlsx"
OUT_PATH = r"D:\Downloads\FYP CHINA\data\city_geo.json"

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

geo = {}

def safe_float(x):
    """将经纬度安全转换成 float，遇到 '-', ' ', None 自动跳过"""
    try:
        if pd.isna(x):
            return None
        x = str(x).strip()
        if x in ["", "-", "--", "—", "null", "None"]:
            return None
        return float(x)
    except:
        return None


# 优先读取 Excel
if os.path.exists(SRC_XLSX):
    print("读取 Excel 站点列表...")
    x = pd.read_excel(SRC_XLSX)

    for _, row in x.iterrows():
        city = str(row.get("城市") or row.get("监测点名称") or "").strip()

        lng = safe_float(row.get("经度"))
        lat = safe_float(row.get("纬度"))

        # 跳过无效记录
        if city and lng is not None and lat is not None:
            geo[city] = {"lng": lng, "lat": lat}

else:
    cleaned_dir = r"D:\Downloads\FYP CHINA\data\cleaned_cities"
    if os.path.exists(cleaned_dir):
        files = [f for f in os.listdir(cleaned_dir) if f.endswith(".csv")]
        for f in files:
            df = pd.read_csv(os.path.join(cleaned_dir, f), encoding="utf-8")

            if "经度" in df.columns and "纬度" in df.columns:

                for _, r in df.iterrows():
                    city = str(r.get("city") or r.get("监测点名称") or "").strip()

                    lng = safe_float(r.get("经度"))
                    lat = safe_float(r.get("纬度"))

                    if city and lng is not None and lat is not None:
                        geo[city] = {"lng": lng, "lat": lat}
                break


if not geo:
    print("⚠ 未找到有效经纬度，使用默认值")
    geo = {
        "北京": {"lng": 116.4074, "lat": 39.9042},
        "上海": {"lng": 121.4737, "lat": 31.2304},
        "广州": {"lng": 113.2644, "lat": 23.1291},
        "深圳": {"lng": 114.0579, "lat": 22.5431},
    }

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(geo, f, ensure_ascii=False, indent=2)

print("✅ 已生成:", OUT_PATH, "共城市:", len(geo))
