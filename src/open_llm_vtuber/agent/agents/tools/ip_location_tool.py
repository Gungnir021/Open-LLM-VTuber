import os
import json
import requests
import re
from typing import Dict, Any, Optional
from loguru import logger
from dotenv import load_dotenv
from .tool_base import ToolBase

# 加载环境变量
load_dotenv()
AMAP_API_KEY = os.getenv("AMAP_API_KEY")

class IPLocationTool(ToolBase):
    """IP定位查询工具"""
    
    @property
    def name(self) -> str:
        return "get_ip_location"
    
    @property
    def description(self) -> str:
        return "根据IP地址查询地理位置信息，包括省份、城市、行政区划代码等。支持国内IP地址查询，不填写IP则自动定位当前请求方位置"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "需要查询的IP地址（仅支持国内IP）。格式如：'114.247.50.2'。如果不填写，则自动定位当前请求方的IP位置",
                    "pattern": r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
                },
                "output": {
                    "type": "string",
                    "description": "返回数据格式，可选值：json、xml，默认为json",
                    "default": "json",
                    "enum": ["json", "xml"]
                }
            },
            "required": []
        }
    
    def execute(self, ip: str = None, output: str = "json") -> str:
        """执行IP定位查询"""
        try:
            # 验证API密钥
            if not AMAP_API_KEY:
                return json.dumps({"error": "未配置高德地图API密钥，请在.env文件中设置AMAP_API_KEY"}, ensure_ascii=False)
            
            # 验证IP地址格式（如果提供了IP）
            if ip and not self._validate_ip(ip):
                return json.dumps({"error": "IP地址格式错误，请提供有效的IPv4地址"}, ensure_ascii=False)
            
            # 验证输出格式
            if output.lower() not in ["json", "xml"]:
                return json.dumps({"error": "输出格式错误，仅支持json或xml"}, ensure_ascii=False)
            
            # 获取IP定位数据
            location_data = self._get_ip_location(ip, output.lower())
            if location_data.get("error"):
                return json.dumps(location_data, ensure_ascii=False)
            
            # 格式化返回结果
            formatted_result = self._format_location_result(location_data)
            return json.dumps(formatted_result, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"IP定位查询出错: {str(e)}")
            return json.dumps({"error": f"IP定位查询失败: {str(e)}"}, ensure_ascii=False)
    
    def _validate_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        try:
            # 使用正则表达式验证IPv4格式
            pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            if not re.match(pattern, ip):
                return False
            
            # 进一步验证每个段的范围
            parts = ip.split('.')
            for part in parts:
                if int(part) > 255:
                    return False
            
            # 排除一些特殊IP段
            first_octet = int(parts[0])
            # 排除私有IP段和特殊用途IP段
            if first_octet in [0, 127, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239]:
                return False
            
            return True
        except (ValueError, IndexError):
            return False
    
    def _get_ip_location(self, ip: str = None, output: str = "json") -> Dict[str, Any]:
        """获取IP定位数据"""
        try:
            # 构建请求参数
            params = {
                "key": AMAP_API_KEY,
                "output": output
            }
            
            # 如果提供了IP地址，则添加到参数中
            if ip:
                params["ip"] = ip
            
            logger.debug(f"IP定位API请求参数: {params}")
            
            response = requests.get(
                "https://restapi.amap.com/v3/ip",
                params=params,
                timeout=10
            )
            
            # 检查HTTP状态码
            response.raise_for_status()
            
            logger.debug(f"IP定位API响应状态码: {response.status_code}")
            logger.debug(f"IP定位API响应内容: {response.text}")
            
            # 根据输出格式解析响应
            if output == "json":
                location_data = response.json()
            else:  # xml格式
                return {"error": "XML格式解析暂未实现，请使用JSON格式"}
            
            # 检查API返回状态
            if location_data.get("status") != "1":
                error_msg = location_data.get("info", "未知错误")
                error_code = location_data.get("infocode", "")
                logger.error(f"高德地图API调用失败: {error_msg} (错误码: {error_code})")
                return {"error": f"API调用失败: {error_msg} (错误码: {error_code})"}
            
            return location_data
            
        except Exception as e:
            logger.error(f"获取IP定位数据时出错: {str(e)}")
            return {"error": f"获取IP定位数据时出错: {str(e)}"}
    
    def _format_location_result(self, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化IP定位结果"""
        try:
            # 提取基本信息 - 确保返回字符串而不是数组
            province = location_data.get("province", "")
            city = location_data.get("city", "")
            adcode = location_data.get("adcode", "")
            rectangle = location_data.get("rectangle", "")
            
            # 确保province和city是字符串类型
            if isinstance(province, list):
                province = province[0] if province else ""
            if isinstance(city, list):
                city = city[0] if city else ""
            
            # 解析矩形区域坐标
            rectangle_info = None
            if rectangle and isinstance(rectangle, str):
                try:
                    coords = rectangle.split(';')
                    if len(coords) == 2:
                        left_bottom = coords[0].split(',')
                        right_top = coords[1].split(',')
                        if len(left_bottom) == 2 and len(right_top) == 2:
                            rectangle_info = {
                                "left_bottom": {
                                    "longitude": float(left_bottom[0]),
                                    "latitude": float(left_bottom[1])
                                },
                                "right_top": {
                                    "longitude": float(right_top[0]),
                                    "latitude": float(right_top[1])
                                }
                            }
                except (ValueError, IndexError) as e:
                    logger.warning(f"解析矩形区域坐标失败: {rectangle}, 错误: {e}")
            
            # 判断位置类型
            location_type = "unknown"
            if province == "局域网":
                location_type = "local_network"
            elif not province or not city:
                location_type = "invalid_or_foreign"
            elif province == city:  # 直辖市
                location_type = "municipality"
            else:
                location_type = "normal"
            
            # 构建友好的位置描述
            location_description = ""
            if location_type == "local_network":
                location_description = "您当前使用的是局域网IP地址"
            elif location_type == "invalid_or_foreign":
                location_description = "无法定位您的具体位置，可能是国外IP或无效IP"
            elif location_type == "municipality":
                location_description = f"您当前位于{province}"
            elif location_type == "normal":
                location_description = f"您当前位于{province}{city}"
            
            return {
                "status": "success",
                "message": "IP定位查询成功",
                "location_info": {
                    "province": province,
                    "city": city,
                    "adcode": adcode,
                    "location_type": location_type,
                    "location_description": location_description,
                    "rectangle": rectangle,
                    "rectangle_parsed": rectangle_info
                },
                "raw_data": {
                    "status": location_data.get("status"),
                    "info": location_data.get("info"),
                    "infocode": location_data.get("infocode")
                }
            }
            
        except Exception as e:
            logger.error(f"格式化IP定位数据时出错: {str(e)}")
            return {"error": f"数据格式化失败: {str(e)}"}
    
    def get_current_location(self) -> str:
        """获取当前请求方的IP定位（不指定IP参数）"""
        return self.execute()
    
    def get_location_by_ip(self, ip: str) -> str:
        """根据指定IP获取定位信息"""
        return self.execute(ip=ip)