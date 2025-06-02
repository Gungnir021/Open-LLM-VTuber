import os
import json
import requests
from typing import Dict, Any, Optional
from loguru import logger
from dotenv import load_dotenv
from .tool_base import ToolBase

# 加载环境变量
load_dotenv()
AMAP_API_KEY = os.getenv("AMAP_API_KEY")

class TrafficTool(ToolBase):
    """交通态势查询工具"""
    
    # 支持的城市列表
    SUPPORTED_CITIES = [
        "杭州", "西宁", "南京", "昆明", "武汉", "上海", "珠海", "沈阳", "深圳", "大连", 
        "宁波", "西安", "青岛", "佛山", "厦门", "福州", "合肥", "长沙", "温州", "台州", 
        "常州", "天津", "东莞", "成都", "苏州", "石家庄", "长春", "太原", "济南", "乌鲁木齐", 
        "绍兴", "重庆", "泉州", "惠州", "中山", "无锡", "广州", "嘉兴", "北京", "金华"
    ]
    
    @property
    def name(self) -> str:
        return "get_traffic_status"
    
    @property
    def description(self) -> str:
        return "查询指定区域的道路交通态势信息，包括拥堵程度、道路状况等"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rectangle": {
                    "type": "string",
                    "description": "矩形区域范围，格式为'左下角经度,左下角纬度;右上角经度,右上角纬度'，如：'116.351147,39.966309;116.357134,39.968727'。对角线距离不能超过10公里"
                },
                "level": {
                    "type": "integer",
                    "description": "道路等级过滤，可选值：0(所有道路)、1(高速路、国道、省道、城市快速路)、2(高速路、国道、省道、城市快速路、主要道路)、3(高速路、国道、省道、城市快速路、主要道路、一般道路)、4(高速路、国道、省道、城市快速路、主要道路、一般道路、县道)、5(高速路、国道、省道、城市快速路、主要道路、一般道路、县道、乡镇村道)、6(所有道路)，默认为6",
                    "default": 6,
                    "minimum": 0,
                    "maximum": 6
                },
                "extensions": {
                    "type": "string",
                    "description": "返回结果控制，可选值：base(返回基本信息)、all(返回全部信息)，默认为all",
                    "default": "all",
                    "enum": ["base", "all"]
                },
                "city": {
                    "type": "string",
                    "description": "城市名称，用于验证是否支持交通态势查询。支持的城市包括：北京、上海、广州、深圳、杭州、南京、武汉等"
                }
            },
            "required": ["rectangle"]
        }
    
    def execute(self, rectangle: str, level: int = 6, extensions: str = "all", city: str = None) -> str:
        """执行交通态势查询"""
        try:
            # 验证API密钥
            if not AMAP_API_KEY:
                return json.dumps({"error": "未配置高德地图API密钥，请在.env文件中设置AMAP_API_KEY"}, ensure_ascii=False)
            
            # 验证城市支持
            if city and not self._is_city_supported(city):
                return json.dumps({
                    "error": f"城市'{city}'不支持交通态势查询",
                    "supported_cities": self.SUPPORTED_CITIES
                }, ensure_ascii=False)
            
            # 验证矩形区域格式
            if not self._validate_rectangle(rectangle):
                return json.dumps({"error": "矩形区域格式错误，应为'左下角经度,左下角纬度;右上角经度,右上角纬度'"}, ensure_ascii=False)
            
            # 验证参数范围
            if level < 0 or level > 6:
                return json.dumps({"error": "道路等级参数错误，应为0-6之间的整数"}, ensure_ascii=False)
            
            if extensions not in ["base", "all"]:
                return json.dumps({"error": "extensions参数错误，应为'base'或'all'"}, ensure_ascii=False)
            
            # 获取交通态势数据
            traffic_data = self._get_traffic_data(rectangle, level, extensions)
            if traffic_data.get("error"):
                return json.dumps(traffic_data, ensure_ascii=False)
            
            # 格式化返回结果
            formatted_result = self._format_traffic_result(traffic_data)
            return json.dumps(formatted_result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"交通态势查询出错: {str(e)}")
            return json.dumps({"error": f"交通态势查询失败: {str(e)}"}, ensure_ascii=False)
    
    def _is_city_supported(self, city: str) -> bool:
        """检查城市是否支持交通态势查询"""
        return any(supported_city in city for supported_city in self.SUPPORTED_CITIES)
    
    def _validate_rectangle(self, rectangle: str) -> bool:
        """验证矩形区域格式"""
        try:
            parts = rectangle.split(';')
            if len(parts) != 2:
                return False
            
            # 验证左下角坐标
            left_bottom = parts[0].split(',')
            if len(left_bottom) != 2:
                return False
            lng1, lat1 = float(left_bottom[0]), float(left_bottom[1])
            
            # 验证右上角坐标
            right_top = parts[1].split(',')
            if len(right_top) != 2:
                return False
            lng2, lat2 = float(right_top[0]), float(right_top[1])
            
            # 验证坐标范围（中国境内）
            if not (73 <= lng1 <= 135 and 3 <= lat1 <= 54):
                return False
            if not (73 <= lng2 <= 135 and 3 <= lat2 <= 54):
                return False
            
            # 验证矩形的有效性（左下角应该在右上角的左下方）
            if lng1 >= lng2 or lat1 >= lat2:
                return False
            
            return True
        except (ValueError, IndexError):
            return False
    
    def _get_traffic_data(self, rectangle: str, level: int, extensions: str) -> Dict[str, Any]:
        """获取交通态势数据"""
        try:
            # 构建请求参数
            params = {
                "key": AMAP_API_KEY,
                "rectangle": rectangle,
                "level": level,
                "extensions": extensions,
                "output": "json"
            }
            
            response = requests.get(
                "https://restapi.amap.com/v3/traffic/status/rectangle",
                params=params,
                timeout=10
            )
            
            # 检查HTTP状态码
            response.raise_for_status()
            
            traffic_data = response.json()
            
            if traffic_data.get("status") != "1":
                error_msg = traffic_data.get("info", "未知错误")
                error_code = traffic_data.get("infocode", "")
                return {"error": f"API调用失败: {error_msg} (错误码: {error_code})"}
            
            return traffic_data
            
        except requests.exceptions.Timeout:
            return {"error": "请求超时，请稍后重试"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"HTTP请求失败: {str(e)}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"网络请求失败: {str(e)}"}
        except json.JSONDecodeError:
            return {"error": "API返回数据格式错误"}
        except Exception as e:
            return {"error": f"获取交通数据时出错: {str(e)}"}
    
    def _format_traffic_result(self, traffic_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化交通态势结果"""
        try:
            trafficinfo = traffic_data.get("trafficinfo", {})
            roads = trafficinfo.get("roads", [])
            
            if not roads:
                return {
                    "status": "success",
                    "message": "查询区域内暂无交通态势数据",
                    "road_count": 0,
                    "roads": []
                }
            
            # 统计交通状况
            traffic_stats = {
                "畅通": 0,
                "缓行": 0,
                "拥堵": 0,
                "严重拥堵": 0,
                "未知": 0
            }
            
            formatted_roads = []
            
            for road in roads:
                # 获取道路基本信息
                road_info = {
                    "name": road.get("name", "未知道路"),
                    "status": self._get_status_text(road.get("status", "0")),
                    "speed": road.get("speed", "未知"),
                    "direction": road.get("direction", "未知"),
                    "angle": road.get("angle", "未知"),
                    "polyline": road.get("polyline", ""),
                    "lcodes": road.get("lcodes", ""),  # 路况编码
                    "time": road.get("time", "")  # 路况时间
                }
                
                # 统计交通状况
                status_text = road_info["status"]
                if status_text in traffic_stats:
                    traffic_stats[status_text] += 1
                else:
                    traffic_stats["未知"] += 1
                
                formatted_roads.append(road_info)
            
            return {
                "status": "success",
                "message": "交通态势查询成功",
                "road_count": len(roads),
                "traffic_summary": traffic_stats,
                "roads": formatted_roads[:50],  # 增加返回道路数量限制
                "query_info": {
                    "description": trafficinfo.get("description", ""),
                    "evaluation": trafficinfo.get("evaluation", {})
                }
            }
            
        except Exception as e:
            logger.error(f"格式化交通数据时出错: {str(e)}")
            return {"error": f"数据格式化失败: {str(e)}"}
    
    def _get_status_text(self, status: str) -> str:
        """将状态码转换为文字描述"""
        status_map = {
            "1": "畅通",
            "2": "缓行",
            "3": "拥堵",
            "4": "严重拥堵"
        }
        return status_map.get(str(status), "未知")