from typing import Dict, Any
import os
import json
import requests
from loguru import logger
from dotenv import load_dotenv
from .tool_base import ToolBase

# 加载环境变量
load_dotenv()
AMAP_API_KEY = os.getenv("AMAP_API_KEY")

class InfrastructureTool(ToolBase):
    """周边基础设施查询工具"""
    
    # POI类型映射表，基于高德地图POI分类
    POI_TYPES = {
        "医院": "090100",      # 医疗保健-综合医院
        "学校": "141200",      # 科教文化服务-学校
        "银行": "160100",      # 金融保险服务-银行
        "ATM": "160200",       # 金融保险服务-ATM
        "加油站": "010100",    # 汽车服务-加油站
        "停车场": "150900",    # 交通设施服务-停车场
        "超市": "061000",      # 购物服务-超市
        "餐厅": "050000",      # 餐饮服务
        "酒店": "100000",      # 住宿服务
        "公交站": "150700",    # 交通设施服务-公交车站
        "地铁站": "150500",    # 交通设施服务-地铁站
        "药店": "090600",      # 医疗保健服务-药店
        "邮局": "110000",      # 邮政电信服务
    }
    
    @property
    def name(self) -> str:
        return "search_nearby_infrastructure"
    
    @property
    def description(self) -> str:
        return "搜索指定位置周边的基础设施，如医院、学校、银行、加油站、停车场等"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "查询位置，可以是城市名、地址或地标，如：北京、上海市浦东新区、天安门广场等"
                },
                "infrastructure_type": {
                    "type": "string",
                    "description": f"基础设施类型，支持：{', '.join(self.POI_TYPES.keys())}",
                    "enum": list(self.POI_TYPES.keys())
                },
                "radius": {
                    "type": "integer",
                    "description": "搜索半径（米），默认3000米，最大10000米",
                    "default": 3000,
                    "minimum": 100,
                    "maximum": 10000
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量限制，默认5个，最大10个",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["location", "infrastructure_type"]
        }
    
    def execute(self, location: str, infrastructure_type: str, radius: int = 3000, limit: int = 10) -> str:
        """执行周边基础设施查询"""
        try:
            # 验证基础设施类型
            if infrastructure_type not in self.POI_TYPES:
                return json.dumps({
                    "error": f"不支持的基础设施类型: {infrastructure_type}，支持的类型：{', '.join(self.POI_TYPES.keys())}"
                }, ensure_ascii=False)
            
            # 获取位置的经纬度坐标
            coordinates = self._get_coordinates(location)
            if not coordinates:
                return json.dumps({"error": f"无法获取位置坐标: {location}"}, ensure_ascii=False)
            
            # 获取POI类型代码
            poi_type = self.POI_TYPES[infrastructure_type]
            
            # 调用高德地图周边搜索API
            result = self._search_nearby_poi(coordinates, poi_type, radius, limit)
            
            if result.get("error"):
                return json.dumps(result, ensure_ascii=False)
            
            # 格式化返回结果
            formatted_result = self._format_result(location, infrastructure_type, radius, result)
            return json.dumps(formatted_result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"周边基础设施查询出错: {str(e)}")
            return json.dumps({"error": f"查询失败: {str(e)}"}, ensure_ascii=False)
    
    def _get_coordinates(self, location: str) -> str:
        """获取位置的经纬度坐标"""
        try:
            # 使用高德地图地理编码API
            geo_response = requests.get(
                "https://restapi.amap.com/v3/geocode/geo",
                params={
                    "key": AMAP_API_KEY,
                    "address": location
                },
                timeout=5
            )
            
            geo_data = geo_response.json()
            
            if geo_data.get("status") != "1" or not geo_data.get("geocodes"):
                logger.error(f"地理编码失败: {location}")
                return None
            
            # 返回经纬度坐标（格式："经度,纬度"）
            return geo_data["geocodes"][0]["location"]
            
        except Exception as e:
            logger.error(f"获取坐标失败: {str(e)}")
            return None
    
    def _search_nearby_poi(self, coordinates: str, poi_type: str, radius: int, limit: int) -> Dict[str, Any]:
        """搜索周边POI"""
        try:
            # 调用高德地图周边搜索API
            response = requests.get(
                "https://restapi.amap.com/v3/place/around",
                params={
                    "key": AMAP_API_KEY,
                    "location": coordinates,
                    "types": poi_type,
                    "radius": radius,
                    "offset": limit,
                    "page": 1,
                    "extensions": "all"  # 获取详细信息
                },
                timeout=10
            )
            
            data = response.json()
            
            if data.get("status") != "1":
                return {"error": f"API调用失败: {data.get('info', '未知错误')}"}
            
            return data
            
        except Exception as e:
            logger.error(f"POI搜索失败: {str(e)}")
            return {"error": f"搜索请求失败: {str(e)}"}
    
    def _format_result(self, location: str, infrastructure_type: str, radius: int, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化搜索结果"""
        pois = api_result.get("pois", [])
        
        if not pois:
            return {
                "location": location,
                "infrastructure_type": infrastructure_type,
                "radius": f"{radius}米",
                "count": 0,
                "message": f"在{location}周边{radius}米范围内未找到{infrastructure_type}",
                "results": []
            }
        
        # 格式化POI信息
        formatted_pois = []
        for poi in pois:
            formatted_poi = {
                "name": poi.get("name", "未知"),
                "address": poi.get("address", "地址未知"),
                "distance": f"{poi.get('distance', '未知')}米",
                "phone": poi.get("tel", "电话未知"),
                "type": poi.get("type", "类型未知")
            }
            
            # 添加营业时间（如果有）
            if poi.get("biz_ext") and poi["biz_ext"].get("open_time"):
                formatted_poi["business_hours"] = poi["biz_ext"]["open_time"]
            
            # 添加评分（如果有）
            if poi.get("biz_ext") and poi["biz_ext"].get("rating"):
                formatted_poi["rating"] = poi["biz_ext"]["rating"]
            
            formatted_pois.append(formatted_poi)
        
        return {
            "location": location,
            "infrastructure_type": infrastructure_type,
            "radius": f"{radius}米",
            "count": len(formatted_pois),
            "message": f"在{location}周边{radius}米范围内找到{len(formatted_pois)}个{infrastructure_type}",
            "results": formatted_pois
        }