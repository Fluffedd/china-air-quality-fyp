import streamlit as st
import pandas as pd
import plotly.express as px

from src.auth import require_login, render_auth_status_in_sidebar
from src.data_loader import create_master_if_missing
from src.utils import get_aqi_level
from src.ui_theme import apply_theme, render_page_header


st.set_page_config(page_title="健康建议与风险提示", layout="wide")
apply_theme()

require_login()
render_auth_status_in_sidebar()

render_page_header(
    "🩺 空气质量健康影响与建议",
    "结合当前与 2020-2025 历史风险，提供城市健康防护参考。",
)


AQI_TABLE = [
    {"range": "0–50", "name": "优", "desc": "空气质量令人满意，基本无空气污染。"},
    {"range": "51–100", "name": "良", "desc": "空气质量可接受，但个别极敏感人群应减少户外活动。"},
    {"range": "101–150", "name": "轻度污染", "desc": "敏感人群症状轻度加剧，应适当减少户外活动时间。"},
    {"range": "151–200", "name": "中度污染", "desc": "心肺疾病、老年人和儿童应减少外出，一般人群适当减少剧烈运动。"},
    {"range": "201–300", "name": "重度污染", "desc": "敏感人群应留在室内，一般人群减少户外停留时间。"},
    {"range": "300+", "name": "严重污染", "desc": "尽量避免外出，开启空气净化设备并佩戴防护口罩。"},
]


col_l, col_r = st.columns([2, 3])
with col_l:
    st.subheader("国家 AQI 分级标准（简化版）")
    st.table(
        pd.DataFrame(
            [
                {"AQI 范围": row["range"], "等级": row["name"], "健康影响": row["desc"]}
                for row in AQI_TABLE
            ]
        )
    )

with col_r:
    st.subheader("如何解读本系统中的 AQI？")
    st.markdown(
        """
        - **AQI 数值越高，空气越差。** 本系统使用与中国环境空气质量标准相近的分级。
        - **颜色编码**：绿色/黄色代表对大部分人群安全，橙色及以上需要逐步加强防护。
        - **地图与预测页中的色带** 与此表完全对应，便于直接判断风险等级。
        """
    )

st.markdown("---")
st.subheader("📍 当前高风险城市一览（基于最近一日数据）")

master = create_master_if_missing()
if master is None or master.empty:
    st.info("暂未找到 master_daily 历史数据，无法生成全国高风险列表。请先运行数据清理脚本。")
else:
    master["date"] = pd.to_datetime(master["date"], errors="coerce")
    master = master.dropna(subset=["date", "AQI"])
    latest_date = master["date"].max()
    latest_df = master[master["date"] == latest_date].copy()

    latest_df["等级"] = latest_df["AQI"].apply(get_aqi_level)
    latest_df = latest_df.sort_values("AQI", ascending=False)

    top_n = st.slider("显示前 N 个高风险城市", 5, 50, 15)
    st.caption(f"基于最近日期：{latest_date.strftime('%Y-%m-%d')}")

    cols = ["city", "AQI", "等级"]
    extra_cols = [c for c in ["PM2.5", "PM10", "SO2", "NO2", "O3"] if c in latest_df.columns]
    st.dataframe(
        latest_df[cols + extra_cols].head(top_n).reset_index(drop=True),
        use_container_width=True,
        height=380,
    )
    top_curr = latest_df[cols].head(10).copy()
    fig_curr = px.bar(
        top_curr.sort_values("AQI", ascending=True),
        x="AQI",
        y="city",
        orientation="h",
        color="AQI",
        color_continuous_scale=["#ffcc00", "#ff7e00", "#ff0000", "#7e0023"],
        title="当前高风险 Top 10 城市（最近一日）",
        height=380,
    )
    fig_curr.update_layout(coloraxis_showscale=False, yaxis_title="城市", xaxis_title="AQI")
    st.plotly_chart(fig_curr, use_container_width=True)

st.markdown("---")
st.subheader("📆 2020-2025 高风险城市总览（长期）")

if master is None or master.empty:
    st.info("暂无历史数据，无法生成 2020-2025 风险总览。")
else:
    hist = master.copy()
    hist["date"] = pd.to_datetime(hist["date"], errors="coerce")
    hist = hist.dropna(subset=["date", "AQI", "city"])
    hist = hist[hist["date"].dt.year.between(2020, 2025)]

    if hist.empty:
        st.info("当前数据中没有 2020-2025 年的记录。")
    else:
        risk_threshold = st.slider("高风险阈值（AQI）", 100, 300, 150, 10)
        min_days = st.slider("入榜最少高风险天数", 5, 120, 20, 5)

        city_stats = (
            hist.assign(is_risk=hist["AQI"] >= risk_threshold)
            .groupby("city", as_index=False)
            .agg(
                平均AQI=("AQI", "mean"),
                最高AQI=("AQI", "max"),
                高风险天数=("is_risk", "sum"),
                记录天数=("AQI", "count"),
            )
        )
        city_stats["高风险占比(%)"] = (city_stats["高风险天数"] / city_stats["记录天数"] * 100).round(1)
        city_stats = city_stats[city_stats["高风险天数"] >= min_days]
        city_stats = city_stats.sort_values(["高风险天数", "平均AQI"], ascending=False)

        if city_stats.empty:
            st.warning("当前阈值下没有城市满足入榜条件，请降低阈值或减少最少高风险天数。")
        else:
            top_k = st.slider("显示前 K 个高风险城市（长期）", 5, 30, 12)
            st.dataframe(
                city_stats.head(top_k).reset_index(drop=True),
                use_container_width=True,
                height=360,
            )

            fig_long = px.bar(
                city_stats.head(top_k).sort_values("高风险天数", ascending=True),
                x="高风险天数",
                y="city",
                orientation="h",
                color="高风险占比(%)",
                color_continuous_scale=["#ffe699", "#ffb347", "#ff6b6b", "#7e0023"],
                title=f"2020-2025 长期高风险城市 Top {top_k}",
                height=420,
            )
            fig_long.update_layout(yaxis_title="城市", xaxis_title="高风险天数", coloraxis_colorbar_title="高风险占比%")
            st.plotly_chart(fig_long, use_container_width=True)

            yearly = (
                hist.assign(year=hist["date"].dt.year, is_risk=hist["AQI"] >= risk_threshold)
                .groupby("year", as_index=False)
                .agg(
                    全国平均AQI=("AQI", "mean"),
                    高风险天占比=("is_risk", "mean"),
                )
            )
            yearly["高风险天占比"] = yearly["高风险天占比"] * 100
            y1, y2 = st.columns(2)
            with y1:
                fig_yearly_aqi = px.line(
                    yearly,
                    x="year",
                    y="全国平均AQI",
                    title="2020-2025 全国平均 AQI 变化",
                )
                fig_yearly_aqi.update_traces(mode="lines+markers")
                fig_yearly_aqi.update_layout(yaxis_title="AQI")
                st.plotly_chart(fig_yearly_aqi, use_container_width=True)
            with y2:
                fig_yearly_risk = px.line(
                    yearly,
                    x="year",
                    y="高风险天占比",
                    title="2020-2025 高风险天占比变化",
                )
                fig_yearly_risk.update_traces(mode="lines+markers")
                fig_yearly_risk.update_layout(yaxis_title="高风险天占比（%）")
                st.plotly_chart(fig_yearly_risk, use_container_width=True)
            st.caption("说明：高风险定义为 AQI >= 你设置的阈值，用于观察 2020-2025 的长期变化。")

st.markdown("---")
st.subheader("✅ 不同人群的防护建议")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**一般健康人群**")
    st.markdown(
        """
        - AQI ≤ 100：可正常户外活动  
        - 101–150：适度减少剧烈运动时间  
        - ≥ 151：尽量避免长时间剧烈户外运动
        """
    )

with c2:
    st.markdown("**儿童、老年人、孕妇**")
    st.markdown(
        """
        - AQI 51–100：缩短户外活动时长  
        - 101–200：建议在空气较好时段（早/晚）短时外出  
        - ≥ 201：建议以室内活动为主，并注意通风与净化
        """
    )

with c3:
    st.markdown("**心肺疾病 / 哮喘 / 过敏体质**")
    st.markdown(
        """
        - AQI 51–100：随身携带常用药物，避免高强度运动  
        - 101–150：减少外出，必要时佩戴防护口罩  
        - ≥ 151：建议留在室内，严格遵医嘱用药
        """
    )

st.markdown("---")
st.caption(
    "本页为一般性健康指导，不能替代医生的专业建议。实际防护措施请结合当地官方预警和个人身体状况。"
)

