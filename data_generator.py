import os
import random
import string
import json
from datetime import datetime, timedelta
from shapely.geometry import Point, shape

# ===== 读取中国省级行政区边界 GeoJSON 文件 =====
# 该文件存储了各省的地理边界信息，后续用于判断随机生成的点是否在对应省内
with open("D:\jupyter_my\iot\Simulation\json\china.json", "r", encoding="utf-8") as f:
    china_geo = json.load(f)

# 解析 GeoJSON 文件，提取每个省份的多边形边界，并存入 province_shapes 字典
province_shapes = {}

# 省份对应的人口密度权重，用于加权随机选择省份，人口密度越大，生成数据的概率越高
province_densities = {
    "北京市": 10, "天津市": 5, "河北省": 5, "山西省": 4, "内蒙古自治区": 3, "辽宁省": 6, "吉林省": 4, "黑龙江省": 4,
    "上海市": 10, "江苏省": 8, "浙江省": 7, "安徽省": 5, "福建省": 6, "江西省": 4, "山东省": 8, "河南省": 6,
    "湖北省": 5, "湖南省": 5, "广东省": 9, "广西壮族自治区": 4, "海南省": 3, "重庆市": 6, "四川省": 7, "贵州省": 3,
    "云南省": 4, "西藏自治区": 1, "陕西省": 5, "甘肃省": 3, "青海省": 2, "宁夏回族自治区": 2, "新疆维吾尔自治区": 2,
    "台湾省": 5, "香港特别行政区": 10, "澳门特别行政区": 10
}

# 遍历 GeoJSON 中每个行政区，提取名称和边界几何形状，存储到 province_shapes 中
for feature in china_geo["features"]:
    name = feature["properties"].get("name")
    if name in province_densities:
        # 使用 shapely 的 shape 函数将 GeoJSON 几何数据转成多边形对象，方便后续点包含判断
        province_shapes[name] = shape(feature["geometry"])

# 生成省份名称列表和对应的权重列表，方便后续带权重随机选省份
province_names = list(province_shapes.keys())
province_weights = [province_densities[p] for p in province_names]


def is_inside_china(lat, lon):
    """
    判断给定的经纬度点是否位于中国境内（即是否落在某个省的边界内）
    参数:
        lat: 纬度
        lon: 经度
    返回:
        True 或 False
    """
    pt = Point(lon, lat)  # shapely 的点，注意经度在前，纬度在后
    # 遍历所有省的边界，判断点是否被包含
    return any(poly.contains(pt) for poly in province_shapes.values())


def random_device_id():
    """
    生成随机设备ID，格式为 'sensor_XXXXX'，X为数字
    """
    return "sensor_" + ''.join(random.choices(string.digits, k=5))


def random_timestamp(start_year=2024, end_year=2025):
    """
    生成一个随机时间戳，范围从 start_year 年初到 end_year 年末
    返回字符串格式 'YYYY-MM-DD HH:MM:SS'
    """
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    # 随机选择天数和秒数
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86400)
    return (start + timedelta(days=random_days, seconds=random_seconds)).strftime('%Y-%m-%d %H:%M:%S')


def random_location():
    """
    生成一个随机地理位置
    - 先基于省份权重随机选择一个省
    - 在该省的边界框内生成随机经纬度，判断点是否在省内
    - 成功则返回一个包含经度、纬度、高度和所属省份的字典
    """
    while True:
        # 按权重随机选择省份
        province = random.choices(province_names, weights=province_weights, k=1)[0]
        poly = province_shapes[province]

        # 获取省边界的最小最大经纬度范围
        minx, miny, maxx, maxy = poly.bounds
        for _ in range(10):  # 最多尝试10次生成点
            lat = round(random.uniform(miny, maxy), 6)  # 纬度
            lon = round(random.uniform(minx, maxx), 6)  # 经度
            pt = Point(lon, lat)
            # 判断点是否真正落在省边界内
            if poly.contains(pt):
                altitude = round(random.uniform(0, 2000), 2)  # 生成一个0-2000米之间的随机海拔
                return {
                    "lat": lat,
                    "lon": lon,
                    "altitude": altitude,
                    "region": province
                }


def random_optional(value_func, miss_rate=0.05):
    """
    按照缺失率决定是否返回值
    - miss_rate: 缺失概率，默认5%
    - value_func: 生成值的函数
    返回生成的值或 None
    """
    return value_func() if random.random() > miss_rate else None


def generate_device_data():
    """
    生成一个设备的详细传感器数据字典
    包含温度、湿度、电池电量、气压、状态、噪声频谱、振动加速度等多项指标
    部分数据存在缺失概率
    """
    data = {
        "temperature": round(random.uniform(-10, 50), 2),  # 温度，范围 -10~50°C
        "humidity": round(random.uniform(10, 100), 2),  # 湿度，范围 10%~100%
        "battery": random_optional(lambda: round(random.uniform(10, 100), 2)),  # 电池电量，部分缺失
        "pressure": random_optional(lambda: round(random.uniform(950, 1050), 2)),  # 气压，部分缺失
        "status": random.choice(["OK", "WARN", "ERROR"]),  # 设备状态
        "metrics": {
            "noise": {  # 噪声相关指标
                "db": round(random.uniform(30, 120), 2),  # 分贝
                "spectrum": {  # 噪声频谱
                    "low_freq": round(random.uniform(20, 100), 2),
                    "mid_freq": round(random.uniform(100, 1000), 2),
                    "high_freq": round(random.uniform(1000, 5000), 2)
                }
            },
            "vibration": {  # 振动加速度，x,y,z轴，单位可自定义
                "x": round(random.uniform(-5, 5), 3),
                "y": round(random.uniform(-5, 5), 3),
                "z": round(random.uniform(-5, 5), 3)
            }
        }
    }

    # 80%概率添加 GPS 信息，包含卫星数和水平精度因子 hdop
    if random.random() > 0.2:
        data["gps"] = {
            "satellites": random.randint(5, 20),
            "hdop": round(random.uniform(0.5, 3.0), 2)
        }

    # 50%概率添加加速度信息，x,y,z轴加速度
    if random.random() > 0.5:
        data["acceleration"] = {
            "x": round(random.uniform(-10, 10), 2),
            "y": round(random.uniform(-10, 10), 2),
            "z": round(random.uniform(-10, 10), 2)
        }

    # image_path 字段，随机选择图片路径或 None
    data["image_path"] = random.choice([f"/images/{random.randint(1, 1000)}.jpg", None])

    return data


def generate_single_record():
    """
    生成单条完整的设备数据记录
    包含设备ID、时间戳、地理位置和传感器数据
    """
    return {
        "device_id": random_device_id(),
        "timestamp": random_timestamp(),
        "location": random_location(),
        "data": generate_device_data()
    }


def generate_records(n=10000):
    """
    生成 n 条设备数据记录，返回列表
    """
    return [generate_single_record() for _ in range(n)]


def save_to_json(records, directory="output", filename="generated_data.json"):
    """
    保存生成的数据列表到 JSON 文件
    - directory: 保存目录，默认 output
    - filename: 文件名，默认 generated_data.json
    会自动创建目录
    """
    os.makedirs(directory, exist_ok=True)  # 确保目录存在
    full_path = os.path.join(directory, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        # 格式化输出中文，缩进2个空格
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"✅ 成功生成 {len(records)} 条数据，并保存至 {full_path}")

# if __name__ == "__main__":
#     # 生成50条数据示例并保存到 ../data 文件夹下
#     records = generate_records(50)
#     save_to_json(records, directory="../data", filename="iot_province_density_based50.json")
