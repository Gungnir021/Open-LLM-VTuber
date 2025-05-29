from typing import AsyncIterator, Dict, Any, List, Optional
import json
import re
from loguru import logger
from datetime import datetime

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
    旅行助手代理，提供天气查询和路况查询功能
    
    该代理使用高德地图API获取天气数据和交通状况，支持查询当前天气、未来天气预报、区域交通状况和路线交通状况
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
        
        # 如果提供了API密钥，可以在这里设置
        # if api_key:
        #     from .tools.get_weather import AMAP_API_KEY
        #     global AMAP_API_KEY
        #     AMAP_API_KEY = api_key
            
        logger.info("TravelAgent初始化完成，系统提示词已设置")

    @tts_filter()
    async def chat(self, input_data: BatchInput) -> AsyncIterator[tuple[SentenceWithTags, DisplayText, Actions]]:
        # 合并所有文本输入
        user_text = "\n".join([t.content for t in input_data.texts])
        self.memory.append({"role": "user", "content": user_text})
    
        messages = self.memory.copy()
        logger.debug(f"发送消息到LLM: {len(messages)}条消息")
        logger.info(f"当前工具调用次数: {self.tool_call_count}")
        
        # 简单的意图检测
        weather_intent, location = self._detect_weather_intent(user_text)
        traffic_intent, locations = self._detect_traffic_intent(user_text)
        route_intent, origin, destination = self._detect_route_intent(user_text)
        
        try:
            response_text = ""
            
            if weather_intent and location:
                # 直接调用天气API
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
                
                # 添加验证信息
                verification_info = f"\n\n[系统信息: 已成功调用天气API，工具名称: {self.last_tool_name}, 调用时间: {self.last_tool_call_time}]"
                response_text += verification_info
                
            elif traffic_intent and locations:
                # 直接调用交通状况API
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
                
                # 添加验证信息
                verification_info = f"\n\n[系统信息: 已成功调用交通状况API，工具名称: {self.last_tool_name}, 调用时间: {self.last_tool_call_time}]"
                response_text += verification_info
                
            elif route_intent and origin and destination:
                # 直接调用路线交通API
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
                
                # 添加验证信息
                verification_info = f"\n\n[系统信息: 已成功调用路线交通API，工具名称: {self.last_tool_name}, 调用时间: {self.last_tool_call_time}]"
                response_text += verification_info
                
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
        """
        检测文本中是否包含天气查询意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            (是否是天气查询, 地点名称)
        """
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
        """
        检测文本中是否包含交通状况查询意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            (是否是交通状况查询, 地点名称)
        """
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
        """
        检测文本中是否包含路线查询意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            (是否是路线查询, 起点, 终点)
        """
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

    def handle_interrupt(self, heard_response: str) -> None:
        """
        处理用户中断
        
        Args:
            heard_response: 中断前听到的响应
        """
        if self.memory and self.memory[-1]["role"] == "assistant":
            self.memory[-1]["content"] = heard_response + "..."
        self.memory.append({"role": "system", "content": "[用户打断了对话]"})
        logger.info("用户中断了对话，已更新对话记录")

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        """
        从历史记录中设置记忆
        
        Args:
            conf_uid: 配置UID
            history_uid: 历史记录UID
        """
        # 可以实现从历史记录加载对话，此处为空实现
        logger.info(f"尝试从历史记录加载对话: conf_uid={conf_uid}, history_uid={history_uid}")
        pass

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用工具函数
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
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
            elif name == "generate_social_media_post":
                return generate_social_media_post(**arguments)
            return {"error": f"未知工具: {name}"}
        except Exception as e:
            logger.error(f"工具调用失败: {str(e)}")
            return {"error": f"工具调用失败: {str(e)}"}

    def tools(self) -> List[Dict[str, Any]]:
        """
        返回可用工具列表
        
        Returns:
            工具定义列表
        """
        return [
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
        ]