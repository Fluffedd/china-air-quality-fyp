# src/utils.py
import numpy as np
def get_aqi_level(aqi):
    if aqi is None: return "无数据"
    aqi = float(aqi)
    if aqi <=50: return "优"
    if aqi<=100: return "良"
    if aqi<=150: return "轻度污染"
    if aqi<=200: return "中度污染"
    if aqi<=300: return "重度污染"
    return "严重污染"

def get_aqi_color(aqi):
    if aqi is None: return "#aaaaaa"
    aqi=float(aqi)
    if aqi<=50: return "#00e400"
    if aqi<=100: return "#ffff00"
    if aqi<=150: return "#ff9900"
    if aqi<=200: return "#ff0000"
    if aqi<=300: return "#99004c"
    return "#7e0023"
