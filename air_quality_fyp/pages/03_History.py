# -----------------------------
# 兼容 numpy
# -----------------------------
import numpy as np

np.bool = bool

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from statsmodels.tsa.seasonal import STL
from pathlib import Path

from src.auth import require_login, render_auth_status_in_sidebar
from src.config import ACTIVE_DATA_ROOT, DAILY_DIR as CFG_DAILY_DIR
from src.ui_theme import apply_theme, render_page_header

st.set_page_config(page_title="历史数据分析", layout="wide")
apply_theme()

require_login()
render_auth_status_in_sidebar()

render_page_header(
    "📊 城市空气质量历史分析",
    "支持趋势、季节性、城市对比与污染物相关性分析，聚焦长期变化。",
)

DATA_DIR = Path(CFG_DAILY_DIR)
city_files = sorted(DATA_DIR.glob("*.csv"))
cities = [f.stem for f in city_files]

if not cities:
    st.error(f"未找到日数据目录：{DATA_DIR}（当前数据根：{ACTIVE_DATA_ROOT}）")
    st.stop()


def get_cache_data_decorator():
    # 兼容不同版本 Streamlit（旧版没有 st.cache_data）
    if hasattr(st, "cache_data"):
        return st.cache_data
    return st.cache


cache_data = get_cache_data_decorator()


@cache_data(show_spinner=False)
def load_city_data(city_name: str) -> pd.DataFrame:
    file_path = DATA_DIR / f"{city_name}.csv"
    df0 = pd.read_csv(file_path, parse_dates=["date"])
    return df0.sort_values("date")


def aqi_level_name(aqi: float) -> str:
    if aqi <= 50:
        return "优"
    if aqi <= 100:
        return "良"
    if aqi <= 150:
        return "轻度污染"
    if aqi <= 200:
        return "中度污染"
    if aqi <= 300:
        return "重度污染"
    return "严重污染"


city = st.selectbox("选择城市", cities)
df = load_city_data(city)

# -----------------------------
# 时间筛选
# -----------------------------
min_date = df["date"].min()
max_date = df["date"].max()

start_date, end_date = st.date_input(
    "选择时间范围",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date,
)

df = df.loc[
    (df["date"] >= pd.to_datetime(start_date))
    & (df["date"] <= pd.to_datetime(end_date))
].copy()

if df.empty:
    st.error("当前时间范围内没有数据，请换一个时间段。")
    st.stop()

if "AQI" not in df.columns:
    st.error("数据缺少 `AQI` 列，无法进行历史分析。")
    st.stop()

# -----------------------------
# 派生字段（星期/月份/季度）
# -----------------------------
df["year"] = df["date"].dt.year
df["month"] = df["date"].dt.month
df["dayofyear"] = df["date"].dt.dayofyear

weekday_labels = {
    0: "周一",
    1: "周二",
    2: "周三",
    3: "周四",
    4: "周五",
    5: "周六",
    6: "周日",
}
df["weekday_idx"] = df["date"].dt.weekday
df["weekday"] = df["weekday_idx"].map(weekday_labels)

df["quarter_num"] = df["date"].dt.quarter
df["quarter"] = "Q" + df["quarter_num"].astype(str)

# -----------------------------
# KPI 统计
# -----------------------------
col1, col2, col3, col4 = st.columns(4)
avg_aqi = df["AQI"].mean()
max_row = df.loc[df["AQI"].idxmax()]
min_row = df.loc[df["AQI"].idxmin()]
trend_change = df["AQI"].iloc[-1] - df["AQI"].iloc[0]

col1.metric("平均 AQI", f"{avg_aqi:.1f}")
col2.metric(
    "最高 AQI",
    f'{int(max_row["AQI"])} ({max_row["date"].strftime("%Y-%m-%d")})',
)
col3.metric(
    "最低 AQI",
    f'{int(min_row["AQI"])} ({min_row["date"].strftime("%Y-%m-%d")})',
)
col4.metric("期间变化", f"{trend_change:+.1f}")
col4.caption(f"末值等级：{aqi_level_name(float(df['AQI'].iloc[-1]))}")

risk_days = int((df["AQI"] >= 100).sum())
heavy_days = int((df["AQI"] >= 150).sum())
st.info(
    f"讲解重点：在当前时间范围内，共 {len(df)} 天；AQI≥100 有 {risk_days} 天，AQI≥150 有 {heavy_days} 天。"
)

st.markdown("---")


def _safe_period_for_stl(n: int) -> int:
    # STL 需要足够长的序列来稳定估计季节周期。
    base = 365
    if n < 730:
        # 兜底：数据跨度短时，把周期缩小到可运行区间
        base = max(14, int(n / 2))
    return int(base)


tab_trend, tab_heatmap, tab_stl, tab_season, tab_multicity, tab_pollutants = st.tabs(
    [
        "📈 趋势与均线",
        "📅 月度热力",
        "📈 STL 分解（更易懂）",
        "🗓️ 星期 / 季度 / 月份",
        "🌍 不同城市 AQI 对比",
        "🧪 污染物对比（可选）",
    ]
)

# -----------------------------
# 趋势图 + 移动平均
# -----------------------------
with tab_trend:
    df_plot = df.copy()
    df_plot["MA7"] = df_plot["AQI"].rolling(7).mean()
    df_plot["MA30"] = df_plot["AQI"].rolling(30).mean()
    max_idx = df_plot["AQI"].idxmax()
    min_idx = df_plot["AQI"].idxmin()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot["date"], y=df_plot["AQI"], name="AQI", line=dict(color="#444")))
    fig.add_trace(
        go.Scatter(
            x=df_plot["date"],
            y=df_plot["MA7"],
            name="7日均线",
            line=dict(color="#ff9900", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot["date"],
            y=df_plot["MA30"],
            name="30日均线",
            line=dict(color="#0072ff", width=2),
        )
    )
    fig.add_hline(y=100, line_dash="dot", line_color="#ff9900", annotation_text="AQI=100（轻度风险起点）")
    fig.add_hline(y=150, line_dash="dot", line_color="#ff0000", annotation_text="AQI=150（中度污染起点）")
    fig.add_trace(
        go.Scatter(
            x=[df_plot.loc[max_idx, "date"]],
            y=[df_plot.loc[max_idx, "AQI"]],
            mode="markers+text",
            marker=dict(size=10, color="#d62728"),
            text=[f'峰值 {df_plot.loc[max_idx, "AQI"]:.0f}'],
            textposition="top center",
            name="峰值",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[df_plot.loc[min_idx, "date"]],
            y=[df_plot.loc[min_idx, "AQI"]],
            mode="markers+text",
            marker=dict(size=9, color="#2ca02c"),
            text=[f'谷值 {df_plot.loc[min_idx, "AQI"]:.0f}'],
            textposition="bottom center",
            name="谷值",
        )
    )
    fig.update_layout(
        height=520,
        template="plotly_white",
        title=f"{city}：AQI 趋势分析",
        xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.06)", zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        f"解读：峰值出现在 {df_plot.loc[max_idx, 'date'].strftime('%Y-%m-%d')}，谷值出现在 {df_plot.loc[min_idx, 'date'].strftime('%Y-%m-%d')}。"
    )

# -----------------------------
# 月度平均热力图
# -----------------------------
with tab_heatmap:
    heat_df = df.groupby(["year", "month"])["AQI"].mean().reset_index()
    pivot = heat_df.pivot(index="year", columns="month", values="AQI")

    heatmap = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale=[
                [0.0, "green"],
                [0.25, "yellow"],
                [0.5, "orange"],
                [0.75, "red"],
                [1.0, "purple"],
            ],
            colorbar=dict(title="月均 AQI"),
        )
    )
    heatmap.update_layout(
        template="plotly_white",
        xaxis_title="月份",
        yaxis_title="年份",
        height=520,
    )
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            heatmap.add_annotation(
                x=pivot.columns[j],
                y=pivot.index[i],
                text="-" if pd.isna(pivot.values[i][j]) else f"{pivot.values[i][j]:.0f}",
                showarrow=False,
                font=dict(color="black"),
            )
    st.plotly_chart(heatmap, use_container_width=True)
    if not heat_df.empty:
        worst_month = heat_df.loc[heat_df["AQI"].idxmax()]
        best_month = heat_df.loc[heat_df["AQI"].idxmin()]
        st.caption(
            f"解读：最差月份是 {int(worst_month['year'])}年{int(worst_month['month'])}月（均值 {worst_month['AQI']:.1f}）；"
            f"最佳月份是 {int(best_month['year'])}年{int(best_month['month'])}月（均值 {best_month['AQI']:.1f}）。"
        )

# -----------------------------
# STL 分解（更易懂）
# -----------------------------
with tab_stl:
    st.subheader("STL = 趋势（Trend） + 季节性（Seasonal） + 残差（Residual）")
    st.markdown(
        """
        你可以把它理解为：
        - **趋势**：长期缓慢变化（例如整体变好/变差）
        - **季节性**：周期规律（例如一年内某些月份更容易高污染）
        - **残差**：剩下的“非规律波动”（天气突变、临时排放等）
        """
    )

    n = len(df)
    period = _safe_period_for_stl(n)
    if period != 365:
        st.info(f"当前数据跨度较短，STL 周期已自动调整为 `period={period}` 以保证可运行。")

    try:
        stl = STL(df.set_index("date")["AQI"], period=period)
        result = stl.fit()
    except Exception as e:
        st.error(f"STL 分解失败：{e}")
        st.stop()

    trend = result.trend
    seasonal = result.seasonal
    resid = result.resid

    stl_tabs = st.tabs(["趋势 Trend", "季节性 Seasonal", "残差 Residual", "拼回对比"])

    with stl_tabs[0]:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend.index, y=trend, name="Trend", line=dict(color="#3333aa", width=2)))
        fig.update_layout(
            template="plotly_white",
            height=360,
            yaxis_title="Trend（相对 AQI）",
        )
        st.plotly_chart(fig, use_container_width=True)

    with stl_tabs[1]:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=seasonal.index,
                y=seasonal,
                name="Seasonal",
                line=dict(color="#cc3366", width=2),
            )
        )
        fig.update_layout(
            template="plotly_white",
            height=360,
            yaxis_title="Seasonal（季节项）",
        )
        st.plotly_chart(fig, use_container_width=True)

        amp = float(seasonal.abs().mean())
        st.caption(f"季节项平均幅度（越大季节性越明显）：{amp:.2f}")

        df_sf = df.copy()
        df_sf["year"] = df_sf["date"].dt.year
        df_sf["dayofyear"] = df_sf["date"].dt.dayofyear

        # 更直观的“多点图”：观察一年中的季节规律
        doy_mean = (
            df_sf.groupby("dayofyear")["AQI"].mean().reset_index().sort_values("dayofyear")
        )
        scatter_fig = go.Figure()
        scatter_fig.add_trace(
            go.Scatter(
                x=df_sf["dayofyear"],
                y=df_sf["AQI"],
                mode="markers",
                name="样本点",
                marker=dict(size=4, opacity=0.25, color="#444"),
            )
        )
        scatter_fig.add_trace(
            go.Scatter(
                x=doy_mean["dayofyear"],
                y=doy_mean["AQI"],
                mode="lines",
                name="多年均值",
                line=dict(color="#FF4B4B", width=3),
            )
        )
        scatter_fig.update_layout(
            template="plotly_white",
            height=360,
            xaxis_title="一年中的第几天（Day of Year）",
            yaxis_title="AQI",
        )
        st.plotly_chart(scatter_fig, use_container_width=True)

    with stl_tabs[2]:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=resid.index,
                y=resid,
                name="Residual",
                line=dict(color="#999999", width=2),
            )
        )
        fig.update_layout(
            template="plotly_white",
            height=360,
            yaxis_title="Residual（非规律波动）",
        )
        st.plotly_chart(fig, use_container_width=True)

    with stl_tabs[3]:
        reconstructed = trend + seasonal
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["AQI"].values,
                name="原始 AQI",
                line=dict(color="#444", width=1),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=reconstructed.index,
                y=reconstructed.values,
                name="Trend + Seasonal（拼回）",
                line=dict(color="#FF4B4B", width=3),
            )
        )
        fig.update_layout(
            template="plotly_white",
            height=420,
            yaxis_title="AQI",
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 星期 / 季度 / 月份分析
# -----------------------------
with tab_season:
    season_tabs = st.tabs(["🗓️ 星期分析", "⏳ 按季度分析", "📅 按月份分析", "多点图看季节性"])

    # 星期分析
    with season_tabs[0]:
        weekday_avg = df.groupby("weekday_idx", as_index=False)["AQI"].mean()
        weekday_avg["weekday"] = weekday_avg["weekday_idx"].map(weekday_labels)
        weekday_avg = weekday_avg.sort_values("weekday_idx")

        fig = go.Figure(
            go.Bar(
                x=weekday_avg["weekday"],
                y=weekday_avg["AQI"],
                marker_color="#ff9900",
            )
        )
        fig.update_layout(
            template="plotly_white",
            height=380,
            xaxis_title="星期",
            yaxis_title="平均 AQI",
        )
        st.plotly_chart(fig, use_container_width=True)
        worst_day = weekday_avg.loc[weekday_avg["AQI"].idxmax()]
        best_day = weekday_avg.loc[weekday_avg["AQI"].idxmin()]
        st.caption(
            f"解读：周内最高为 {worst_day['weekday']}（{worst_day['AQI']:.1f}），最低为 {best_day['weekday']}（{best_day['AQI']:.1f}）。"
        )

    # 季度分析
    with season_tabs[1]:
        quarter_avg = df.groupby("quarter_num", as_index=False)["AQI"].mean()
        quarter_avg["quarter"] = "Q" + quarter_avg["quarter_num"].astype(str)
        quarter_avg = quarter_avg.sort_values("quarter_num")

        fig = go.Figure(
            go.Bar(
                x=quarter_avg["quarter"],
                y=quarter_avg["AQI"],
                marker_color="#0072ff",
            )
        )
        fig.update_layout(
            template="plotly_white",
            height=380,
            xaxis_title="季度",
            yaxis_title="平均 AQI",
        )
        st.plotly_chart(fig, use_container_width=True)
        worst_quarter = quarter_avg.loc[quarter_avg["AQI"].idxmax()]
        best_quarter = quarter_avg.loc[quarter_avg["AQI"].idxmin()]
        st.caption(
            f"解读：季度中 {worst_quarter['quarter']} 最高（{worst_quarter['AQI']:.1f}），{best_quarter['quarter']} 最低（{best_quarter['AQI']:.1f}）。"
        )

    # 月份分析
    with season_tabs[2]:
        month_avg = df.groupby("month", as_index=False)["AQI"].mean().sort_values("month")
        month_avg["month_label"] = month_avg["month"].apply(lambda m: f"{int(m)}月")

        fig = go.Figure(
            go.Scatter(
                x=month_avg["month_label"],
                y=month_avg["AQI"],
                mode="lines+markers",
                line=dict(color="#cc3366", width=3),
            )
        )
        fig.update_layout(
            template="plotly_white",
            height=380,
            xaxis_title="月份",
            yaxis_title="平均 AQI",
        )
        st.plotly_chart(fig, use_container_width=True)
        worst_month = month_avg.loc[month_avg["AQI"].idxmax()]
        best_month = month_avg.loc[month_avg["AQI"].idxmin()]
        st.caption(
            f"解读：月份中 {worst_month['month_label']} 最高（{worst_month['AQI']:.1f}），{best_month['month_label']} 最低（{best_month['AQI']:.1f}）。"
        )

    # 多点图看季节性（散点）
    with season_tabs[3]:
        scatter_df = df.copy()
        scatter_df["year"] = scatter_df["date"].dt.year
        scatter_df["dayofyear"] = scatter_df["date"].dt.dayofyear

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=scatter_df["dayofyear"],
                y=scatter_df["AQI"],
                mode="markers",
                marker=dict(size=4, opacity=0.25, color="#444"),
                name="样本点",
            )
        )
        doy_mean = scatter_df.groupby("dayofyear", as_index=False)["AQI"].mean()
        doy_mean = doy_mean.sort_values("dayofyear")
        fig.add_trace(
            go.Scatter(
                x=doy_mean["dayofyear"],
                y=doy_mean["AQI"],
                mode="lines",
                line=dict(color="#FF4B4B", width=3),
                name="多年均值",
            )
        )
        fig.update_layout(
            template="plotly_white",
            height=420,
            xaxis_title="一年中的第几天（Day of Year）",
            yaxis_title="AQI",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("解读：灰点是每日样本，红线是全年平均季节曲线；红线峰值越高，说明该时段更易出现污染。")

# -----------------------------
# 不同城市 AQI 对比
# -----------------------------
with tab_multicity:
    st.subheader("AQI 对比（同一时间范围）")
    cities_default = [city]
    cities_compare = st.multiselect(
        "选择对比城市",
        cities,
        default=cities_default,
        help="建议最多选择 5 个城市，图表更清晰。",
    )

    if len(cities_compare) < 2:
        st.info("至少选择 2 个城市才能进行对比。")
    else:
        if len(cities_compare) > 6:
            st.warning("城市数量较多，已截断到前 6 个以保证性能与可读性。")
            cities_compare = cities_compare[:6]

        # 统一过滤同一时间段
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        fig = go.Figure()
        city_stats = []

        show_ma = st.checkbox("显示 7日均线（更平滑）", value=True)

        for c in cities_compare:
            dfc = load_city_data(c)
            dfc = dfc.loc[(dfc["date"] >= start_ts) & (dfc["date"] <= end_ts)].copy()
            if dfc.empty or "AQI" not in dfc.columns:
                continue
            dfc = dfc.sort_values("date")

            avg = float(dfc["AQI"].mean())
            maxv = float(dfc["AQI"].max())
            minv = float(dfc["AQI"].min())
            city_stats.append({"城市": c, "平均 AQI": avg, "最高 AQI": maxv, "最低 AQI": minv})

            fig.add_trace(
                go.Scatter(
                    x=dfc["date"],
                    y=dfc["AQI"],
                    mode="lines",
                    name=f"{c}（AQI）",
                )
            )
            if show_ma:
                dfc["MA7"] = dfc["AQI"].rolling(7).mean()
                fig.add_trace(
                    go.Scatter(
                        x=dfc["date"],
                        y=dfc["MA7"],
                        mode="lines",
                        name=f"{c}（MA7）",
                        line=dict(width=2),
                        opacity=0.6,
                    )
                )

        if city_stats:
            city_stats_df = pd.DataFrame(city_stats)
            base_avg = city_stats_df.loc[city_stats_df["城市"] == city, "平均 AQI"]
            base_avg = float(base_avg.iloc[0]) if not base_avg.empty else float(city_stats_df["平均 AQI"].mean())
            city_stats_df["相对基准城市差值"] = (city_stats_df["平均 AQI"] - base_avg).round(1)
            fig.update_layout(
                template="plotly_white",
                height=520,
                legend=dict(orientation="h"),
                title="不同城市 AQI 对比",
                xaxis_title="日期",
                yaxis_title="AQI",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                city_stats_df.sort_values("平均 AQI"),
                use_container_width=True,
                height=260,
            )
            best_city_row = city_stats_df.loc[city_stats_df["平均 AQI"].idxmin()]
            worst_city_row = city_stats_df.loc[city_stats_df["平均 AQI"].idxmax()]
            st.caption(
                f"解读：对比城市中，平均 AQI 最低是 {best_city_row['城市']}（{best_city_row['平均 AQI']:.1f}），"
                f"最高是 {worst_city_row['城市']}（{worst_city_row['平均 AQI']:.1f}）。"
            )
        else:
            st.warning("所选城市在当前时间范围内暂无可用 AQI 数据。")

# -----------------------------
# 污染物对比（可选）
# -----------------------------
with tab_pollutants:
    st.subheader("污染物与 AQI 的关系（如果数据里有污染物列）")

    non_date_aqi_cols = [c for c in df.columns if c not in ["date", "AQI"]]
    pollutant_candidates = [
        c for c in non_date_aqi_cols if pd.api.types.is_numeric_dtype(df[c])
    ]

    if not pollutant_candidates:
        st.info("当前城市的数据表里没有发现污染物列（除 `AQI` 外）。")
    else:
        default_polluts = pollutant_candidates[: min(3, len(pollutant_candidates))]
        selected_polluts = st.multiselect(
            "选择要对比的污染物（用于相关性/散点）",
            pollutant_candidates,
            default=default_polluts,
        )

        if not selected_polluts:
            st.info("请选择至少一个污染物。")
        else:
            # 相关性柱状图
            corrs = []
            for p in selected_polluts:
                # 避免 NaN 影响相关性
                sub = df[[p, "AQI"]].dropna()
                if len(sub) < 5:
                    corr = float("nan")
                else:
                    corr = float(sub[p].corr(sub["AQI"]))
                corrs.append({"污染物": p, "相关系数 Corr(AQI)": corr})

            corr_df = pd.DataFrame(corrs).sort_values("相关系数 Corr(AQI)", ascending=False)
            corr_fig = px.bar(
                corr_df,
                x="污染物",
                y="相关系数 Corr(AQI)",
                title="污染物与 AQI 相关性（Pearson）",
                color="相关系数 Corr(AQI)",
                color_continuous_scale=["#2ca02c", "#f7f7f7", "#d62728"],
                range_color=[-1, 1],
            )
            corr_fig.update_layout(template="plotly_white")
            st.plotly_chart(corr_fig, use_container_width=True)
            top_corr = corr_df.dropna().head(1)
            if not top_corr.empty:
                t = top_corr.iloc[0]
                st.caption(
                    f"解读：当前相关性最高的是 {t['污染物']}（r={t['相关系数 Corr(AQI)']:.2f}），可作为重点监测对象。"
                )

            # 散点：选择一个重点污染物做对比
            pollutant_focus = st.selectbox("选择重点污染物用于散点图", selected_polluts)
            focus_sub = df[[pollutant_focus, "AQI"]].dropna()
            if len(focus_sub) > 0:
                scatter = px.scatter(
                    focus_sub,
                    x=pollutant_focus,
                    y="AQI",
                    trendline="ols",
                    opacity=0.6,
                    labels={pollutant_focus: pollutant_focus, "AQI": "AQI"},
                    title=f"{pollutant_focus} vs AQI",
                )
                scatter.update_layout(template="plotly_white")
                st.plotly_chart(scatter, use_container_width=True)

            st.caption("相关性只用于探索性分析，不等同于因果关系。")

st.success("✅ 历史分析页面加载完成")