# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from src.auth import require_login, render_auth_status_in_sidebar
from src.data_loader import create_master_if_missing
from src.utils import get_aqi_level
from src.ui_theme import apply_theme, render_page_header

st.set_page_config(page_title="中国空气质量监测", layout="wide")
apply_theme()

require_login()
render_auth_status_in_sidebar()

render_page_header(
    "中国空气质量监测",
    "总览仪表盘 + 多页面：Realtime / History / Predict / Health",
)
st.sidebar.info("请在 .streamlit/secrets.toml 中配置 WAQI_TOKEN 或设置环境变量 WAQI_TOKEN。")

# ===========================
# 总览：全国 AQI 仪表盘
# ===========================
master = create_master_if_missing()

if master is None or master.empty:
    st.warning("未找到历史日数据（master_daily.csv）。请先运行数据清理脚本，或前往各功能页使用局部功能。")
    st.write("打开左侧页面导航：Realtime / History / Predict / Health")
else:
    master["date"] = pd.to_datetime(master["date"], errors="coerce")
    master = master.dropna(subset=["date", "AQI"])

    if master.empty:
        st.warning("历史数据缺少有效的日期或 AQI 列。")
        st.write("打开左侧页面导航：Realtime / History / Predict / Health")
    else:
        latest_date = master["date"].max()
        latest_df = master[master["date"] == latest_date].copy()

        avg_aqi = latest_df["AQI"].mean()
        best_row = latest_df.loc[latest_df["AQI"].idxmin()]
        worst_row = latest_df.loc[latest_df["AQI"].idxmax()]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("最新日期", latest_date.strftime("%Y-%m-%d"))
        col2.metric("全国平均 AQI", f"{avg_aqi:.1f}")
        col3.metric("最佳城市", f'{best_row["city"]} ({int(best_row["AQI"])})')
        col4.metric("最差城市", f'{worst_row["city"]} ({int(worst_row["AQI"])})')

        # 健康提示
        level = get_aqi_level(avg_aqi)
        st.markdown(f"**当前全国整体空气质量等级：{level}。**")

        if level in ["优", "良"]:
            st.info("适宜绝大多数人群户外活动，可安排运动或拍摄。")
        elif level in ["轻度污染", "中度污染"]:
            st.warning("对敏感人群（儿童、老年人、呼吸道疾病人群）可能有影响，建议减少长时间或剧烈户外运动。")
        else:
            st.error("空气质量较差，不建议长时间户外停留，必要时佩戴口罩并开启室内空气净化。")

        st.markdown("---")
        st.subheader("📈 全国平均 AQI 趋势（按日）")

        nat = (
            master.groupby("date", as_index=False)["AQI"]
            .mean()
            .rename(columns={"AQI": "avg_aqi"})
        )

        fig = px.line(
            nat,
            x="date",
            y="avg_aqi",
            labels={"date": "日期", "avg_aqi": "全国平均 AQI"},
            height=420,
        )
        fig.add_hrect(y0=0, y1=50, fillcolor="#00e400", opacity=0.1, line_width=0)
        fig.add_hrect(y0=51, y1=100, fillcolor="#ffff00", opacity=0.1, line_width=0)
        fig.add_hrect(y0=101, y1=150, fillcolor="#ff9900", opacity=0.08, line_width=0)
        fig.add_hrect(y0=151, y1=200, fillcolor="#ff0000", opacity=0.06, line_width=0)

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.caption("更多细节请切换到左侧导航的 Realtime / History / Predict / Health 页面。")
