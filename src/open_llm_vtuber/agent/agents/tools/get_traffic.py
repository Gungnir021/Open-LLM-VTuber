import os
import json
import requests
import math
from typing import Dict, List, Optional, Tuple
from loguru import logger

# 使用与天气API相同的密钥
from .get_weather import AMAP_API_KEY, get_location_adcode

def generate_rectangle(center_point: Tuple[float, float], radius_km: float) -> str:
    """
    通过中心点和半径生成矩形范围
    
    Args:
        center_point: 中心点坐标 (经度,纬度)
        radius_km: 半径（单位：公里）
        
    Returns:
        矩形范围字符串 (格式: "左下角经度,左下角纬度;右上角经度,右上角纬度")
    """
    try:
        center_lon, center_lat = center_point
        
        # 经度1度约等于111公里，纬度1度约等于111*cos(纬度)公里
        # 将半径转换为度数
        lat_diff = radius_km / 111.0
        lon_diff = radius_km / (111.0 * math.cos(math.radians(center_lat)))
        
        min_lon = center_lon - lon_diff
        min_lat = center_lat - lat_diff
        max_lon = center_lon + lon_diff
        max_lat = center_lat + lat_diff
        
        rectangle = f"{min_lon:.6f},{min_lat:.6f};{max_lon:.6f},{max_lat:.6f}"
        return rectangle
    except Exception as e:
        logger.error(f"生成矩形范围时出错: {str(e)}")
        return None

def get_location_coordinates(location: str) -> Optional[Tuple[float, float]]:
    """
    通过高德地图API获取地点的坐标
    
    Args:
        location: 地点名称，如"北京"、"上海市"
        
    Returns:
        坐标元组 (经度, 纬度) 或None（如果查询失败）
    """
    geo_url = f"https://restapi.amap.com/v3/geocode/geo?key={AMAP_API_KEY}&address={location}"
    try:
        response = requests.get(geo_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "1" and data["geocodes"]:
            location_str = data["geocodes"][0]["location"]
            lon, lat = map(float, location_str.split(","))
            return (lon, lat)
        logger.warning(f"无法找到地点 '{location}' 的坐标")
        return None
    except Exception as e:
        logger.error(f"获取地点坐标时出错: {str(e)}")
        return None

def get_traffic_status(location: str, radius: float = 2.0) -> Dict:
    """
    获取指定地点周围的交通状况
    
    Args:
        location: 地点名称，如"北京"、"上海市"
        radius: 查询半径，单位为公里，默认2公里
        
    Returns:
        包含交通状况信息的字典
    """
    # 获取地点坐标
    coordinates = get_location_coordinates(location)
    if not coordinates:
        return {"error": f"找不到地点 '{location}' 或无法获取坐标"}
    
    # 生成矩形区域
    rectangle = generate_rectangle(coordinates, radius)
    if not rectangle:
        return {"error": f"无法生成查询区域"}
    
    # 查询交通状况
    traffic_url = f"https://restapi.amap.com/v3/traffic/status/rectangle?key={AMAP_API_KEY}&rectangle={rectangle}&extensions=all"
    
    try:
        response = requests.get(traffic_url, timeout=10)
        data = response.json()
        
        if data["status"] == "1":
            traffic_info = data.get("trafficinfo", {})
            roads = traffic_info.get("roads", [])
            
            if not roads:
                return {
                    "location": location,
                    "status": "无数据",
                    "message": "该区域没有交通状况数据"
                }
            
            # 统计路况
            status_count = {"未知": 0, "畅通": 0, "缓行": 0, "拥堵": 0}
            road_details = []
            
            for road in roads:
                status_code = int(road.get("status", 0))
                status_text = ["未知", "畅通", "缓行", "拥堵"][status_code] if 0 <= status_code <= 3 else "未知"
                status_count[status_text] += 1
                
                road_details.append({
                    "name": road.get("name", "未命名道路"),
                    "status": status_text,
                    "direction": road.get("direction", ""),
                    "speed": road.get("speed", "未知"),
                    "angle": road.get("angle", "")
                })
            
            # 计算整体路况
            total_roads = len(roads)
            congestion_ratio = (status_count["拥堵"] + status_count["缓行"] * 0.5) / total_roads if total_roads > 0 else 0
            
            overall_status = "畅通"
            if congestion_ratio >= 0.6:
                overall_status = "拥堵"
            elif congestion_ratio >= 0.3:
                overall_status = "缓行"
            
            return {
                "location": location,
                "overall_status": overall_status,
                "status_statistics": status_count,
                "total_roads": total_roads,
                "road_details": road_details[:5],  # 只返回前5条道路详情
                "query_time": data.get("infocode")
            }
        
        return {"error": "交通数据不可用", "api_message": data.get("info", "未知错误")}
    
    except Exception as e:
        logger.error(f"交通API请求失败: {str(e)}")
        return {"error": f"API请求失败: {str(e)}"}

def get_route_traffic(origin: str, destination: str) -> Dict:
    """
    获取两地之间的路线交通状况
    
    Args:
        origin: 起点名称，如"北京站"
        destination: 终点名称，如"北京大学"
        
    Returns:
        包含路线交通状况的字典
    """
    # 获取起点坐标
    origin_coords = get_location_coordinates(origin)
    if not origin_coords:
        return {"error": f"找不到起点 '{origin}' 或无法获取坐标"}
    
    # 获取终点坐标
    dest_coords = get_location_coordinates(destination)
    if not dest_coords:
        return {"error": f"找不到终点 '{destination}' 或无法获取坐标"}
    
    # 构建起点和终点坐标字符串
    origin_str = f"{origin_coords[0]},{origin_coords[1]}"
    destination_str = f"{dest_coords[0]},{dest_coords[1]}"
    
    # 查询路线规划
    route_url = f"https://restapi.amap.com/v3/direction/driving?key={AMAP_API_KEY}&origin={origin_str}&destination={destination_str}&extensions=all"
    
    try:
        response = requests.get(route_url, timeout=10)
        data = response.json()
        
        if data["status"] == "1" and "route" in data:
            route_info = data["route"]
            paths = route_info.get("paths", [])
            
            if not paths:
                return {
                    "origin": origin,
                    "destination": destination,
                    "status": "无数据",
                    "message": "无法获取路线信息"
                }
            
            # 获取最佳路线
            best_path = paths[0]
            
            # 提取路线信息
            distance = int(best_path.get("distance", 0))  # 单位：米
            duration = int(best_path.get("duration", 0))  # 单位：秒
            traffic_condition = best_path.get("traffic_condition", "未知")
            
            # 获取路段信息
            steps = best_path.get("steps", [])
            step_details = []
            
            for step in steps:
                road_name = step.get("road_name", "未命名道路")
                instruction = step.get("instruction", "")
                step_traffic = step.get("traffic_condition", "未知")
                step_distance = int(step.get("distance", 0))
                
                step_details.append({
                    "road": road_name,
                    "instruction": instruction,
                    "traffic": step_traffic,
                    "distance": step_distance
                })
            
            # 计算拥堵路段比例
            congested_steps = [s for s in steps if s.get("traffic_condition") in ["拥堵", "严重拥堵"]]
            congestion_ratio = len(congested_steps) / len(steps) if steps else 0
            
            return {
                "origin": origin,
                "destination": destination,
                "distance": distance,
                "distance_text": f"{distance/1000:.1f}公里" if distance >= 1000 else f"{distance}米",
                "duration": duration,
                "duration_text": f"{duration//3600}小时{(duration%3600)//60}分钟" if duration >= 3600 else f"{duration//60}分钟",
                "traffic_condition": traffic_condition,
                "congestion_ratio": f"{congestion_ratio:.0%}",
                "steps": step_details[:3]  # 只返回前3个路段详情
            }
        
        return {"error": "路线数据不可用", "api_message": data.get("info", "未知错误")}
    
    except Exception as e:
        logger.error(f"路线API请求失败: {str(e)}")
        return {"error": f"API请求失败: {str(e)}"}