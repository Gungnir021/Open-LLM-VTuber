import requests
from typing import Dict, List, Tuple
from .get_weather import AMAP_API_KEY

def find_nearby_facilities(location: str, facility_type: str, radius: int = 1000) -> List[Dict]:
    """查找附近设施（洗手间、休息点、商场等）"""
    # 设施类型映射
    facility_mapping = {
        "洗手间": "公共厕所",
        "休息点": "公园|广场",
        "商场": "购物中心|商场",
        "餐厅": "餐饮服务",
        "医院": "医疗保健服务"
    }
    
    search_keyword = facility_mapping.get(facility_type, facility_type)
    
    # 使用高德API搜索周边
    url = "https://restapi.amap.com/v3/place/around"
    params = {
        "key": AMAP_API_KEY,
        "location": location,
        "keywords": search_keyword,
        "radius": radius,
        "output": "json"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("status") == "1":
            return data.get("pois", [])
        else:
            return []
    except Exception as e:
        return []

def get_scenic_spot_info(location: str) -> Dict:
    """获取景点信息和讲解内容"""
    # 这里可以集成景点数据库或调用相关API
    # 暂时返回模拟数据
    return {
        "name": location,
        "description": f"{location}的详细介绍和历史文化背景",
        "highlights": ["特色1", "特色2", "特色3"],
        "tips": ["游览建议1", "游览建议2"]
    }