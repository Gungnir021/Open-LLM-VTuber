import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Union, Optional
from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "ee170d9927962ec572636358acd61d53")

def get_weather(location: str) -> str:
    """获取城市当前天气（摄氏度）- 为 DeepSeek Function Calling 优化"""
    try:
        # 获取地理编码
        geo = requests.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params={"key": AMAP_API_KEY, "address": location},
            timeout=5,
        ).json()
        
        if not geo.get("geocodes"):
            return json.dumps({"error": f"找不到城市: {location}"}, ensure_ascii=False)

        adcode = geo["geocodes"][0]["adcode"]
        
        # 获取天气信息
        weather = requests.get(
            "https://restapi.amap.com/v3/weather/weatherInfo",
            params={"key": AMAP_API_KEY, "city": adcode, "extensions": "base"},
            timeout=5,
        ).json()
        
        if weather.get("status") != "1" or not weather.get("lives"):
            return json.dumps({"error": f"无法获取 {location} 天气"}, ensure_ascii=False)

        live = weather["lives"][0]
        return json.dumps({
            "city": live["city"],
            "weather": live["weather"],
            "temperature": live["temperature"] + "℃",
            "humidity": live["humidity"] + "%",
            "windpower": live["windpower"] + "级",
            "winddirection": live.get("winddirection", "未知"),
            "reporttime": live.get("reporttime", "")
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"天气查询出错: {str(e)}")
        return json.dumps({"error": f"天气查询失败: {str(e)}"}, ensure_ascii=False)

def get_location_adcode(location: str) -> Optional[str]:
    """
    通过高德地图API获取地点的行政区划编码
    
    Args:
        location: 地点名称，如"北京"、"上海市"
        
    Returns:
        行政区划编码或None（如果查询失败）
    """
    geo_url = f"https://restapi.amap.com/v3/geocode/geo?key={AMAP_API_KEY}&address={location}"
    try:
        response = requests.get(geo_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "1" and data["geocodes"]:
            return data["geocodes"][0]["adcode"]
        logger.warning(f"无法找到地点 '{location}' 的行政区划编码")
        return None
    except Exception as e:
        logger.error(f"获取地点编码时出错: {str(e)}")
        return None

def get_current_temperature(location: str, unit: str = "celsius") -> Dict:
    """
    获取指定地点的当前天气信息
    
    Args:
        location: 地点名称，如"北京"、"上海市"
        unit: 温度单位，"celsius"（摄氏度）或"fahrenheit"（华氏度）
        
    Returns:
        包含天气信息的字典
    """
    adcode = get_location_adcode(location)
    if not adcode:
        return {"error": f"找不到地点 '{location}' 或无法获取行政区划编码"}

    weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={AMAP_API_KEY}&city={adcode}&extensions=base"
    try:
        response = requests.get(weather_url, timeout=5)
        data = response.json()
        if data["status"] == "1" and data.get("lives"):
            live_weather = data["lives"][0]
            temp_c = float(live_weather.get("temperature"))
            temperature = temp_c if unit == "celsius" else temp_c * 9 / 5 + 32
            return {
                "temperature": round(temperature, 1),
                "weather": live_weather.get("weather"),
                "humidity": live_weather.get("humidity"),
                "wind_direction": live_weather.get("winddirection"),
                "wind_power": live_weather.get("windpower"),
                "location": location,
                "unit": unit,
                "report_time": live_weather.get("reporttime")
            }
        logger.warning(f"无法获取 '{location}' 的天气数据")
        return {"error": "天气数据不可用"}
    except Exception as e:
        logger.error(f"天气API请求失败: {str(e)}")
        return {"error": "API请求失败"}

def get_temperature_date(location: str, date: str, unit: str = "celsius") -> Union[Dict, List[Dict]]:
    """
    获取指定地点和日期的天气预报
    
    Args:
        location: 地点名称，如"北京"、"上海市"
        date: 日期，可以是YYYY-MM-DD格式，也可以是"明天"或"未来X天"
        unit: 温度单位，"celsius"（摄氏度）或"fahrenheit"（华氏度）
        
    Returns:
        包含天气预报的字典或字典列表
    """
    adcode = get_location_adcode(location)
    if not adcode:
        return {"error": f"找不到地点 '{location}' 或无法获取行政区划编码"}

    forecast_url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={AMAP_API_KEY}&city={adcode}&extensions=all"
    dates_to_query = []
    today = datetime.now()

    if date == "明天":
        dates_to_query.append((today + timedelta(days=1)).strftime("%Y-%m-%d"))
    elif date.startswith("未来"):
        num_days = 2 if "两" in date else int("".join([c for c in date if c.isdigit()]) or 0)
        if num_days <= 0:
            return {"error": f"无效的日期格式: {date}"}
        for i in range(1, min(num_days, 7) + 1):
            dates_to_query.append((today + timedelta(days=i)).strftime("%Y-%m-%d"))
    else:
        try:
            datetime.strptime(date, "%Y-%m-%d")
            dates_to_query.append(date)
        except ValueError:
            return {"error": f"无效的日期格式: {date}，请使用YYYY-MM-DD格式、'明天'或'未来X天'"}

    try:
        response = requests.get(forecast_url, timeout=10)
        data = response.json()
        if data["status"] == "1" and data.get("forecasts"):
            forecasts = data["forecasts"][0].get("casts", [])
            results = []
            for qd in dates_to_query:
                forecast = next((f for f in forecasts if f.get("date") == qd), None)
                if forecast:
                    temp_day = float(forecast.get("daytemp"))
                    temp_night = float(forecast.get("nighttemp"))
                    if unit == "fahrenheit":
                        temp_day = temp_day * 9 / 5 + 32
                        temp_night = temp_night * 9 / 5 + 32
                    results.append({
                        "location": location,
                        "date": qd,
                        "day_temperature": round(temp_day, 1),
                        "night_temperature": round(temp_night, 1),
                        "unit": unit,
                        "day_weather": forecast.get("dayweather"),
                        "night_weather": forecast.get("nightweather"),
                        "day_wind_direction": forecast.get("daywind"),
                        "day_wind_power": forecast.get("daypower"),
                        "night_wind_direction": forecast.get("nightwind"),
                        "night_wind_power": forecast.get("nightpower"),
                    })
                else:
                    results.append({"date": qd, "error": "未找到预报数据"})
            return results[0] if len(results) == 1 else results
        logger.warning(f"无法获取 '{location}' 的预报数据")
        return {"error": "预报数据不可用"}
    except Exception as e:
        logger.error(f"天气API请求失败: {str(e)}")
        return {"error": "API请求失败"}
