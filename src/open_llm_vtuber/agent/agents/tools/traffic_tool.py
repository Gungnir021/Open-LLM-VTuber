import os
import json
import requests
import math
from typing import Dict, Any
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
                "city": {
                    "type": "string",
                    "description": "城市名称，如：上海、北京、广州等。系统会自动为该城市生成合适的查询范围"
                },
                "rectangle": {
                    "type": "string",
                    "description": "可选：自定义矩形区域范围，格式为'左下角经度,左下角纬度;右上角经度,右上角纬度'。如不提供，将使用城市默认范围"
                },
                "level": {
                    "type": "integer",
                    "description": "道路等级过滤，1=主要道路，6=所有道路，默认为1",
                    "default": 1,
                    "minimum": 0,
                    "maximum": 6
                },
                "extensions": {
                    "type": "string",
                    "description": "返回结果控制，base=基本信息，all=全部信息，默认为base",
                    "default": "base",
                    "enum": ["base", "all"]
                }
            },
            "required": ["city"]
        }
    
    def execute(self, city: str, rectangle: str = None, level: int = 1, extensions: str = "base") -> str:
        """执行交通态势查询"""
        try:
            # 验证API密钥
            if not AMAP_API_KEY:
                return json.dumps({"error": "未配置高德地图API密钥，请在.env文件中设置AMAP_API_KEY"}, ensure_ascii=False)
            
            # 验证城市支持
            if not self._is_city_supported(city):
                return json.dumps({
                    "error": f"城市'{city}'不支持交通态势查询",
                    "supported_cities": self.SUPPORTED_CITIES
                }, ensure_ascii=False)
            
            # 如果没有提供rectangle，根据城市生成默认范围
            if not rectangle:
                rectangle = self._get_city_default_rectangle(city)
                if not rectangle:
                    return json.dumps({"error": f"无法为城市'{city}'生成默认查询范围"}, ensure_ascii=False)
            
            # 验证并调整矩形区域
            adjusted_rectangle = self._adjust_rectangle_if_needed(rectangle)
            if not adjusted_rectangle:
                return json.dumps({"error": "矩形区域格式错误或范围过大，应为'左下角经度,左下角纬度;右上角经度,右上角纬度'，且对角线距离不超过10公里"}, ensure_ascii=False)
            
            # 验证参数范围
            if level < 0 or level > 6:
                return json.dumps({"error": "道路等级参数错误，应为0-6之间的整数"}, ensure_ascii=False)
            
            if extensions not in ["base", "all"]:
                return json.dumps({"error": "extensions参数错误，应为'base'或'all'"}, ensure_ascii=False)
            
            # 获取交通态势数据
            traffic_data = self._get_traffic_data(adjusted_rectangle, level, extensions)
            if traffic_data.get("error"):
                return json.dumps(traffic_data, ensure_ascii=False)
            
            # 格式化返回结果
            formatted_result = self._format_traffic_result(traffic_data, city, adjusted_rectangle)
            return json.dumps(formatted_result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"交通态势查询出错: {str(e)}")
            return json.dumps({"error": f"交通态势查询失败: {str(e)}"}, ensure_ascii=False)
    
    def _is_city_supported(self, city: str) -> bool:
        """检查城市是否支持交通态势查询"""
        return any(supported_city in city for supported_city in self.SUPPORTED_CITIES)
    
    def _get_city_default_rectangle(self, city: str) -> str:
        """根据城市获取默认查询矩形范围"""
        city_rectangles = {
            "上海": "121.3574,31.1718;121.5810,31.3076",  # 上海市中心区域，约5公里范围
            "北京": "116.2844,39.8493;116.4733,39.9850",  # 北京市中心区域
            "广州": "113.1943,23.0669;113.3840,23.1966",  # 广州市中心区域
            "深圳": "114.0579,22.5178;114.2577,22.6475",  # 深圳市中心区域
            "杭州": "120.0791,30.2084;120.2688,30.3381",  # 杭州市中心区域
            "南京": "118.7073,32.0162;118.8970,32.1459",  # 南京市中心区域
            "武汉": "114.2049,30.5370;114.3946,30.6667",  # 武汉市中心区域
            "西安": "108.8400,34.2000;109.0400,34.3300",  # 西安市中心区域
            "成都": "104.0100,30.6000;104.2100,30.7300",  # 成都市中心区域
            "重庆": "106.4500,29.5000;106.6500,29.6300",  # 重庆市中心区域
            "天津": "117.1000,39.0000;117.3000,39.1300",  # 天津市中心区域
            "苏州": "120.5000,31.2000;120.7000,31.3300",  # 苏州市中心区域
        }
        
        for city_name, rectangle in city_rectangles.items():
            if city_name in city:
                return rectangle
        
        # 如果没有预设的城市范围，返回None
        return None
    
    def _adjust_rectangle_if_needed(self, rectangle: str) -> str:
        """调整矩形范围以确保符合API要求"""
        try:
            if not self._validate_rectangle(rectangle):
                return None
            
            parts = rectangle.split(';')
            left_bottom = parts[0].split(',')
            right_top = parts[1].split(',')
            
            lng1, lat1 = float(left_bottom[0]), float(left_bottom[1])
            lng2, lat2 = float(right_top[0]), float(right_top[1])
            
            # 计算对角线距离（简化计算）
            distance = math.sqrt((lng2 - lng1)**2 + (lat2 - lat1)**2) * 111  # 粗略转换为公里
            
            # 如果距离超过10公里，缩小范围
            if distance > 10:
                # 缩小到5公里范围
                center_lng = (lng1 + lng2) / 2
                center_lat = (lat1 + lat2) / 2
                
                # 大约0.025度对应2.5公里
                offset = 0.025
                
                new_rectangle = f"{center_lng-offset},{center_lat-offset};{center_lng+offset},{center_lat+offset}"
                logger.info(f"矩形范围过大，已自动调整为: {new_rectangle}")
                return new_rectangle
            
            return rectangle
            
        except Exception as e:
            logger.error(f"调整矩形范围时出错: {str(e)}")
            return None
    
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
            
            logger.info(f"交通态势查询参数: {params}")
            
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
                
                # 针对20000错误码提供更详细的说明
                if error_code == "20000":
                    error_msg += "。可能原因：1)查询范围过大(超过10公里) 2)坐标格式不正确 3)API密钥权限不足"
                
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
    
    def _format_traffic_result(self, traffic_data: Dict[str, Any], city: str, rectangle: str) -> Dict[str, Any]:
        """格式化交通态势结果"""
        try:
            trafficinfo = traffic_data.get("trafficinfo", {})
            roads = trafficinfo.get("roads", [])
            
            if not roads:
                return {
                    "status": "success",
                    "message": f"查询区域内暂无交通态势数据",
                    "city": city,
                    "query_rectangle": rectangle,
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
            highway_roads = []  # 专门收集高速公路信息
            
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
                
                # 检查是否是高速公路
                road_name = road_info["name"]
                if any(keyword in road_name for keyword in ["高速", "快速路", "环线", "立交"]):
                    highway_roads.append(road_info)
                
                formatted_roads.append(road_info)
            
            # 生成交通状况总结
            total_roads = len(roads)
            congestion_rate = (traffic_stats["拥堵"] + traffic_stats["严重拥堵"]) / total_roads * 100 if total_roads > 0 else 0
            
            summary_text = f"{city}地区交通状况："
            if congestion_rate < 20:
                summary_text += "整体畅通"
            elif congestion_rate < 40:
                summary_text += "轻微拥堵"
            elif congestion_rate < 60:
                summary_text += "中度拥堵"
            else:
                summary_text += "严重拥堵"
            
            return {
                "status": "success",
                "message": "交通态势查询成功",
                "city": city,
                "query_rectangle": rectangle,
                "summary": summary_text,
                "congestion_rate": round(congestion_rate, 1),
                "road_count": total_roads,
                "traffic_summary": traffic_stats,
                "highway_roads": highway_roads[:10],  # 重点显示高速公路状况
                "roads": formatted_roads[:30],  # 限制返回道路数量
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