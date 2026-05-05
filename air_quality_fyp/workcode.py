import streamlit as st
import requests
import pandas as pd
from pyecharts.charts import Map
from pyecharts import options as opts
from streamlit_echarts import st_pyecharts
import plotly.express as px
from datetime import datetime
import time
import os

# =============================
# 配置
# =============================``
API_TOKEN = "c789e2f118363d65053b4360e4f42ed9d345917d"

# 中国省级行政区划及主要城市（扩展版）
CITY_LIST = [
    # 直辖市
    "beijing", "shanghai", "tianjin", "chongqing",
    # 省份省会/首府
    "guangzhou", "shenzhen", "hangzhou", "nanjing", "wuhan", "chengdu", "xian",
    "zhengzhou", "changsha", "shenyang", "changchun", "harbin", "shijiazhuang",
    "taiyuan", "jinan", "hefei", "fuzhou", "nanchang", "jinan", "haikou",
    "kunming", "guiyang", "xining", "yinchuan", "urumqi", "lhasa",
    
    # 重要城市
    "suzhou", "qingdao", "dalian", "ningbo", "xiamen", "wuxi", "foshan",
    "dongguan", "zhuhai", "shantou", "zibo", "wenzhou", "changzhou",
    "nantong", "yangzhou", "yantai", "weifang", "linyi", "jining",
    "baotou", "hohhot", "datong", "baoding", "tangshan", "handan",
    "anyang", "xinxiang", "luoyang", "kaifeng", "xiangyang", "yichang",
    "zhuzhou", "xiangtan", "zhangjiajie", "zhuhai", "zhongshan", "jiangmen",
    "zhanjiang", "maoming", "huizhou", "shaoguan", "heyuan", "yangjiang",
    "qingyuan", "dongguan", "zhongshan", "foshan", "jiangmen", "zhaoqing",
    "huizhou", "meizhou", "shanwei", "jieyang", "yunfu", "chaozhou",
    
    # 特别行政区
    "hongkong", "macau"
]

# 城市中文名映射
CITY_CN_MAP = {
    "beijing": "北京", "shanghai": "上海", "tianjin": "天津", "chongqing": "重庆",
    "guangzhou": "广州", "shenzhen": "深圳", "hangzhou": "杭州", "nanjing": "南京",
    "wuhan": "武汉", "chengdu": "成都", "xian": "西安", "zhengzhou": "郑州",
    "changsha": "长沙", "shenyang": "沈阳", "changchun": "长春", "harbin": "哈尔滨",
    "shijiazhuang": "石家庄", "taiyuan": "太原", "jinan": "济南", "hefei": "合肥",
    "fuzhou": "福州", "nanchang": "南昌", "haikou": "海口", "kunming": "昆明",
    "guiyang": "贵阳", "xining": "西宁", "yinchuan": "银川", "urumqi": "乌鲁木齐",
    "lhasa": "拉萨", "suzhou": "苏州", "qingdao": "青岛", "dalian": "大连",
    "ningbo": "宁波", "xiamen": "厦门", "wuxi": "无锡", "foshan": "佛山",
    "dongguan": "东莞", "zhuhai": "珠海", "shantou": "汕头", "zibo": "淄博",
    "wenzhou": "温州", "changzhou": "常州", "nantong": "南通", "yangzhou": "扬州",
    "yantai": "烟台", "weifang": "潍坊", "linyi": "临沂", "jining": "济宁",
    "baotou": "包头", "hohhot": "呼和浩特", "datong": "大同", "baoding": "保定",
    "tangshan": "唐山", "handan": "邯郸", "anyang": "安阳", "xinxiang": "新乡",
    "luoyang": "洛阳", "kaifeng": "开封", "xiangyang": "襄阳", "yichang": "宜昌",
    "zhuzhou": "株洲", "xiangtan": "湘潭", "zhangjiajie": "张家界", "zhongshan": "中山",
    "jiangmen": "江门", "zhanjiang": "湛江", "maoming": "茂名", "huizhou": "惠州",
    "shaoguan": "韶关", "heyuan": "河源", "yangjiang": "阳江", "qingyuan": "清远",
    "zhaoqing": "肇庆", "meizhou": "梅州", "shanwei": "汕尾", "jieyang": "揭阳",
    "yunfu": "云浮", "chaozhou": "潮州", "hongkong": "香港", "macau": "澳门"
}

# 城市坐标数据
CITY_COORDS = {
    "北京": [116.4074, 39.9042], "上海": [121.4737, 31.2304], 
    "天津": [117.2010, 39.0842], "重庆": [106.5516, 29.5630],
    "广州": [113.2644, 23.1291], "深圳": [114.0579, 22.5431],
    "杭州": [120.1551, 30.2741], "南京": [118.7969, 32.0603],
    "武汉": [114.3052, 30.5928], "成都": [104.0668, 30.5728],
    "西安": [108.9480, 34.2632], "郑州": [113.6654, 34.7570],
    "长沙": [112.9388, 28.2282], "沈阳": [123.4315, 41.8057],
    "长春": [125.3245, 43.8868], "哈尔滨": [126.5350, 45.8038],
    "石家庄": [114.5149, 38.0423], "太原": [112.5489, 37.8706],
    "济南": [117.1201, 36.6512], "合肥": [117.2272, 31.8206],
    "福州": [119.2965, 26.0745], "南昌": [115.8581, 28.6829],
    "海口": [110.1999, 20.0442], "昆明": [102.8332, 24.8797],
    "贵阳": [106.7074, 26.5982], "西宁": [101.7778, 36.6171],
    "银川": [106.2325, 38.4864], "乌鲁木齐": [87.6168, 43.8256],
    "拉萨": [91.1172, 29.6469], "苏州": [120.5853, 31.2990],
    "青岛": [120.3826, 36.0671], "大连": [121.6186, 38.9140],
    "宁波": [121.5498, 29.8683], "厦门": [118.0894, 24.4795],
    "无锡": [120.3119, 31.4912], "佛山": [113.1224, 23.0094],
    "东莞": [113.7518, 23.0207], "珠海": [113.5767, 22.2707],
    "香港": [114.1694, 22.3193], "澳门": [113.5439, 22.1987]
}

# =============================
# 函数定义
# =============================
def get_city_aqi(city):
    """获取单个城市的AQI数据"""
    url = f"https://api.waqi.info/feed/{city}/?token={API_TOKEN}"
    try:
        r = requests.get(url, timeout=10).json()
        if r["status"] != "ok":
            return None
        data = r["data"]
        return {
            "city_en": city,
            "city_cn": CITY_CN_MAP.get(city, city),
            "aqi": int(data["aqi"]) if str(data["aqi"]).isdigit() else None,
            "pm25": data["iaqi"].get("pm25", {}).get("v", None) if "iaqi" in data else None,
            "pm10": data["iaqi"].get("pm10", {}).get("v", None) if "iaqi" in data else None,
            "o3": data["iaqi"].get("o3", {}).get("v", None) if "iaqi" in data else None,
            "no2": data["iaqi"].get("no2", {}).get("v", None) if "iaqi" in data else None,
            "so2": data["iaqi"].get("so2", {}).get("v", None) if "iaqi" in data else None,
            "co": data["iaqi"].get("co", {}).get("v", None) if "iaqi" in data else None,
            "dominent": data.get("dominentpol", "N/A"),
            "update_time": data["time"]["s"],
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"获取{city}数据失败: {e}")
        return None

def health_advice(aqi):
    """健康建议"""
    if aqi is None:
        return "无数据"
    if aqi <= 50:
        return "空气质量优，可正常活动"
    elif aqi <= 100:
        return "良，敏感人群注意"
    elif aqi <= 150:
        return "轻度污染，减少户外活动"
    elif aqi <= 200:
        return "中度污染，儿童/老人注意防护"
    elif aqi <= 300:
        return "重度污染，尽量减少外出"
    else:
        return "严重污染，建议留在室内并佩戴口罩"

def get_aqi_color(aqi):
    """根据AQI获取颜色"""
    if aqi <= 50:
        return "#00e400"  # 绿色
    elif aqi <= 100:
        return "#ffff00"  # 黄色
    elif aqi <= 150:
        return "#ff9900"  # 橙色
    elif aqi <= 200:
        return "#ff0000"  # 红色
    elif aqi <= 300:
        return "#99004c"  # 紫色
    else:
        return "#7e0023"  # 深红色

def get_aqi_level(aqi):
    """根据AQI获取等级"""
    if aqi <= 50:
        return "优"
    elif aqi <= 100:
        return "良"
    elif aqi <= 150:
        return "轻度污染"
    elif aqi <= 200:
        return "中度污染"
    elif aqi <= 300:
        return "重度污染"
    else:
        return "严重污染"

def create_csv_filename():
    """创建包含时间戳的CSV文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"china_aqi_data_{timestamp}.csv"

def batch_fetch_aqi(city_list, progress_bar=None):
    """批量获取AQI数据"""
    records = []
    total_cities = len(city_list)
    
    for i, city in enumerate(city_list):
        data = get_city_aqi(city)
        if data and data['aqi'] is not None:
            records.append(data)
        
        # 更新进度条
        if progress_bar:
            progress_bar.progress((i + 1) / total_cities)
        
        # 避免请求过快
        time.sleep(0.1)
    
    return records

# =============================
# Streamlit 页面布局
# =============================
st.set_page_config(page_title="中国空气质量实时监测", layout="wide")

# 标题
st.title("🇨🇳 中国空气质量实时监测平台")
st.markdown("---")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    
    # 城市选择
    st.subheader("选择要监测的城市")
    selected_cities = st.multiselect(
        "城市列表",
        options=CITY_LIST,
        default=CITY_LIST[:20],
        format_func=lambda x: f"{CITY_CN_MAP.get(x, x)} ({x})"
    )
    
    # 自动刷新设置
    st.subheader("🔄 自动刷新")
    auto_refresh = st.checkbox("启用自动刷新", value=False)
    if auto_refresh:
        refresh_interval = st.slider("刷新间隔（秒）", 60, 3600, 300)
    
    # 数据管理
    st.subheader("💾 数据管理")
    if st.button("手动抓取数据"):
        st.session_state.manual_fetch = True
    else:
        st.session_state.manual_fetch = False
    
    # 显示当前数据信息
    if 'last_fetch_time' in st.session_state:
        st.info(f"上次抓取时间: {st.session_state.last_fetch_time}")

# 主区域分为三列
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    # 单城市查询
    st.subheader("🔍 单城市查询")
    input_city = st.text_input("输入城市英文名", "beijing")
    
    if st.button("查询"):
        with st.spinner("查询中..."):
            result = get_city_aqi(input_city)
            if result:
                st.success(f"📍 {result['city_cn']}")
                st.metric("AQI指数", result['aqi'], get_aqi_level(result['aqi']))
                st.write(f"主要污染物: {result['dominent']}")
                st.write(f"更新时间: {result['update_time']}")
                st.info(f"健康建议: {health_advice(result['aqi'])}")
            else:
                st.error("无法查询该城市")

# 批量数据抓取和显示
with col2:
    st.subheader("📊 全国城市空气质量实时数据")
    
    # 抓取数据按钮
    if st.button("🚀 开始抓取全国数据", type="primary") or st.session_state.get('manual_fetch', False):
        with st.spinner("正在抓取全国空气质量数据..."):
            progress_bar = st.progress(0)
            records = batch_fetch_aqi(selected_cities, progress_bar)
            
            if records:
                # 创建DataFrame
                df = pd.DataFrame(records)
                
                # 添加等级和颜色列
                df['level'] = df['aqi'].apply(get_aqi_level)
                df['color'] = df['aqi'].apply(get_aqi_color)
                
                # 按AQI排序
                df = df.sort_values('aqi', ascending=False)
                
                # 保存数据
                csv_filename = create_csv_filename()
                df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                
                # 保存到session state
                st.session_state.aqi_data = df
                st.session_state.last_fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.csv_filename = csv_filename
                
                st.success(f"✅ 数据抓取完成！共获取 {len(df)} 个城市的数据")
                st.success(f"💾 数据已保存到: {csv_filename}")
                
                # 显示数据表格
                st.dataframe(
                    df[['city_cn', 'aqi', 'level', 'pm25', 'pm10', 'dominent', 'update_time']].head(20),
                    use_container_width=True
                )
            else:
                st.error("❌ 数据抓取失败")

# 显示已有数据
with col3:
    st.subheader("📁 数据文件")
    
    # 列出所有CSV文件
    csv_files = [f for f in os.listdir('.') if f.startswith('china_aqi_data_') and f.endswith('.csv')]
    if csv_files:
        latest_file = max(csv_files, key=os.path.getctime)
        st.write("最新数据文件:")
        st.code(latest_file)
        
        if st.button("📥 加载最新数据"):
            try:
                df = pd.read_csv(latest_file)
                st.session_state.aqi_data = df
                st.success(f"已加载 {len(df)} 条记录")
            except:
                st.error("文件加载失败")
    else:
        st.info("暂无数据文件")

# =============================
# 地图显示
# =============================
st.markdown("---")
st.header("🗺️ 中国空气质量分布地图")

# 选择地图类型
map_type = st.radio("选择地图类型", ["Plotly交互地图", "PyECharts分级地图"], horizontal=True)

# 检查是否有数据
if 'aqi_data' not in st.session_state or st.session_state.aqi_data.empty:
    st.warning("⚠️ 请先抓取数据以显示地图")
    
    # 加载示例数据或已有文件
    if csv_files:
        if st.button("加载最新文件数据"):
            latest_file = max(csv_files, key=os.path.getctime)
            df = pd.read_csv(latest_file)
            st.session_state.aqi_data = df
            st.rerun()
else:
    df = st.session_state.aqi_data
    
    if map_type == "Plotly交互地图":
        # 准备Plotly地图数据
        plot_data = []
        for _, row in df.iterrows():
            city_cn = row['city_cn']
            if city_cn in CITY_COORDS:
                lon, lat = CITY_COORDS[city_cn]
                plot_data.append({
                    'city': city_cn,
                    'aqi': row['aqi'],
                    'level': row.get('level', get_aqi_level(row['aqi'])),
                    'lon': lon,
                    'lat': lat,
                    'pm25': row.get('pm25', 'N/A'),
                    'update_time': row.get('update_time', 'N/A')
                })
        
        if plot_data:
            df_plot = pd.DataFrame(plot_data)
            
            # 创建Plotly地图
            fig = px.scatter_mapbox(
                df_plot,
                lon='lon',
                lat='lat',
                hover_name='city',
                hover_data={
                    'aqi': True,
                    'level': True,
                    'pm25': True,
                    'update_time': True,
                    'lon': False,
                    'lat': False
                },
                size='aqi',
                color='aqi',
                color_continuous_scale=[
                    [0, '#00e400'],    # 优
                    [0.15, '#ffff00'], # 良
                    [0.3, '#ff9900'],  # 轻度污染
                    [0.45, '#ff0000'], # 中度污染
                    [0.6, '#99004c'],  # 重度污染
                    [1.0, '#7e0023']   # 严重污染
                ],
                size_max=30,
                zoom=3.2,
                height=600,
                title=f"中国城市AQI分布 ({st.session_state.last_fetch_time if 'last_fetch_time' in st.session_state else '实时数据'})"
            )
            
            fig.update_layout(
                mapbox_style="carto-positron",
                mapbox=dict(center=dict(lat=35, lon=105), zoom=3.2),
                margin={"r":0,"t":40,"l":0,"b":0}
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("没有足够的坐标数据来显示地图")
    
    else:  # PyECharts地图
        # 准备地图数据
        map_data = [(row['city_cn'], row['aqi']) for _, row in df.iterrows()]
        
        # 创建PyECharts地图
        c = (
            Map()
            .add(
                "AQI指数",
                map_data,
                "china",
                is_map_symbol_show=False,
                label_opts=opts.LabelOpts(is_show=False)
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title=f"中国城市AQI分布图 ({st.session_state.last_fetch_time if 'last_fetch_time' in st.session_state else '实时数据'})"
                ),
                visualmap_opts=opts.VisualMapOpts(
                    is_piecewise=True,
                    pieces=[
                        {"min": 0, "max": 50, "label": "优", "color": "#00e400"},
                        {"min": 51, "max": 100, "label": "良", "color": "#ffff00"},
                        {"min": 101, "max": 150, "label": "轻度污染", "color": "#ff9900"},
                        {"min": 151, "max": 200, "label": "中度污染", "color": "#ff0000"},
                        {"min": 201, "max": 300, "label": "重度污染", "color": "#99004c"},
                        {"min": 301, "label": "严重污染", "color": "#7e0023"},
                    ],
                    pos_top="50",
                    pos_left="20"
                )
            )
        )
        
        st_pyecharts(c, height="600px")

# =============================
# 数据统计和图表
# =============================
st.markdown("---")
st.header("📈 数据统计")

if 'aqi_data' in st.session_state and not st.session_state.aqi_data.empty:
    df = st.session_state.aqi_data
    
    # 创建三列显示统计信息
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("监测城市数量", len(df))
        avg_aqi = df['aqi'].mean()
        st.metric("平均AQI", f"{avg_aqi:.1f}")
    
    with col2:
        max_aqi = df['aqi'].max()
        max_city = df.loc[df['aqi'].idxmax(), 'city_cn']
        st.metric("最高AQI", f"{max_aqi}", max_city)
    
    with col3:
        min_aqi = df['aqi'].min()
        min_city = df.loc[df['aqi'].idxmin(), 'city_cn']
        st.metric("最低AQI", f"{min_aqi}", min_city)
    
    # AQI等级分布饼图
    st.subheader("AQI等级分布")
    level_counts = df['level'].value_counts()
    
    fig_pie = px.pie(
        values=level_counts.values,
        names=level_counts.index,
        color=level_counts.index,
        color_discrete_map={
            "优": "#00e400",
            "良": "#ffff00",
            "轻度污染": "#ff9900",
            "中度污染": "#ff0000",
            "重度污染": "#99004c",
            "严重污染": "#7e0023"
        }
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # 污染物浓度对比
    st.subheader("主要污染物浓度")
    pollutant_cols = ['pm25', 'pm10', 'o3', 'no2', 'so2', 'co']
    available_pollutants = [col for col in pollutant_cols if col in df.columns and df[col].notna().any()]
    
    if available_pollutants:
        pollutant_df = df[['city_cn'] + available_pollutants].melt(
            id_vars=['city_cn'],
            value_vars=available_pollutants,
            var_name='污染物',
            value_name='浓度'
        ).dropna()
        
        fig_bar = px.bar(
            pollutant_df,
            x='city_cn',
            y='浓度',
            color='污染物',
            barmode='group',
            title="各城市污染物浓度对比"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# =============================
# 自动刷新逻辑
# =============================
if 'auto_refresh' in locals() and auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()

# =============================
# 底部信息
# =============================
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>数据来源: <a href='https://waqi.info/' target='_blank'>World Air Quality Index</a></p>
    <p>更新时间: {}</p>
</div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)