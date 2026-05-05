# src/config.py
from pathlib import Path

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

# 重要城市坐标（更多请补充）
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

# 本地路径（优先使用新版清洗结果：data/tempo）
DATA_ROOT = Path(r"D:\Downloads\FYP CHINA\data")
TEMPO_ROOT = DATA_ROOT / "tempo"

# 如果 tempo 目录存在，则全项目默认使用 tempo 数据；
# 否则回退到旧版 data 根目录，避免本地环境直接报错。
ACTIVE_DATA_ROOT = TEMPO_ROOT if TEMPO_ROOT.exists() else DATA_ROOT

CLEANED_DIR = str(ACTIVE_DATA_ROOT / "cleaned_cities")
DAILY_DIR = str(ACTIVE_DATA_ROOT / "daily_cities")
MASTER_DAILY = str(ACTIVE_DATA_ROOT / "master_daily.csv")

CITY_GEO_FILE = str(DATA_ROOT / "city_geo.json")
REALTIME_DIR = str(DATA_ROOT / "realtime")


MODEL_DIR ="models_prophet"
PREDICT_DIR ="predict_results"