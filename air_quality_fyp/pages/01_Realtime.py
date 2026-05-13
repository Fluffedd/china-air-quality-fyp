# pages/01_Realtime.py
"""
 Realtime 页面（放到 pages/01_Realtime.py）
功能亮点：
- 自动读取 city_geo.json / daily_cities / cleaned_cities 生成城市列表
- 优先使用 async batch fetch (src.api_client.batch_fetch)，若不存在则 fallback 到同步抓取
- 并发抓取（可调），进度条、错误报告、自动保存 CSV、地图与统计面板
- 美观的卡片式布局与交互（Plotly 地图 + 图表）
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from src.auth import require_login, render_auth_status_in_sidebar
from src.config import (
    ACTIVE_DATA_ROOT,
    CITY_GEO_FILE as CFG_CITY_GEO_FILE,
    CLEANED_DIR as CFG_CLEANED_DIR,
    DAILY_DIR as CFG_DAILY_DIR,
    REALTIME_DIR as CFG_REALTIME_DIR,
)
from src.ui_theme import apply_theme, render_page_header

st.set_page_config(page_title="Realtime AQI — Professional", layout="wide", initial_sidebar_state="expanded")
apply_theme()

require_login()
render_auth_status_in_sidebar()

# -----------------------------
# 常量 / 路径
# -----------------------------
CITY_GEO_FILE = Path(CFG_CITY_GEO_FILE)
DAILY_DIR = Path(CFG_DAILY_DIR)
CLEANED_DIR = Path(CFG_CLEANED_DIR)
REALTIME_DIR = Path(CFG_REALTIME_DIR)

REALTIME_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# 小工具函数
# -----------------------------
def safe_load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        st.error(f"读取 JSON 失败：{path}，错误：{e}")
        return {}

def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def save_realtime_csv(df: pd.DataFrame, prefix="china_realtime"):
    fn = REALTIME_DIR / f"{prefix}_{timestamp()}.csv"
    df.to_csv(fn, index=False, encoding="utf-8-sig")
    return fn

def get_aqi_level(aqi: Optional[float]) -> str:
    if aqi is None or pd.isna(aqi):
        return "无数据"
    aqi = float(aqi)
    if aqi <= 50: return "优"
    if aqi <= 100: return "良"
    if aqi <= 150: return "轻度污染"
    if aqi <= 200: return "中度污染"
    if aqi <= 300: return "重度污染"
    return "严重污染"

def get_aqi_color(aqi: Optional[float]) -> str:
    if aqi is None or pd.isna(aqi): return "#888888"
    aqi = float(aqi)
    if aqi <= 50: return "#00e400"
    if aqi <= 100: return "#ffff00"
    if aqi <= 150: return "#ff9900"
    if aqi <= 200: return "#ff0000"
    if aqi <= 300: return "#99004c"
    return "#7e0023"


def cached_data(fn):
    if hasattr(st, "cache_data"):
        return st.cache_data(show_spinner=False)(fn)
    return st.cache(allow_output_mutation=False)(fn)


AQI_LEVEL_ORDER = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染", "无数据"]
AQI_LEVEL_COLOR = {
    "优": "#00e400",
    "良": "#ffff00",
    "轻度污染": "#ff9900",
    "中度污染": "#ff0000",
    "重度污染": "#99004c",
    "严重污染": "#7e0023",
    "无数据": "#888888",
}

# -----------------------------
# 尝试导入异步 API client（优先）
# -----------------------------
use_async_client = False
batch_fetch = None
try:
    # 如果你的项目有 src/api_client.py 并暴露 batch_fetch 函数，会被优先使用（并发 aiohttp）
    from src.api_client import batch_fetch as async_batch_fetch  # type: ignore
    # adapt name
    batch_fetch = async_batch_fetch
    use_async_client = True
except Exception as e:
    # 如果导入失败， we'll fallback to sync requests below
    use_async_client = False

# -----------------------------
# 同步备选抓取（fallback）
# -----------------------------
if not use_async_client:
    import requests
    def _sync_get_city(city: str, token: Optional[str]=None, timeout=8):
        token = token or os.environ.get("WAQI_TOKEN") or ""
        url = f"https://api.waqi.info/feed/{city}/?token={token}"
        try:
            r = requests.get(url, timeout=timeout)
            js = r.json()
            if js.get("status") != "ok":
                return None
            d = js["data"]
            return {
                "city_en": city,
                "city_cn": d.get("city", {}).get("name", city),
                "aqi": (int(d.get("aqi")) if str(d.get("aqi")).isdigit() else None),
                "pm25": d.get("iaqi", {}).get("pm25", {}).get("v"),
                "pm10": d.get("iaqi", {}).get("pm10", {}).get("v"),
                "o3": d.get("iaqi", {}).get("o3", {}).get("v"),
                "no2": d.get("iaqi", {}).get("no2", {}).get("v"),
                "so2": d.get("iaqi", {}).get("so2", {}).get("v"),
                "co": d.get("iaqi", {}).get("co", {}).get("v"),
                "dominent": d.get("dominentpol"),
                "update_time": d.get("time", {}).get("s"),
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception:
            return None

    def batch_fetch(city_list: List[str], concurrency: int = 10, token: Optional[str] = None):
        """
        简单并发模拟：分批同步请求以避免一次性打爆 API。
        这是 fallback，如果你有 async client，会使用 async client（更快）。
        """
        results = []
        errors = {}
        batch_size = max(1, concurrency)
        token = token or os.environ.get("WAQI_TOKEN") or ""
        for i in range(0, len(city_list), batch_size):
            slice_ = city_list[i:i+batch_size]
            for c in slice_:
                r = _sync_get_city(c, token=token)
                if r:
                    results.append(r)
                else:
                    errors[c] = errors.get(c, 0) + 1
            time.sleep(0.12)  # small cooldown
        return results

# -----------------------------
# 数据准备（读取 city list）
# -----------------------------
render_page_header(
    "🇨🇳 AQI 实时监测",
    f"自动读取 `{ACTIVE_DATA_ROOT}` 历史目录（优先 tempo 数据），支持批量抓取、风险地图与榜单分析。",
)

# load geo
geo = safe_load_json(CITY_GEO_FILE)
if not geo:
    st.warning("⚠️ 未找到 city_geo.json 或文件为空。请先运行 scripts/geo_builder.py 生成 city_geo.json。 页面仍会尝试通过 daily/cleaned 中的城市名继续运行。")

# load city list — use city_geo.json as primary source (366 cities)
def load_city_list(geo_dict: dict) -> List[str]:
    cities = set()
    # PRIMARY: city_geo.json has the full 366-city list
    if geo_dict:
        cities.update(list(geo_dict.keys()))
    # EXTRA: also add any cities found in CSV files
    for search_dir in [DAILY_DIR, CLEANED_DIR]:
        if search_dir.exists():
            for f in search_dir.glob("*.csv"):
                try:
                    for enc in ["utf-8", "utf-8-sig"]:
                        try:
                            df = pd.read_csv(f, usecols=["city"], encoding=enc)
                            cities.update(df["city"].dropna().astype(str).unique().tolist())
                            break
                        except Exception:
                            continue
                except Exception:
                    continue
    # final fallback: hardcoded major cities from config
    if not cities:
        from src.config import CITY_CN_MAP
        cities.update(list(CITY_CN_MAP.values()))
    return sorted(cities)

all_cities = load_city_list(geo)
if not all_cities:
    st.error("无法找到任何城市（daily_cities / cleaned_cities / city_geo.json 均为空）。请先生成或放入数据，再刷新本页面。")
    st.stop()

# -----------------------------
# Sidebar 控件（UI）高级化
# -----------------------------
with st.sidebar:
    st.header("🔧 设置（Realtime）")

    st.markdown("**城市选择**（自动从 data/ 读取）")
    select_all = st.checkbox("选择全部城市（Select all）", value=True)
    if select_all:
        selected_cities = st.multiselect("选择城市（也可搜索选择）", options=all_cities, default=all_cities, key="city_multi")
    else:
        selected_cities = st.multiselect("选择城市（也可搜索选择）", options=all_cities, default=all_cities[:40], key="city_multi")

    st.markdown("---")
    st.markdown("**抓取选项**")
    concurrency = st.slider("并发数 / 批量大小（并发越高越快，API 限制请自己控制）", min_value=1, max_value=120, value=30)
    pause_after_fetch = st.checkbox("抓取后把结果自动保存到 data/realtime/ 目录", value=True)

    st.markdown("---")
    st.markdown("**自动刷新**")
    auto_refresh = st.checkbox("启用自动刷新（页面会定时重新抓取）", value=False)
    if auto_refresh:
        refresh_interval = st.number_input("刷新间隔（秒）", min_value=30, max_value=3600, value=300)
    else:
        refresh_interval = 0

    st.markdown("---")
    st.markdown("**Token / 调试**")
    waqi_token = st.text_input("WAQI API Token（为空会尝试读取环境变量 WAQI_TOKEN）", value="", type="password")

# -----------------------------
# 主操作区：抓取按钮
# -----------------------------
col_left, col_right = st.columns([2,1])


def run_fetch_job(
    selected_city_list: List[str],
    token_input: str,
    batch_size: int,
    save_after_fetch: bool,
    silent: bool = False,
) -> bool:
    if not selected_city_list:
        if not silent:
            st.warning("请先选择城市。")
        return False

    token_saved = token_input.strip() or os.environ.get("WAQI_TOKEN") or os.getenv("WAQI_TOKEN", "")
    if token_saved:
        os.environ["WAQI_TOKEN"] = token_saved

    start_time = time.time()
    try:
        # 优先使用支持 token 的签名；若第三方实现不支持则回退
        records = batch_fetch(selected_city_list, concurrency=batch_size, token=token_saved)
    except TypeError:
        records = batch_fetch(selected_city_list, concurrency=batch_size)
    except Exception as e:
        if not silent:
            st.error(f"抓取过程中出现严重错误：{e}")
        records = []

    duration = time.time() - start_time
    if records:
        df_fetched = pd.DataFrame(records)
        if "city_cn" not in df_fetched.columns and "city" in df_fetched.columns:
            df_fetched = df_fetched.rename(columns={"city": "city_cn"})
        df_fetched["aqi"] = pd.to_numeric(df_fetched.get("aqi"), errors="coerce")
        df_fetched["level"] = df_fetched["aqi"].apply(get_aqi_level)
        df_fetched["color"] = df_fetched["aqi"].apply(get_aqi_color)
        st.session_state["aqi_data"] = df_fetched
        st.session_state["last_fetch_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state["last_fetch_count"] = len(df_fetched)
        if not silent:
            st.success(f"抓取完成：成功获取 {len(df_fetched)} 条记录（耗时：{duration:.1f}s）")
        if save_after_fetch:
            fp = save_realtime_csv(df_fetched)
            if not silent:
                st.info(f"已保存：{fp}")
        return True

    if not silent:
        st.error("❌ 未获取到任何有效数据，请检查 Token、网络或 API 限制。")
    return False

with col_left:
    st.subheader("📡 抓取控制")
    st.write("选择城市后点击“开始抓取”，即可更新当前实时空气质量结果。")
    start = st.button("🚀 开始抓取所选城市", type="primary")

    if start:
        with st.spinner("正在抓取..."):
            run_fetch_job(
                selected_city_list=selected_cities,
                token_input=waqi_token,
                batch_size=concurrency,
                save_after_fetch=pause_after_fetch,
                silent=False,
            )

    if auto_refresh and not start:
        st.caption(
            f"自动刷新已启用：每 {int(refresh_interval)} 秒抓取一次（城市数：{len(selected_cities)}）。"
        )
        if selected_cities:
            with st.spinner("自动刷新抓取中..."):
                run_fetch_job(
                    selected_city_list=selected_cities,
                    token_input=waqi_token,
                    batch_size=concurrency,
                    save_after_fetch=pause_after_fetch,
                    silent=True,
                )
            st.info(
                f"自动刷新成功：{st.session_state.get('last_fetch_count', 0)} 条，时间 {st.session_state.get('last_fetch_time', '-')}"
            )
        else:
            st.warning("自动刷新已启用，但当前未选择城市。")

with col_right:
    st.subheader("🗒️ 数据导出")
    if 'aqi_data' in st.session_state and isinstance(st.session_state['aqi_data'], pd.DataFrame):
        df_loaded = st.session_state['aqi_data']
        st.write(f"当前会话数据：{len(df_loaded)} 条")
        st.download_button(
            "📥 下载当前数据（CSV）",
            data=df_loaded.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"realtime_aqi_{timestamp()}.csv",
            mime="text/csv",
        )
    else:
        st.info("当前没有抓取数据，或数据已过期。请先抓取。")

# -----------------------------
# Visualization area (Map + Stats)
# -----------------------------
st.markdown("---")
st.header("🗺️ 实时地图与讲解看板")

# Prepare df variable to display (either session or load latest file)
if 'aqi_data' in st.session_state and isinstance(st.session_state['aqi_data'], pd.DataFrame):
    df = st.session_state['aqi_data']
else:
    # try load the newest realtime file automatically if exists
    files = sorted(REALTIME_DIR.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    df = None
    if files:
        try:
            df = pd.read_csv(files[0], encoding="utf-8")
            st.info(f"加载最新保存文件：{files[0].name}")
            st.session_state['aqi_data'] = df
        except Exception as e:
            st.warning(f"尝试加载历史文件失败：{e}")
            df = None

# show warning if no df
if df is None or df.empty:
    st.warning("当前无实时数据。请在左侧点击“开始抓取所选城市”。")
    if auto_refresh and refresh_interval > 0:
        time.sleep(int(refresh_interval))
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()
    st.stop()

# add coordinates using geo (city name matching)
def attach_coords(df: pd.DataFrame, geo_map: dict) -> pd.DataFrame:
    lngs, lats = [], []
    for city in df['city_cn'].astype(str).tolist():
        entry = geo_map.get(city) or geo_map.get(city.strip())
        if not entry:
            # try partial match (some names may be '市'/'州' differences)
            entry = geo_map.get(city.replace("市", "").strip())
        if entry:
            lngs.append(entry.get("lng"))
            lats.append(entry.get("lat"))
        else:
            lngs.append(np.nan)
            lats.append(np.nan)
    df = df.copy()
    df['lng'] = lngs
    df['lat'] = lats
    return df

df = attach_coords(df, geo)

# drop missing coords for map plotting
df_map = df.dropna(subset=['lng', 'lat']).copy()
if df_map.empty:
    st.warning("当前数据中没有可用经纬度，无法显示地图。请检查 city_geo.json 是否覆盖这些城市。")
else:
    df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
    avg_aqi = df["aqi"].mean()
    avg_aqi_label = f"{avg_aqi:.1f}" if pd.notna(avg_aqi) else "N/A"
    level_now = get_aqi_level(avg_aqi)
    max_row = df.loc[df["aqi"].idxmax()] if df["aqi"].notna().any() else None
    min_row = df.loc[df["aqi"].idxmin()] if df["aqi"].notna().any() else None

    # Dashboard headline
    st.markdown(
        f"""
        <div style="padding:14px 16px;border-radius:12px;background:{AQI_LEVEL_COLOR.get(level_now, "#444")};
                    color:#111;font-weight:700;margin-bottom:10px;">
            当前全国综合风险等级：{level_now}（平均 AQI: {avg_aqi_label}）
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("监测城市数", len(df))
    c2.metric("平均 AQI", avg_aqi_label)
    c3.metric(
        "最高 AQI 城市",
        f"{int(max_row['aqi'])}" if max_row is not None else "N/A",
        max_row["city_cn"] if max_row is not None else "",
    )
    c4.metric(
        "最低 AQI 城市",
        f"{int(min_row['aqi'])}" if min_row is not None else "N/A",
        min_row["city_cn"] if min_row is not None else "",
    )

    level_counts = df["level"].fillna("无数据").value_counts().reindex(AQI_LEVEL_ORDER, fill_value=0)
    total_count = int(level_counts.sum()) if level_counts.sum() else 1
    risk_bar_html = "".join(
        [
            f'<div style="width:{(cnt / total_count) * 100:.2f}%;background:{AQI_LEVEL_COLOR[lbl]};height:18px;" title="{lbl}: {cnt}"></div>'
            for lbl, cnt in level_counts.items()
            if cnt > 0
        ]
    )
    st.markdown(
        f"""
        <div style="margin:6px 0 14px 0;">
            <div style="font-size:13px;color:#666;margin-bottom:6px;">等级分布带（鼠标悬停可看数量）</div>
            <div style="display:flex;border-radius:8px;overflow:hidden;border:1px solid #ddd;">{risk_bar_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    main_tab, data_tab = st.tabs(["🗺️ 实时地图与榜单", "🧪 污染物与明细"])

    with main_tab:
        left, right = st.columns([2, 1])
        with left:
            df_plot = df_map.copy()
            df_plot["aqi_size"] = df_plot["aqi"].apply(lambda v: max(5, min(32, ((v or 0) / 6) + 7)))
            fig_map = px.scatter_mapbox(
                df_plot,
                lat="lat",
                lon="lng",
                hover_name="city_cn",
                hover_data={"aqi": True, "level": True, "pm25": True, "pm10": True, "update_time": True, "lat": False, "lng": False},
                size="aqi_size",
                color="aqi",
                color_continuous_scale=[
                    [0, "#00e400"], [0.15, "#ffff00"], [0.3, "#ff9900"], [0.45, "#ff0000"], [0.6, "#99004c"], [1.0, "#7e0023"]
                ],
                size_max=32,
                zoom=3.2,
                height=600,
                title=f"全国城市实时 AQI 地图（更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）",
            )
            fig_map.update_layout(mapbox_style="carto-positron", margin={"r": 0, "t": 38, "l": 0, "b": 0})
            st.plotly_chart(fig_map, use_container_width=True)

        with right:
            st.markdown("#### 城市风险排行榜")
            rank_n = st.slider("显示前 N 个", 5, 30, 12)
            rank_cols = [c for c in ["city_cn", "aqi", "level", "dominent"] if c in df.columns]
            st.dataframe(df.sort_values("aqi", ascending=False)[rank_cols].head(rank_n), height=285, use_container_width=True)
            st.markdown("#### 低风险城市")
            st.dataframe(df.sort_values("aqi", ascending=True)[rank_cols].head(rank_n), height=285, use_container_width=True)

    with data_tab:
        c1, c2 = st.columns([1, 2])
        with c1:
            pie = px.pie(
                names=level_counts.index,
                values=level_counts.values,
                color=level_counts.index,
                color_discrete_map=AQI_LEVEL_COLOR,
                title="AQI 等级分布",
            )
            st.plotly_chart(pie, use_container_width=True)
        with c2:
            pollutant_cols = [c for c in ["pm25", "pm10", "o3", "no2", "so2", "co"] if c in df.columns]
            if pollutant_cols:
                melt = (
                    df[["city_cn"] + pollutant_cols]
                    .melt(id_vars="city_cn", var_name="pollutant", value_name="value")
                    .dropna()
                )
                bar = px.bar(
                    melt,
                    x="city_cn",
                    y="value",
                    color="pollutant",
                    barmode="group",
                    title="污染物浓度对比",
                    height=420,
                )
                st.plotly_chart(bar, use_container_width=True)
            else:
                st.info("无污染物数据可视化（数据缺少 pm25/pm10 等列）")

        st.markdown("#### 全量明细")
        show_cols = [c for c in ["city_cn", "aqi", "level", "dominent", "pm25", "pm10", "o3", "no2", "so2", "co", "update_time"] if c in df.columns]
        st.dataframe(df.sort_values("aqi", ascending=False)[show_cols], use_container_width=True, height=360)

st.markdown("---")
st.markdown(
    f"""
    <div style="text-align:center;font-size:12px;color:#666">
    数据存放目录：`{REALTIME_DIR}` &nbsp;&nbsp;|&nbsp;&nbsp; geo 文件：`{CITY_GEO_FILE}` <br/>
    </div>
    """, unsafe_allow_html=True
)

if auto_refresh and refresh_interval > 0:
    time.sleep(int(refresh_interval))
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()
