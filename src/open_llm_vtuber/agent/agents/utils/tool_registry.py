from typing import Dict, Any, List, Callable, Optional
from ..tools.get_weather import get_current_temperature, get_temperature_date
from ..tools.get_traffic import get_traffic_status, get_route_traffic
from ..tools.user_profile import UserProfileManager
from ..tools.trip_planner import generate_travel_itinerary, generate_packing_list
from ..tools.location_services import find_nearby_facilities, get_scenic_spot_info
from ..tools.image_analysis import analyze_travel_photo, generate_social_media_post

class ToolRegistry:
    """
    工具注册表，负责管理所有可用的工具函数
    """
    
    def __init__(self):
        """
        初始化工具注册表
        """
        self._tool_functions: Dict[str, Callable] = {
            "get_current_temperature": get_current_temperature,
            "get_temperature_date": get_temperature_date,
            "get_traffic_status": get_traffic_status,
            "get_route_traffic": get_route_traffic,
            "collect_user_info": self._collect_user_info,
            "generate_travel_itinerary": generate_travel_itinerary,
            "generate_packing_list": generate_packing_list,
            "find_nearby_facilities": find_nearby_facilities,
            "get_scenic_spot_info": get_scenic_spot_info,
            "analyze_travel_photo": analyze_travel_photo,
            "generate_social_media_post": generate_social_media_post
        }
        
        self._user_manager = UserProfileManager()
    
    def get_tool_function(self, name: str) -> Optional[Callable]:
        """
        获取工具函数
        
        Args:
            name: 工具名称
            
        Returns:
            工具函数或None
        """
        return self._tool_functions.get(name)
    
    def _collect_user_info(self, user_id: str, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        收集用户信息的包装函数
        
        Args:
            user_id: 用户ID
            info: 用户信息
            
        Returns:
            收集结果
        """
        return self._user_manager.collect_user_info(user_id, info)
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        获取所有工具定义
        
        Returns:
            工具定义列表
        """
        return [
            # 天气查询工具
            {
                "type": "function",
                "function": {
                    "name": "get_current_temperature",
                    "description": "获取指定地点当前的实时天气信息，包括温度、天气状况、湿度、风向和风力。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "需要查询天气的城市名称，例如 '北京', '上海市'。",
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "温度单位，'celsius' (摄氏度) 或 'fahrenheit' (华氏度)。默认为 'celsius'。",
                            },
                        },
                        "required": ["location"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_temperature_date",
                    "description": "获取指定地点和日期的天气预报。可以查询特定日期 (YYYY-MM-DD)、'明天' 或 '未来X天'（例如 '未来3天'）的天气。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "需要查询天气预报的城市名称，例如 '上海', '杭州市'。",
                            },
                            "date": {
                                "type": "string",
                                "description": "需要查询的日期。可以是 'YYYY-MM-DD' 格式的具体日期，也可以是 '明天'，或 '未来X天' (例如 '未来2天', '未来两天')这样的描述。",
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "温度单位，'celsius' (摄氏度) 或 'fahrenheit' (华氏度)。默认为 'celsius'。",
                            },
                        },
                        "required": ["location", "date"],
                    },
                },
            },
            # 交通查询工具
            {
                "type": "function",
                "function": {
                    "name": "get_traffic_status",
                    "description": "获取指定地点周围的实时交通状况，包括道路拥堵情况、畅通程度等信息。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "需要查询交通状况的地点名称，例如 '北京西站', '上海人民广场'。",
                            },
                            "radius": {
                                "type": "number",
                                "description": "查询半径，单位为公里，默认为2公里。",
                            },
                        },
                        "required": ["location"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_route_traffic",
                    "description": "获取两地之间的路线交通状况，包括距离、预计时间、拥堵情况等。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "origin": {
                                "type": "string",
                                "description": "起点名称，例如 '北京站', '上海虹桥机场'。",
                            },
                            "destination": {
                                "type": "string",
                                "description": "终点名称，例如 '北京大学', '上海外滩'。",
                            },
                        },
                        "required": ["origin", "destination"],
                    },
                },
            },
            # 用户信息管理工具
            {
                "type": "function",
                "function": {
                    "name": "collect_user_info",
                    "description": "收集和更新用户的旅行相关信息，包括旅行日期、饮食限制、偏好、预算和旅行风格等。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "用户ID，用于标识不同用户。",
                            },
                            "info": {
                                "type": "object",
                                "description": "用户信息对象，包含各种旅行相关信息。",
                                "properties": {
                                    "destination": {
                                        "type": "string",
                                        "description": "旅行目的地，例如 '北京', '杭州'。",
                                    },
                                    "travel_dates": {
                                        "type": "object",
                                        "description": "旅行日期范围。",
                                        "properties": {
                                            "start": {
                                                "type": "string",
                                                "description": "开始日期，格式为 'YYYY-MM-DD'。",
                                            },
                                            "end": {
                                                "type": "string",
                                                "description": "结束日期，格式为 'YYYY-MM-DD'。",
                                            },
                                        },
                                    },
                                    "dietary_restrictions": {
                                        "type": "array",
                                        "description": "饮食限制或禁忌，例如 '不吃猪肉', '素食', '过敏花生'。",
                                        "items": {
                                            "type": "string"
                                        },
                                    },
                                    "preferences": {
                                        "type": "array",
                                        "description": "旅行偏好，例如 '历史景点', '自然风光', '美食探索'。",
                                        "items": {
                                            "type": "string"
                                        },
                                    },
                                    "budget": {
                                        "type": "string",
                                        "description": "旅行预算，例如 '5000元', '经济型', '高端'。",
                                    },
                                    "travel_style": {
                                        "type": "string",
                                        "description": "旅行风格，例如 '休闲', '冒险', '文化'。",
                                    },
                                },
                            },
                        },
                        "required": ["user_id", "info"],
                    },
                },
            },
            # 行程规划工具
            {
                "type": "function",
                "function": {
                    "name": "generate_travel_itinerary",
                    "description": "根据目的地、日期、天气和用户偏好生成智能旅行路线规划。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {
                                "type": "string",
                                "description": "旅行目的地，例如 '北京', '杭州'。",
                            },
                            "start_date": {
                                "type": "string",
                                "description": "开始日期，格式为 'YYYY-MM-DD'。",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "结束日期，格式为 'YYYY-MM-DD'。",
                            },
                            "user_preferences": {
                                "type": "object",
                                "description": "用户偏好信息，包含饮食限制、活动偏好等。",
                            },
                        },
                        "required": ["destination", "start_date", "end_date", "user_preferences"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_packing_list",
                    "description": "根据目的地、旅行日期、天气情况和用户风格生成出行物品清单。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "destination": {
                                "type": "string",
                                "description": "旅行目的地，例如 '北京', '杭州'。",
                            },
                            "travel_dates": {
                                "type": "array",
                                "description": "旅行日期列表，包含开始和结束日期。",
                                "items": {
                                    "type": "string"
                                },
                            },
                            "weather_info": {
                                "type": "object",
                                "description": "目的地天气信息。",
                            },
                            "user_style": {
                                "type": "string",
                                "description": "用户旅行风格，例如 '休闲', '冒险', '商务'。",
                            },
                        },
                        "required": ["destination", "travel_dates", "weather_info", "user_style"],
                    },
                },
            },
            # 位置服务工具
            {
                "type": "function",
                "function": {
                    "name": "find_nearby_facilities",
                    "description": "查找附近的设施，如洗手间、休息点、商场、餐厅等。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "当前位置的坐标（经度,纬度）或地点名称。",
                            },
                            "facility_type": {
                                "type": "string",
                                "description": "设施类型，例如 '洗手间', '休息点', '商场', '餐厅', '医院'。",
                            },
                            "radius": {
                                "type": "integer",
                                "description": "搜索半径，单位为米，默认为1000米。",
                            },
                        },
                        "required": ["location", "facility_type"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_scenic_spot_info",
                    "description": "获取景点的详细信息和讲解内容。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "景点名称，例如 '故宫', '西湖'。",
                            },
                        },
                        "required": ["location"],
                    },
                },
            },
            # 图片分析工具
            {
                "type": "function",
                "function": {
                    "name": "analyze_travel_photo",
                    "description": "分析旅行照片内容，识别照片中的景点、物体、场景和氛围等。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_data": {
                                "type": "string",
                                "description": "图片数据，Base64编码或图片URL。",
                            },
                        },
                        "required": ["image_data"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_social_media_post",
                    "description": "根据旅行信息和照片分析生成社交媒体文案。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "trip_info": {
                                "type": "object",
                                "description": "旅行信息，包含目的地、亮点等。",
                            },
                            "photos_analysis": {
                                "type": "array",
                                "description": "照片分析结果列表。",
                                "items": {
                                    "type": "object"
                                },
                            },
                        },
                        "required": ["trip_info"],
                    },
                },
            },
        ]