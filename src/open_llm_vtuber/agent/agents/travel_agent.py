import os
import sys
import json
import requests
from typing import AsyncIterator, List, Dict, Any, Callable, Literal
from loguru import logger
from dotenv import load_dotenv

from .agent_interface import AgentInterface
from ..output_types import SentenceOutput, DisplayText
from ..input_types import BatchInput, TextSource, ImageSource
from ...chat_history_manager import get_history
from ..transformers import (
    sentence_divider,
    actions_extractor,
    tts_filter,
    display_processor,
)
from ...config_manager import TTSPreprocessorConfig
from .tools.get_weather import get_weather

# ──────────────────── 1. 读取环境变量 ──────────────────── 
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
AMAP_API_KEY = os.getenv("AMAP_API_KEY")

if not DEEPSEEK_API_KEY:
    logger.warning("❌ 未检测到 DEEPSEEK_API_KEY，请在 .env 文件中配置。")
if not AMAP_API_KEY:
    logger.warning("❌ 未检测到 AMAP_API_KEY，请在 .env 文件中配置。")

from ..stateless_llm.stateless_llm_interface import StatelessLLMInterface

class TravelAgent(AgentInterface):
    """
    旅行助手 Agent，支持 DeepSeek Function Calling
    实现天气查询、旅行建议等功能
    """

    _system: str = """你是一个专业的旅行助手，可以帮助用户查询天气、提供旅行建议。
当用户询问天气时，请使用 get_weather 函数获取准确的天气信息。
请用友好、专业的语气回复用户。"""

    def __init__(
        self,
        llm: StatelessLLMInterface,
        system_prompt: str = None,
        live2d_model=None,
        tts_preprocessor_config: TTSPreprocessorConfig = None,
        faster_first_response: bool = True,
        segment_method: str = "pysbd",
        interrupt_method: Literal["system", "user"] = "user",
    ):
        """
        初始化旅行助手
        
        Args:
            llm: StatelessLLMInterface - LLM 实例
            system_prompt: 系统提示词
            live2d_model: Live2D 模型
            tts_preprocessor_config: TTS 预处理配置
            faster_first_response: 是否启用快速首次响应
            segment_method: 句子分割方法
            interrupt_method: 中断处理方法
        """
        super().__init__()
        self._memory = []
        self._llm = llm
        self._live2d_model = live2d_model
        self._tts_preprocessor_config = tts_preprocessor_config
        self._faster_first_response = faster_first_response
        self._segment_method = segment_method
        self.interrupt_method = interrupt_method
        self._interrupt_handled = False
        
        if system_prompt:
            self._system = system_prompt
        
        # 设置聊天功能
        self.chat = self._chat_function_factory(llm.chat_completion)
        logger.info("TravelAgent initialized.")

    def _set_llm(self, llm: StatelessLLMInterface):
        """
        设置要使用的 LLM
        
        Args:
            llm: StatelessLLMInterface - LLM 实例
        """
        self._llm = llm
        self.chat = self._chat_function_factory(llm.chat_completion)

    def _add_message(
        self,
        message: str | List[Dict[str, Any]],
        role: str,
        display_text: DisplayText | None = None,
    ):
        """添加消息到记忆中"""
        if isinstance(message, list):
            text_content = ""
            for item in message:
                if item.get("type") == "text":
                    text_content += item["text"]
        else:
            text_content = message

        message_data = {
            "role": role,
            "content": text_content,
        }

        if display_text:
            if display_text.name:
                message_data["name"] = display_text.name
            if display_text.avatar:
                message_data["avatar"] = display_text.avatar

        self._memory.append(message_data)

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        """从聊天历史加载记忆"""
        messages = get_history(conf_uid, history_uid)

        self._memory = []
        self._memory.append({
            "role": "system",
            "content": self._system,
        })

        for msg in messages:
            self._memory.append({
                "role": "user" if msg["role"] == "human" else "assistant",
                "content": msg["content"],
            })

    def handle_interrupt(self, heard_response: str) -> None:
        """处理用户中断"""
        if self._interrupt_handled:
            return

        self._interrupt_handled = True

        if self._memory and self._memory[-1]["role"] == "assistant":
            self._memory[-1]["content"] = heard_response + "..."
        else:
            if heard_response:
                self._memory.append({
                    "role": "assistant",
                    "content": heard_response + "...",
                })
            self._memory.append({
                "role": "system" if self.interrupt_method == "system" else "user",
                "content": "[Interrupted by user]",
            })

    def reset_interrupt(self) -> None:
        """重置中断标志"""
        self._interrupt_handled = False

    def _to_text_prompt(self, input_data: BatchInput) -> str:
        """将 BatchInput 格式化为提示字符串"""
        message_parts = []

        for text_data in input_data.texts:
            if text_data.source == TextSource.INPUT:
                message_parts.append(text_data.content)
            elif text_data.source == TextSource.CLIPBOARD:
                message_parts.append(f"[Clipboard content: {text_data.content}]")

        if input_data.images:
            message_parts.append("\nImages in this message:")
            for i, img_data in enumerate(input_data.images, 1):
                source_desc = {
                    ImageSource.CAMERA: "captured from camera",
                    ImageSource.SCREEN: "screenshot",
                    ImageSource.CLIPBOARD: "from clipboard",
                    ImageSource.UPLOAD: "uploaded",
                }[img_data.source]
                message_parts.append(f"- Image {i} ({source_desc})")

        return "\n".join(message_parts)

    def _deepseek_function_call(self, query: str) -> str:
        """使用 DeepSeek API 进行函数调用"""
        print("\n🔧 [DEBUG] 开始尝试 DeepSeek Function Calling...")
        print(f"🔧 [DEBUG] 用户输入: {query}")
        
        if not DEEPSEEK_API_KEY:
            print("❌ [DEBUG] DeepSeek API Key 未配置")
            return "❌ DeepSeek API Key 未配置，无法使用智能功能。"
            
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 构建包含记忆的消息列表
        messages = self._memory.copy() if self._memory else []
        
        # 如果没有系统消息，添加系统提示
        if not messages or messages[0]["role"] != "system":
            messages.insert(0, {
                "role": "system",
                "content": self._system
            })
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": query})
        
        print(f"🔧 [DEBUG] 构建的消息数量: {len(messages)}")
        
        # 步骤1: 首次调用获取函数调用请求
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "tools": [{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "获取指定城市的当前天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "城市名称，如：北京、上海、广州等"
                            }
                        },
                        "required": ["location"]
                    }
                }
            }],
            "tool_choice": "auto"  # 让 AI 自动决定是否调用工具
        }
        
        try:
            print("🔧 [DEBUG] 正在调用 DeepSeek API...")
            response = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            ).json()
            
            print(f"🔧 [DEBUG] DeepSeek API 响应状态: 成功")
            
            # 检查是否要求调用函数
            tool_calls = response["choices"][0]["message"].get("tool_calls")
            if not tool_calls:
                # AI 判断不需要调用工具，返回普通回复
                print("🔧 [DEBUG] AI 判断不需要调用工具，返回普通回复")
                return response["choices"][0]["message"]["content"]
            
            print(f"🔧 [DEBUG] AI 决定调用工具，工具数量: {len(tool_calls)}")
            
            # 步骤2: 执行函数调用
            function_name = tool_calls[0]["function"]["name"]
            function_args = json.loads(tool_calls[0]["function"]["arguments"])
            
            print(f"🔧 [DEBUG] 调用函数: {function_name}")
            print(f"🔧 [DEBUG] 函数参数: {function_args}")
            
            if function_name == "get_weather":
                print("🌤️ [DEBUG] 正在执行天气查询...")
                weather_result = get_weather(function_args["location"])
                print(f"🌤️ [DEBUG] 天气查询结果: {weather_result[:100]}...")
            else:
                print(f"❌ [DEBUG] 未知函数调用: {function_name}")
                weather_result = json.dumps({"error": "未知函数调用"}, ensure_ascii=False)
            
            # 步骤3: 将函数结果返回给模型
            print("🔧 [DEBUG] 将函数结果返回给 DeepSeek 模型...")
            payload["messages"].append(response["choices"][0]["message"])
            payload["messages"].append({
                "role": "tool",
                "content": weather_result,
                "tool_call_id": tool_calls[0]["id"]
            })
            
            final_response = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            ).json()
            
            final_content = final_response["choices"][0]["message"]["content"]
            print(f"🔧 [DEBUG] Function Calling 完成，最终回复长度: {len(final_content)}")
            print("✅ [DEBUG] DeepSeek Function Calling 执行成功！")
            
            return final_content
            
        except Exception as e:
            print(f"❌ [DEBUG] DeepSeek API 调用失败: {str(e)}")
            logger.error(f"DeepSeek API 调用失败: {str(e)}")
            return f"❌ 抱歉，智能功能暂时不可用: {str(e)}"

    def _chat_function_factory(
        self, chat_func: Callable[[List[Dict[str, Any]], str], AsyncIterator[str]]
    ) -> Callable[..., AsyncIterator[SentenceOutput]]:
        """
        创建聊天管道，优先使用 DeepSeek Function Calling
        
        管道流程:
        DeepSeek Function Calling -> sentence_divider -> actions_extractor -> display_processor -> tts_filter
        """
        
        @tts_filter(self._tts_preprocessor_config)
        @display_processor()
        @actions_extractor(self._live2d_model)
        @sentence_divider(
            faster_first_response=self._faster_first_response,
            segment_method=self._segment_method,
            valid_tags=["think"],
        )
        async def chat_with_memory(input_data: BatchInput) -> AsyncIterator[str]:
            """
            使用记忆和处理管道的聊天实现，优先使用 Function Calling
            
            Args:
                input_data: BatchInput
            
            Returns:
                AsyncIterator[str] - 来自 LLM 的 token 流
            """
            
            user_input = self._to_text_prompt(input_data)
            print(f"\n💬 [DEBUG] 收到用户输入: {user_input}")
            
            # 优先尝试 DeepSeek Function Calling
            # 让 AI 自动判断是否需要调用工具
            print("🚀 [DEBUG] 开始处理用户请求...")
            try:
                print("🔧 [DEBUG] 尝试使用 DeepSeek Function Calling...")
                response = self._deepseek_function_call(user_input)
                
                # 检查是否成功调用了函数（通过响应内容判断）
                if not response.startswith("❌"):
                    # 成功使用 Function Calling，流式输出响应
                    print("✅ [DEBUG] Function Calling 成功，开始流式输出...")
                    for char in response:
                        yield char
                    
                    # 存储到记忆
                    self._add_message(user_input, "user")
                    self._add_message(response, "assistant")
                    print("✅ [DEBUG] 响应已存储到记忆中")
                    return
                else:
                    # Function Calling 失败，记录日志但继续使用普通聊天
                    print(f"⚠️ [DEBUG] Function calling 不可用: {response}")
                    logger.info(f"Function calling 不可用，使用普通聊天模式: {response}")
                    
            except Exception as e:
                print(f"❌ [DEBUG] Function calling 出错: {str(e)}")
                logger.error(f"Function calling 出错，回退到普通聊天: {str(e)}")
            
            # 回退到普通聊天流程
            print("🔄 [DEBUG] 回退到普通聊天流程...")
            messages = self._to_messages(input_data)
            
            # 从 LLM 获取 token 流
            print("🤖 [DEBUG] 调用普通 LLM 聊天接口...")
            token_stream = chat_func(messages, self._system)
            complete_response = ""
            
            async for token in token_stream:
                yield token
                complete_response += token
            
            # 存储完整响应
            print(f"✅ [DEBUG] 普通聊天完成，响应长度: {len(complete_response)}")
            self._add_message(complete_response, "assistant")
        
        return chat_with_memory

    def _to_messages(self, input_data: BatchInput) -> List[Dict[str, Any]]:
        """
        准备支持图像的消息列表
        """
        messages = self._memory.copy()
        
        if input_data.images:
            content = []
            text_content = self._to_text_prompt(input_data)
            content.append({"type": "text", "text": text_content})
            
            for img_data in input_data.images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": img_data.data, "detail": "auto"},
                })
            
            user_message = {"role": "user", "content": content}
        else:
            user_message = {"role": "user", "content": self._to_text_prompt(input_data)}
        
        messages.append(user_message)
        self._add_message(user_message["content"], "user")
        return messages

    async def chat(self, input_data: BatchInput) -> AsyncIterator[SentenceOutput]:
        """聊天方法"""
        chat_func = self._create_chat_function()
        async for output in chat_func(input_data):
            yield output