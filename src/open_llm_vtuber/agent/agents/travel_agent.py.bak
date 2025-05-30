from typing import AsyncIterator, Dict, Any, List, Optional, Union
import json
import re
from loguru import logger
from datetime import datetime, timedelta

from .agent_interface import AgentInterface
from ..input_types import BatchInput
from ..output_types import SentenceOutput, DisplayText, Actions
from ...utils.sentence_divider import SentenceWithTags
from ...config_manager import TTSPreprocessorConfig
from ..transformers import tts_filter
from ..stateless_llm.stateless_llm_interface import StatelessLLMInterface
from .tools.get_weather import get_current_temperature, get_temperature_date
from .tools.get_traffic import get_traffic_status, get_route_traffic
from .tools.user_profile import UserProfileManager
from .tools.trip_planner import generate_travel_itinerary, generate_packing_list
from .tools.location_services import find_nearby_facilities, get_scenic_spot_info
from .tools.image_analysis import analyze_travel_photo, generate_social_media_post

class TravelAgent(AgentInterface):
    """
    旅行助手代理，提供全方位旅行服务
    
    该代理提供旅行前、旅行中和旅行后的全流程服务，包括：
    - 旅行前：用户信息收集、旅行计划制定、天气路况预报、出行清单生成
    - 旅行中：实时讲解、周边设施查询
    - 旅行后：社交媒体内容生成、用户反馈收集
    """
    
    def __init__(self, llm: StatelessLLMInterface, system_prompt: str, api_key: str = None, tts_preprocessor_config: TTSPreprocessorConfig = None):
        """
        初始化旅行助手代理
        
        Args:
            llm: 无状态LLM接口实例
            system_prompt: 系统提示词
            api_key: 可选的高德地图API密钥，如果提供则覆盖默认值
            tts_preprocessor_config: TTS预处理器配置
        """
        self.llm = llm
        self.system_prompt = system_prompt
        self._tts_preprocessor_config = tts_preprocessor_config
        self.memory = [
            {"role": "system", "content": self.system_prompt}
        ]
        self.tool_call_count = 0  # 工具调用计数器
        self.last_tool_call_time = None  # 最后一次工具调用时间
        self.last_tool_name = None  # 最后一次调用的工具名称
        self.last_tool_args = None  # 最后一次调用的工具参数
        self.user_manager = UserProfileManager()
        self.current_user_id = "default"  # 当前用户ID
        
        # 如果提供了API密钥，设置到天气和交通工具中
        if api_key:
            global AMAP_API_KEY, TRAFFIC_AMAP_API_KEY
            from .tools.get_weather import AMAP_API_KEY
            from .tools.get_traffic import AMAP_API_KEY as TRAFFIC_AMAP_API_KEY
            AMAP_API_KEY = api_key
            TRAFFIC_AMAP_API_KEY = api_key
            
        logger.info("TravelAgent初始化完成，系统提示词已设置")

    @tts_filter()
    async def chat(self, input_data: BatchInput) -> AsyncIterator[tuple[SentenceWithTags, DisplayText, Actions]]:
        # 合并所有文本输入
        user_text = "\n".join([t.content for t in input_data.texts])
        self.memory.append({"role": "user", "content": user_text})
    
        messages = self.memory.copy()
        logger.debug(f"发送消息到LLM: {len(messages)}条消息")
        logger.info(f"当前工具调用次数: {self.tool_call_count}")
        
        # 处理图片输入
        image_data = None
        if input_data.images and len(input_data.images) > 0:
            # 获取第一张图片的数据
            image_data = input_data.images[0].data
            logger.info("检测到图片输入，将进行图片分析")
        
        try:
            response_text = ""
            
            # 简单的意图检测
            weather_intent, location = self._detect_weather_intent(user_text)
            traffic_intent, locations = self._detect_traffic_intent(user_text)
            route_intent, origin, destination = self._detect_route_intent(user_text)
            nearby_intent, facility_type = self._detect_nearby_facility_intent(user_text)
            itinerary_intent = self._detect_itinerary_intent(user_text)
            packing_intent = self._detect_packing_intent(user_text)
            social_media_intent = self._detect_social_media_intent(user_text)
            user_info_intent = self._detect_user_info_intent(user_text)
            scenic_info_intent, spot_name = self._detect_scenic_info_intent(user_text)
            
            # 处理图片分析请求
            if image_data and ("分析" in user_text or "识别" in user_text or "照片" in user_text or "图片" in user_text):
                logger.info("处理图片分析请求")
                
                # 记录工具调用信息
                self.tool_call_count += 1
                self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.last_tool_name = "analyze_travel_photo"
                self.last_tool_args = {"image_data": "[图片数据]"}
                
                # 调用图片分析工具
                photo_analysis = self.call_tool("analyze_travel_photo", {"image_data": image_data})
                
                # 将工具结果添加到记忆中
                self.memory.append({
                    "role": "tool",
                    "name": "analyze_travel_photo",
                    "content": json.dumps(photo_analysis, ensure_ascii=False),
                })
                
                # 如果同时检测到社交媒体意图，生成朋友圈文案
                if social_media_intent:
                    # 获取用户信息
                    user_profile = self.user_manager.get_user_profile(self.current_user_id)
                    
                    # 记录工具调用信息
                    self.tool_call_count += 1
                    self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.last_tool_name = "generate_social_media_post"
                    self.last_tool_args = {"trip_info": user_profile, "photos_analysis": [photo_analysis]}
                    
                    # 调用社交媒体文案生成工具
                    social_media_result = self.call_tool("generate_social_media_post", {
                        "trip_info": user_profile,
                        "photos_analysis": [photo_analysis]
                    })
                    
                    # 将工具结果添加到记忆中
                    self.memory.append({
                        "role": "tool",
                        "name": "generate_social_media_post",
                        "content": json.dumps(social_media_result, ensure_ascii=False),
                    })
                
                # 使用LLM生成最终回答
                async for chunk in self.llm.chat_completion(messages=self.memory):
                    response_text += chunk
                
            # 处理天气查询
            elif weather_intent and location:
                logger.info(f"检测到天气查询意图，地点: {location}")
                
                # 记录工具调用信息
                self.tool_call_count += 1
                self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.last_tool_name = "get_current_temperature"
                self.last_tool_args = {"location": location}
                
                # 调用天气API
                weather_result = self.call_tool("get_current_temperature", {"location": location})
                
                # 将工具结果添加到记忆中
                self.memory.append({
                    "role": "tool",
                    "name": "get_current_temperature",
                    "content": json.dumps(weather_result, ensure_ascii=False),
                })
                
                # 使用LLM生成最终回答
                async for chunk in self.llm.chat_completion(messages=self.memory):
                    response_text += chunk
            
            # 处理交通状况查询
            elif traffic_intent and locations:
                logger.info(f"检测到交通状况查询意图，地点: {locations}")
                
                # 记录工具调用信息
                self.tool_call_count += 1
                self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.last_tool_name = "get_traffic_status"
                self.last_tool_args = {"location": locations}
                
                # 调用交通状况API
                traffic_result = self.call_tool("get_traffic_status", {"location": locations})
                
                # 将工具结果添加到记忆中
                self.memory.append({
                    "role": "tool",
                    "name": "get_traffic_status",
                    "content": json.dumps(traffic_result, ensure_ascii=False),
                })
                
                # 使用LLM生成最终回答
                async for chunk in self.llm.chat_completion(messages=self.memory):
                    response_text += chunk
            
            # 处理路线查询
            elif route_intent and origin and destination:
                logger.info(f"检测到路线查询意图，起点: {origin}，终点: {destination}")
                
                # 记录工具调用信息
                self.tool_call_count += 1
                self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.last_tool_name = "get_route_traffic"
                self.last_tool_args = {"origin": origin, "destination": destination}
                
                # 调用路线交通API
                route_result = self.call_tool("get_route_traffic", {"origin": origin, "destination": destination})
                
                # 将工具结果添加到记忆中
                self.memory.append({
                    "role": "tool",
                    "name": "get_route_traffic",
                    "content": json.dumps(route_result, ensure_ascii=False),
                })
                
                # 使用LLM生成最终回答
                async for chunk in self.llm.chat_completion(messages=self.memory):
                    response_text += chunk
            
            # 处理附近设施查询
            elif nearby_intent and facility_type:
                logger.info(f"检测到附近设施查询意图，设施类型: {facility_type}")
                
                # 记录工具调用信息
                self.tool_call_count += 1
                self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.last_tool_name = "find_nearby_facilities"
                self.last_tool_args = {"location": "当前位置", "facility_type": facility_type}
                
                # 调用附近设施查询API
                # 注意：这里需要获取用户当前位置，暂时使用固定值
                current_location = "116.397428,39.909187"  # 默认位置（北京天安门）
                nearby_result = self.call_tool("find_nearby_facilities", {
                    "location": current_location,
                    "facility_type": facility_type
                })
                
                # 将工具结果添加到记忆中
                self.memory.append({
                    "role": "tool",
                    "name": "find_nearby_facilities",
                    "content": json.dumps(nearby_result, ensure_ascii=False),
                })
                
                # 使用LLM生成最终回答
                async for chunk in self.llm.chat_completion(messages=self.memory):
                    response_text += chunk
            
            # 处理行程规划请求
            elif itinerary_intent:
                logger.info("检测到行程规划请求")
                
                # 获取用户信息
                user_profile = self.user_manager.get_user_profile(self.current_user_id)
                
                if not user_profile or not user_profile.get("travel_dates") or not user_profile.get("preferences"):
                    response_text = "我需要先收集一些基本信息才能为您规划行程。请告诉我您的旅行目的地、出发日期、返回日期以及您的偏好（如喜欢的活动、饮食限制等）。"
                else:
                    # 记录工具调用信息
                    self.tool_call_count += 1
                    self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.last_tool_name = "generate_travel_itinerary"
                    
                    # 从用户信息中提取必要参数
                    destination = user_profile.get("destination", "未知目的地")
                    travel_dates = user_profile.get("travel_dates", {})
                    start_date = travel_dates.get("start", datetime.now().strftime("%Y-%m-%d"))
                    end_date = travel_dates.get("end", (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"))
                    
                    self.last_tool_args = {
                        "destination": destination,
                        "start_date": start_date,
                        "end_date": end_date,
                        "user_preferences": user_profile
                    }
                    
                    # 调用行程规划工具
                    itinerary_result = self.call_tool("generate_travel_itinerary", {
                        "destination": destination,
                        "start_date": start_date,
                        "end_date": end_date,
                        "user_preferences": user_profile
                    })
                    
                    # 将工具结果添加到记忆中
                    self.memory.append({
                        "role": "tool",
                        "name": "generate_travel_itinerary",
                        "content": json.dumps(itinerary_result, ensure_ascii=False),
                    })
                    
                    # 使用LLM生成最终回答
                    async for chunk in self.llm.chat_completion(messages=self.memory):
                        response_text += chunk
            
            # 处理出行清单请求
            elif packing_intent:
                logger.info("检测到出行清单请求")
                
                # 获取用户信息
                user_profile = self.user_manager.get_user_profile(self.current_user_id)
                
                if not user_profile or not user_profile.get("travel_dates") or not user_profile.get("destination"):
                    response_text = "我需要先收集一些基本信息才能为您生成出行清单。请告诉我您的旅行目的地、出发日期、返回日期以及您的旅行风格。"
                else:
                    # 记录工具调用信息
                    self.tool_call_count += 1
                    self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.last_tool_name = "generate_packing_list"
                    
                    # 从用户信息中提取必要参数
                    destination = user_profile.get("destination", "未知目的地")
                    travel_dates = user_profile.get("travel_dates", {})
                    travel_style = user_profile.get("travel_style", "休闲")
                    
                    # 获取目的地天气信息
                    weather_info = self.call_tool("get_current_temperature", {"location": destination})
                    
                    self.last_tool_args = {
                        "destination": destination,
                        "travel_dates": [travel_dates.get("start"), travel_dates.get("end")],
                        "weather_info": weather_info,
                        "user_style": travel_style
                    }
                    
                    # 调用出行清单生成工具
                    packing_result = self.call_tool("generate_packing_list", {
                        "destination": destination,
                        "travel_dates": [travel_dates.get("start"), travel_dates.get("end")],
                        "weather_info": weather_info,
                        "user_style": travel_style
                    })
                    
                    # 将工具结果添加到记忆中
                    self.memory.append({
                        "role": "tool",
                        "name": "generate_packing_list",
                        "content": json.dumps(packing_result, ensure_ascii=False),
                    })
                    
                    # 使用LLM生成最终回答
                    async for chunk in self.llm.chat_completion(messages=self.memory):
                        response_text += chunk
            
            # 处理用户信息收集
            elif user_info_intent:
                logger.info("检测到用户信息收集请求")
                
                # 从用户文本中提取信息
                user_info = self._extract_user_info(user_text)
                
                if user_info:
                    # 记录工具调用信息
                    self.tool_call_count += 1
                    self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.last_tool_name = "collect_user_info"
                    self.last_tool_args = {"user_id": self.current_user_id, "info": user_info}
                    
                    # 调用用户信息收集工具
                    info_result = self.call_tool("collect_user_info", {
                        "user_id": self.current_user_id,
                        "info": user_info
                    })
                    
                    # 将工具结果添加到记忆中
                    self.memory.append({
                        "role": "tool",
                        "name": "collect_user_info",
                        "content": json.dumps(info_result, ensure_ascii=False),
                    })
                    
                    # 使用LLM生成最终回答
                    async for chunk in self.llm.chat_completion(messages=self.memory):
                        response_text += chunk
                else:
                    response_text = "我需要收集一些信息来为您提供更好的服务。请告诉我您的旅行目的地、出发日期、返回日期、饮食限制（如有）、预算和旅行风格。"
            
            # 处理景点信息查询
            elif scenic_info_intent and spot_name:
                logger.info(f"检测到景点信息查询意图，景点: {spot_name}")
                
                # 记录工具调用信息
                self.tool_call_count += 1
                self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.last_tool_name = "get_scenic_spot_info"
                self.last_tool_args = {"location": spot_name}
                
                # 调用景点信息查询工具
                scenic_result = self.call_tool("get_scenic_spot_info", {"location": spot_name})
                
                # 将工具结果添加到记忆中
                self.memory.append({
                    "role": "tool",
                    "name": "get_scenic_spot_info",
                    "content": json.dumps(scenic_result, ensure_ascii=False),
                })
                
                # 使用LLM生成最终回答
                async for chunk in self.llm.chat_completion(messages=self.memory):
                    response_text += chunk
            
            # 处理社交媒体文案生成（无图片情况）
            elif social_media_intent and not image_data:
                logger.info("检测到社交媒体文案生成请求（无图片）")
                
                # 获取用户信息
                user_profile = self.user_manager.get_user_profile(self.current_user_id)
                
                if not user_profile or not user_profile.get("destination"):
                    response_text = "我需要先了解您的旅行信息才能生成朋友圈文案。请告诉我您去了哪里旅行，或者上传一张旅行照片。"
                else:
                    # 记录工具调用信息
                    self.tool_call_count += 1
                    self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.last_tool_name = "generate_social_media_post"
                    self.last_tool_args = {"trip_info": user_profile, "photos_analysis": []}
                    
                    # 调用社交媒体文案生成工具
                    social_media_result = self.call_tool("generate_social_media_post", {
                        "trip_info": user_profile,
                        "photos_analysis": []
                    })
                    
                    # 将工具结果添加到记忆中
                    self.memory.append({
                        "role": "tool",
                        "name": "generate_social_media_post",
                        "content": json.dumps(social_media_result, ensure_ascii=False),
                    })
                    
                    # 使用LLM生成最终回答
                    async for chunk in self.llm.chat_completion(messages=self.memory):
                        response_text += chunk
            
            else:
                # 常规LLM对话
                logger.info("未检测到明确的查询意图，使用常规对话")
                async for chunk in self.llm.chat_completion(messages=messages):
                    response_text += chunk
            
            # 将回答添加到记忆中
            self.memory.append({"role": "assistant", "content": response_text})
            
            # 创建显示文本对象和句子对象
            display_text = DisplayText(text=response_text, name="旅行助手")
            sentence = SentenceWithTags(text=response_text, tags=[])
            
            # 返回元组格式以配合tts_filter装饰器
            yield sentence, display_text, Actions()
            
        except Exception as e:
            logger.error(f"处理聊天请求时出错: {str(e)}")
            error_msg = f"抱歉，处理您的请求时出现了问题: {str(e)}"
            display_text = DisplayText(text=error_msg, name="旅行助手")
            sentence = SentenceWithTags(text=error_msg, tags=[])
            yield sentence, display_text, Actions()

    def _detect_weather_intent(self, text: str) -> tuple[bool, Optional[str]]:
        """检测文本中是否包含天气查询意图"""
        # 简单的正则表达式匹配天气查询意图
        weather_patterns = [
            r'(.*?)(?:的|在|at|in)\s*(.+?)(?:的|)\s*(?:天气|weather)(?:怎么样|如何|情况|forecast|report|condition)',
            r'(.+?)(?:今天|today|现在|now|当前|current)(?:的|)\s*(?:天气|weather)',
            r'(?:天气|weather)(?:怎么样|如何|情况|forecast|report|condition)(?:.*?)(?:在|at|in)\s*(.+)'
        ]
        
        for pattern in weather_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # 提取地点名称
                groups = match.groups()
                location = next((g for g in groups if g and len(g.strip()) > 0), None)
                if location:
                    return True, location.strip()
        
        return False, None

    def _detect_traffic_intent(self, text: str) -> tuple[bool, Optional[str]]:
        """检测文本中是否包含交通状况查询意图"""
        # 简单的正则表达式匹配交通状况查询意图
        traffic_patterns = [
            r'(.*?)(?:的|在|at|in)\s*(.+?)(?:的|)\s*(?:交通|路况|traffic)(?:怎么样|如何|情况|condition|status)',
            r'(.+?)(?:现在|now|当前|current)(?:的|)\s*(?:交通|路况|traffic)',
            r'(?:交通|路况|traffic)(?:怎么样|如何|情况|condition|status)(?:.*?)(?:在|at|in)\s*(.+)'
        ]
        
        for pattern in traffic_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # 提取地点名称
                groups = match.groups()
                location = next((g for g in groups if g and len(g.strip()) > 0), None)
                if location:
                    return True, location.strip()
        
        return False, None

    def _detect_route_intent(self, text: str) -> tuple[bool, Optional[str], Optional[str]]:
        """检测文本中是否包含路线查询意图"""
        # 简单的正则表达式匹配路线查询意图
        route_patterns = [
            r'(?:从|from)\s*(.+?)\s*(?:到|去|至|to)\s*(.+?)\s*(?:怎么走|路线|route|path|way)',
            r'(?:从|from)\s*(.+?)\s*(?:到|去|至|to)\s*(.+?)\s*(?:的|)(?:交通|路况|traffic)',
            r'(.+?)\s*(?:到|去|至|to)\s*(.+?)\s*(?:怎么走|路线|route|path|way)'
        ]
        
        for pattern in route_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and len(match.groups()) >= 2:
                origin = match.group(1).strip() if match.group(1) else None
                destination = match.group(2).strip() if match.group(2) else None
                if origin and destination:
                    return True, origin, destination
        
        return False, None, None

    def _detect_nearby_facility_intent(self, text: str) -> tuple[bool, Optional[str]]:
        """检测文本中是否包含附近设施查询意图"""
        # 简单的正则表达式匹配附近设施查询意图
        facility_patterns = [
            r'(?:附近|周边|nearby|around)(?:的|)\s*(.+?)(?:在哪|在哪里|where)',
            r'(?:最近的|nearest|closest)\s*(.+?)(?:在哪|在哪里|where)',
            r'(?:找|查找|寻找|find|search)\s*(?:附近|周边|nearby|around)(?:的|)\s*(.+)',
            r'(?:哪里有|where.*?)\s*(.+?)'
        ]
        
        # 设施类型关键词
        facility_keywords = {
            "洗手间": ["洗手间", "厕所", "卫生间", "toilet", "restroom", "bathroom"],
            "休息点": ["休息点", "休息区", "休息处", "rest area", "lounge"],
            "商场": ["商场", "购物中心", "mall", "shopping center"],
            "餐厅": ["餐厅", "饭店", "吃饭的地方", "restaurant", "dining"],
            "医院": ["医院", "诊所", "医疗中心", "hospital", "clinic", "medical center"]
        }
        
        for pattern in facility_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                facility = match.group(1).strip() if match.group(1) else None
                if facility:
                    # 匹配设施类型
                    for facility_type, keywords in facility_keywords.items():
                        if any(keyword in facility for keyword in keywords):
                            return True, facility_type
                    # 如果没有匹配到预定义类型，直接返回用户输入的设施类型
                    return True, facility
        
        # 直接检查文本中是否包含设施关键词
        for facility_type, keywords in facility_keywords.items():
            if any(keyword in text for keyword in keywords):
                return True, facility_type
        
        return False, None

    def _detect_itinerary_intent(self, text: str) -> bool:
        """检测文本中是否包含行程规划意图"""
        itinerary_keywords = [
            "行程", "规划", "计划", "安排", "itinerary", "plan", "schedule",
            "旅行计划", "旅游计划", "travel plan", "trip plan"
        ]
        
        return any(keyword in text for keyword in itinerary_keywords)

    def _detect_packing_intent(self, text: str) -> bool:
        """检测文本中是否包含出行清单意图"""
        packing_keywords = [
            "出行清单", "行李清单", "带什么", "携带物品", "packing list", "what to bring",
            "行李", "物品", "装备", "luggage", "items", "gear"
        ]
        
        return any(keyword in text for keyword in packing_keywords)

    def _detect_social_media_intent(self, text: str) -> bool:
        """检测文本中是否包含社交媒体文案生成意图"""
        social_media_keywords = [
            "朋友圈", "文案", "发布", "分享", "social media", "post", "caption",
            "微信", "微博", "小红书", "wechat", "weibo", "xiaohongshu"
        ]
        
        return any(keyword in text for keyword in social_media_keywords)

    def _detect_user_info_intent(self, text: str) -> bool:
        """检测文本中是否包含用户信息收集意图"""
        user_info_keywords = [
            "个人信息", "旅行信息", "基本信息", "personal info", "travel info",
            "我要去", "我计划去", "我打算去", "I'm going to", "I plan to"
        ]
        
        return any(keyword in text for keyword in user_info_keywords)

    def _detect_scenic_info_intent(self, text: str) -> tuple[bool, Optional[str]]:
        """检测文本中是否包含景点信息查询意图"""
        scenic_patterns = [
            r'(?:介绍|讲解|tell me about|explain)\s*(.+?)(?:的|)\s*(?:景点|景区|名胜|attraction|scenic spot)',
            r'(.+?)(?:景点|景区|名胜|attraction|scenic spot)(?:的|)\s*(?:介绍|讲解|information|details)',
            r'(?:了解|知道|learn about|know about)\s*(.+?)'
        ]
        
        for pattern in scenic_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                spot_name = match.group(1).strip() if match.group(1) else None
                if spot_name:
                    return True, spot_name
        
        return False, None

    def _extract_user_info(self, text: str) -> Dict:
        """从用户文本中提取旅行相关信息"""
        info = {}
        
        # 提取目的地
        destination_patterns = [
            r'(?:去|到|前往|目的地|destination)\s*(?:是|)\s*(.+?)(?:旅行|旅游|玩|travel|tour|visit)',
            r'(?:计划|打算|准备|plan|going to)\s*(?:去|到|前往|visit|travel to)\s*(.+?)'
        ]
        
        for pattern in destination_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                destination = match.group(1).strip()
                if destination:
                    info["destination"] = destination
                    break
        
        # 提取旅行日期
        date_patterns = [
            r'(?:从|出发|start|from)\s*(.+?)(?:到|至|to|until)\s*(.+?)(?:旅行|旅游|travel|tour)',
            r'(?:旅行|旅游|travel|tour)\s*(?:时间|日期|date|period)\s*(?:是|为|:)\s*(.+?)(?:到|至|to|until)\s*(.+?)'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and len(match.groups()) >= 2:
                start_date = match.group(1).strip()
                end_date = match.group(2).strip()
                if start_date and end_date:
                    info["travel_dates"] = {"start": start_date, "end": end_date}
                    break
        
        # 提取饮食限制
        dietary_patterns = [
            r'(?:饮食限制|饮食禁忌|dietary restrictions|food restrictions)\s*(?:是|为|:)\s*(.+?)(?:\.|,|，|。|$)',
            r'(?:不能吃|不吃|cannot eat|don\'t eat)\s*(.+?)(?:\.|,|，|。|$)'
        ]
        
        dietary_restrictions = []
        for pattern in dietary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                restriction = match.group(1).strip()
                if restriction:
                    dietary_restrictions.append(restriction)
        
        if dietary_restrictions:
            info["dietary_restrictions"] = dietary_restrictions
        
        # 提取预算
        budget_patterns = [
            r'(?:预算|budget)\s*(?:是|为|:)\s*(.+?)(?:\.|,|，|。|$)',
            r'(?:计划花费|打算花费|plan to spend|expect to spend)\s*(.+?)(?:\.|,|，|。|$)'
        ]
        
        for pattern in budget_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                budget = match.group(1).strip()
                if budget:
                    info["budget"] = budget
                    break
        
        # 提取旅行风格
        style_patterns = [
            r'(?:旅行风格|travel style)\s*(?:是|为|:)\s*(.+?)(?:\.|,|，|。|$)',
            r'(?:喜欢|偏好|prefer|like)\s*(.+?)(?:风格|类型|style|type)(?:的|)(?:旅行|旅游|travel|tour)'
        ]
        
        for pattern in style_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                style = match.group(1).strip()
                if style:
                    info["travel_style"] = style
                    break
        
        # 提取偏好
        preference_patterns = [
            r'(?:喜欢|偏好|prefer|like)\s*(.+?)(?:\.|,|，|。|$)',
            r'(?:对|)\s*(.+?)\s*(?:感兴趣|interested in)'
        ]
        
        preferences = []
        for pattern in preference_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                preference = match.group(1).strip()
                if preference and "旅行风格" not in preference and "travel style" not in preference.lower():
                    preferences.append(preference)
        
        if preferences:
            info["preferences"] = preferences
        
        return info

    def handle_interrupt(self, heard_response: str) -> None:
        """处理用户中断"""
        if self.memory and self.memory[-1]["role"] == "assistant":
            self.memory[-1]["content"] = heard_response + "..."
        self.memory.append({"role": "system", "content": "[用户打断了对话]"})
        logger.info("用户中断了对话，已更新对话记录")

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        """从历史记录中设置记忆"""
        # 可以实现从历史记录加载对话，此处为空实现
        logger.info(f"尝试从历史记录加载对话: conf_uid={conf_uid}, history_uid={history_uid}")
        pass

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具函数"""
        logger.debug(f"调用工具: {name} 参数: {arguments}")
        try:
            if name == "get_current_temperature":
                return get_current_temperature(**arguments)
            elif name == "get_temperature_date":
                return get_temperature_date(**arguments)
            elif name == "get_traffic_status":
                return get_traffic_status(**arguments)
            elif name == "get_route_traffic":
                return get_route_traffic(**arguments)
            elif name == "collect_user_info":
                return self.user_manager.collect_user_info(**arguments)
            elif name == "generate_travel_itinerary":
                return generate_travel_itinerary(**arguments)
            elif name == "generate_packing_list":
                return generate_packing_list(**arguments)
            elif name == "find_nearby_facilities":
                return find_nearby_facilities(**arguments)
            elif name == "get_scenic_spot_info":
                return get_scenic_spot_info(**arguments)
            elif name == "analyze_travel_photo":
                return analyze_travel_photo(**arguments)
            elif name == "generate_social_media_post":
                return generate_social_media_post(**arguments)
            return {"error": f"未知工具: {name}"}
        except Exception as e:
            logger.error(f"工具调用失败: {str(e)}")
            return {"error": f"工具调用失败: {str(e)}"}

    def tools(self) -> List[Dict[str, Any]]:
        """返回可用工具列表"""
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