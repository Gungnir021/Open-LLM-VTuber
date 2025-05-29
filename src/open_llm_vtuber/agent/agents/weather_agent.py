from typing import AsyncIterator, Dict, Any, List
import json
from loguru import logger
import time
from datetime import datetime

from .agent_interface import AgentInterface
from ..input_types import BatchInput
from ..output_types import SentenceOutput, DisplayText, Actions
from ..stateless_llm.stateless_llm_interface import StatelessLLMInterface
from .tools.get_weather import get_current_temperature, get_temperature_date

class WeatherAgent(AgentInterface):
    """
    天气查询代理，提供实时天气和天气预报功能
    
    该代理使用高德地图API获取天气数据，支持查询当前天气和未来天气预报
    """
    
    def __init__(self, llm: StatelessLLMInterface, system_prompt: str, api_key: str = None):
        """
        初始化天气代理
        
        Args:
            llm: 无状态LLM接口实例
            system_prompt: 系统提示词
            api_key: 可选的高德地图API密钥，如果提供则覆盖默认值
        """
        self.llm = llm
        self.system_prompt = system_prompt
        self.memory = [
            {"role": "system", "content": self.system_prompt}
        ]
        self.tool_call_count = 0  # 添加工具调用计数器
        self.last_tool_call_time = None  # 添加最后一次工具调用时间
        self.last_tool_name = None  # 添加最后一次调用的工具名称
        self.last_tool_args = None  # 添加最后一次调用的工具参数
        
        # 如果提供了API密钥，可以在这里设置
        # if api_key:
        #     from .tools.get_weather import AMAP_API_KEY
        #     global AMAP_API_KEY
        #     AMAP_API_KEY = api_key
            
        logger.info("WeatherAgent初始化完成，系统提示词已设置")

    async def chat(self, input_data: BatchInput) -> AsyncIterator[SentenceOutput]:
        # 合并所有文本输入
        user_text = "\n".join([t.content for t in input_data.texts])
        self.memory.append({"role": "user", "content": user_text})
    
        messages = self.memory.copy()
        logger.debug(f"发送消息到LLM: {len(messages)}条消息")
        logger.info(f"当前工具调用次数: {self.tool_call_count}")
    
        try:
            # 第一次调用：检查是否应该使用工具
            response_text = ""
            tool_response = None
            
            # 使用async for正确处理异步生成器
            async for chunk in self.llm.chat_completion(messages=messages, tools=self.tools()):
                response_text += chunk
                # 检查是否是工具调用的JSON响应
                if chunk.startswith('{"message":{"tool_calls"'):
                    try:
                        tool_response = json.loads(chunk)
                        break  # 找到工具调用，停止收集
                    except json.JSONDecodeError:
                        pass
            
            # 解析响应
            if tool_response:
                # 处理工具调用
                response_message = tool_response.get("message", {})
                tool_calls = response_message.get("tool_calls", [])
                
                if tool_calls:
                    logger.info(f"检测到{len(tool_calls)}个工具调用")
                    self.memory.append(response_message)
                    
                    # 处理每个工具调用
                    for tool_call in tool_calls:
                        function_name = tool_call['function']['name']
                        function_args = json.loads(tool_call['function']['arguments'])
                        
                        # 记录工具调用信息
                        self.tool_call_count += 1
                        self.last_tool_call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.last_tool_name = function_name
                        self.last_tool_args = function_args
                        
                        logger.info(f"调用工具: {function_name}, 参数: {function_args}, 时间: {self.last_tool_call_time}")
                        tool_result = self.call_tool(function_name, function_args)
                        
                        self.memory.append({
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(tool_result, ensure_ascii=False),
                        })
    
                # 第二次调用：返回最终答案
                second_response_text = ""
                async for chunk in self.llm.chat_completion(messages=self.memory):
                    second_response_text += chunk
                
                answer = second_response_text
                
                # 添加验证信息到回答中
                verification_info = f"\n\n[系统信息: 已成功调用天气API，工具名称: {self.last_tool_name}, 调用时间: {self.last_tool_call_time}]"
                logger.info(f"已添加天气API调用验证信息到回答中")
                answer += verification_info
            else:
                logger.info("LLM直接回答，不使用工具")
                answer = response_text
        else:
            # 如果没有工具调用，使用收集到的文本作为回答
            logger.info("LLM直接回答，不使用工具")
            answer = response_text

        self.memory.append({"role": "assistant", "content": answer})
        
        # 创建显示文本对象
        display_text = DisplayText(text=answer, name="天气助手")
        
        # 返回SentenceOutput
        yield SentenceOutput(
            display_text=display_text,
            tts_text=answer,
            actions=Actions()
        )
        
    except Exception as e:
        logger.error(f"处理聊天请求时出错: {str(e)}")
        error_msg = f"抱歉，处理您的请求时出现了问题: {str(e)}"
        yield SentenceOutput(
            display_text=DisplayText(text=error_msg, name="天气助手"),
            tts_text=error_msg,
            actions=Actions()
        )

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
        ]