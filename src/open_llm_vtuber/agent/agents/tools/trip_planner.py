from typing import Dict, List
from datetime import datetime, timedelta
from .get_weather import get_temperature_date
from .user_profile import UserProfileManager

def generate_travel_itinerary(destination: str, start_date: str, end_date: str, user_preferences: Dict) -> Dict:
    """生成智能旅行路线规划"""
    # 获取目的地天气信息
    weather_info = get_temperature_date(destination, start_date)
    
    # 根据用户偏好和天气生成行程
    itinerary = {
        "destination": destination,
        "dates": {"start": start_date, "end": end_date},
        "weather_forecast": weather_info,
        "daily_plans": [],
        "recommendations": {
            "clothing": _get_clothing_recommendations(weather_info),
            "activities": _get_activity_recommendations(destination, weather_info, user_preferences),
            "dining": _get_dining_recommendations(destination, user_preferences.get('dietary_restrictions', []))
        }
    }
    
    return itinerary

def generate_packing_list(destination: str, travel_dates: List[str], weather_info: Dict, user_style: str) -> List[str]:
    """生成出行清单"""
    base_items = ["身份证件", "手机充电器", "常用药品"]
    
    # 根据天气添加物品
    if weather_info.get('temperature', 0) < 10:
        base_items.extend(["厚外套", "保暖内衣", "手套"])
    elif weather_info.get('temperature', 0) > 25:
        base_items.extend(["防晒霜", "太阳镜", "轻薄衣物"])
    
    # 根据降雨概率添加雨具
    if weather_info.get('humidity', 0) > 80:
        base_items.append("雨伞")
    
    return base_items