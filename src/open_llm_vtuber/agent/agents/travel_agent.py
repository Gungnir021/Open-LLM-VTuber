import os
import re
import json
import requests
import asyncio
import concurrent.futures
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
from .tools.tool_base import ToolManager
from .tools.weather_tool import WeatherTool
from .tools.infrastructure_tool import InfrastructureTool
from .tools.traffic_tool import TrafficTool
from .tools.ip_location_tool import IPLocationTool
from ..stateless_llm.stateless_llm_interface import StatelessLLMInterface

# ──────────────────── 1. 读取环境变量 ──────────────────── 
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
AMAP_API_KEY = os.getenv("AMAP_API_KEY")

if not DEEPSEEK_API_KEY:
    logger.warning("❌ 未检测到 DEEPSEEK_API_KEY，请在 .env 文件中配置。")
if not AMAP_API_KEY:
    logger.warning("❌ 未检测到 AMAP_API_KEY，请在 .env 文件中配置。")


class TravelAgent(AgentInterface):
    """
    旅行助手 Agent，支持 DeepSeek Function Calling
    """

    _system: str = """
    你是一个专业的旅行助手，可以帮助用户提供旅行建议。
    请用友好、专业的语气回复用户。
    禁止输出 markdown 格式的内容。

    你拥有以下工具能力：
    - get_ip_location: 获取用户当前位置信息
    - get_weather: 查询指定地点的天气情况
    - get_traffic_info: 查询交通状况信息
    - get_infrastructure_info: 查询基础设施信息

    请根据用户的具体需求，智能判断需要调用哪些工具：
    - 如果用户询问涉及位置的问题，考虑是否需要获取当前位置
    - 如果用户询问涉及天气的问题，考虑是否需要查询天气
    - 如果用户询问涉及出行、路线的问题，考虑是否需要查询交通信息
    - 如果用户询问涉及设施、服务的问题，考虑是否需要查询基础设施

    你可以同时调用多个工具来获取完整信息，然后基于所有信息给出综合建议。
    请根据用户问题的复杂程度和信息需求，自主决定调用工具的数量和类型。
    """

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
        
        # 初始化工具管理器
        self._tool_manager = ToolManager()
        self._register_tools()
        
        # 设置聊天功能
        self.chat = self._chat_function_factory(llm.chat_completion)
        logger.info("TravelAgent initialized.")
    
    def _register_tools(self):
        """注册所有工具"""
        print("🔧 [DEBUG] 开始注册工具...")
        
        # 注册天气工具
        self._tool_manager.register_tool(WeatherTool())

        # 注册基础设施查询工具
        self._tool_manager.register_tool(InfrastructureTool())

        # 注册交通态势查询工具
        self._tool_manager.register_tool(TrafficTool())

        # 注册 ip 定位查询工具
        self._tool_manager.register_tool(IPLocationTool())
        
        print(f"🔧 [DEBUG] 工具注册完成，共注册 {len(self._tool_manager.get_all_tools())} 个工具")
    
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
        """使用 DeepSeek API 进行函数调用，支持多个 tool 并发调用"""
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
        
        # 获取所有工具的函数定义
        tools = self._tool_manager.get_function_definitions()
        print(f"🔧 [DEBUG] 可用工具数量: {len(tools)}")
        
        # 优化API参数以提升AI的工具调用能力
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",  # 让AI自主决定是否调用工具
            "parallel_tool_calls": True,  # 启用并行工具调用
            "temperature": 0.3,  # 降低温度提高一致性
            "max_tokens": 2000
        }
        
        try:
            print("🔧 [DEBUG] 正在调用 DeepSeek API...")
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"❌ [DEBUG] API 调用失败: {response.status_code} - {response.text}")
                return f"❌ API 调用失败: {response.status_code}"
            
            response_json = response.json()
            print("🔧 [DEBUG] DeepSeek API 响应状态: 成功")
            
            # 检查是否要求调用函数
            tool_calls = response_json["choices"][0]["message"].get("tool_calls")
            if not tool_calls:
                # AI 判断不需要调用工具，返回普通回复
                print("🔧 [DEBUG] AI 自主判断不需要调用工具，返回普通回复")
                return response_json["choices"][0]["message"]["content"]
            
            print(f"🔧 [DEBUG] AI 自主决定调用工具，工具数量: {len(tool_calls)}")
            
            # 记录AI的工具选择决策
            for i, tool_call in enumerate(tool_calls):
                function_name = tool_call["function"]["name"]
                function_args = tool_call["function"]["arguments"]
                print(f"🔧 [DEBUG] 工具 {i+1}: {function_name} - 参数: {function_args}")
            
            # 步骤2: 并发执行多个函数调用
            assistant_message = response_json["choices"][0]["message"]
            
            # 添加助手的消息（包含工具调用请求）
            messages.append(assistant_message)
            
            # 并发执行所有工具调用
            tool_results = self._execute_tools_concurrently(tool_calls)
            
            # 将所有工具结果添加到消息列表
            for tool_call, result in zip(tool_calls, tool_results):
                messages.append({
                    "role": "tool",
                    "content": result["content"],
                    "tool_call_id": tool_call["id"]
                })
            
            print(f"🔧 [DEBUG] 所有函数调用完成，共执行 {len(tool_calls)} 个函数")
            
            # 步骤3: 将所有函数结果返回给模型，获取最终回复
            print("🔧 [DEBUG] 将所有函数结果返回给 DeepSeek 模型...")
            print(f"🔧 [DEBUG] 发送的消息数量: {len(messages)}")
            
            # 构建最终请求，不包含 tools 参数
            final_payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            # 重试机制
            max_retries = 2
            final_content = None
            
            for retry in range(max_retries):
                try:
                    final_response = requests.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers=headers,
                        json=final_payload,
                        timeout=60
                    )
                    
                    print(f"🔧 [DEBUG] 最终响应状态码: {final_response.status_code}")
                    
                    if final_response.status_code != 200:
                        print(f"❌ [DEBUG] 最终API调用失败: {final_response.text}")
                        if retry < max_retries - 1:
                            print(f"⚠️ [DEBUG] 第 {retry + 1} 次尝试失败，重试中...")
                            continue
                        return "❌ 获取最终回复时出现错误"
                    
                    final_response_json = final_response.json()
                    
                    final_content = final_response_json["choices"][0]["message"]["content"]
                    print(f"🔧 [DEBUG] Function Calling 完成，最终回复长度: {len(final_content)}")
                    
                    # 响应格式验证和清理
                    if final_content and self._validate_and_clean_response(final_content):
                        final_content = self._validate_and_clean_response(final_content)
                        break
                    elif retry < max_retries - 1:
                        print(f"⚠️ [DEBUG] 第 {retry + 1} 次尝试响应异常，重试中...")
                        continue
                        
                except Exception as e:
                    print(f"❌ [DEBUG] 第 {retry + 1} 次最终调用异常: {str(e)}")
                    if retry < max_retries - 1:
                        continue
                    else:
                        raise e
            
            if not final_content:
                print("⚠️ [DEBUG] 最终回复为空，返回默认消息")
                return "抱歉，我已经获取了相关信息，但生成回复时出现了问题。请稍后重试。"
            
            print("✅ [DEBUG] DeepSeek 多函数调用执行成功！")
            return final_content
            
        except Exception as e:
            print(f"❌ [DEBUG] DeepSeek API 调用失败: {str(e)}")
            logger.error(f"DeepSeek API 调用失败: {str(e)}")
            return f"❌ 抱歉，智能功能暂时不可用: {str(e)}"
    
    def _execute_tools_concurrently(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """并发执行多个工具调用"""
        print(f"🔧 [DEBUG] 开始并发执行 {len(tool_calls)} 个工具")
        
        def execute_single_tool(tool_call):
            """执行单个工具的包装函数"""
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"])
            tool_call_id = tool_call["id"]
            
            print(f"🔧 [DEBUG] 开始执行工具: {function_name}")
            print(f"🔧 [DEBUG] 工具参数: {function_args}")
            
            try:
                # 使用工具管理器执行工具
                tool_result = self._tool_manager.execute_tool(function_name, function_args)
                print(f"✅ [DEBUG] 工具 {function_name} 执行成功")
                print(f"🔧 [DEBUG] 工具执行结果: {tool_result[:200]}...")
                
                return {
                    "success": True,
                    "content": tool_result,
                    "tool_name": function_name
                }
                
            except Exception as tool_error:
                print(f"❌ [DEBUG] 工具 {function_name} 执行失败: {str(tool_error)}")
                error_message = f"工具 {function_name} 执行失败: {str(tool_error)}"
                
                return {
                    "success": False,
                    "content": error_message,
                    "tool_name": function_name
                }
        
        # 使用线程池并发执行工具
        results = []
        max_workers = min(len(tool_calls), 3)  # 限制并发数量
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_tool = {executor.submit(execute_single_tool, tool_call): tool_call 
                             for tool_call in tool_calls}
            
            # 收集结果（保持原始顺序）
            for tool_call in tool_calls:
                for future, original_tool_call in future_to_tool.items():
                    if original_tool_call == tool_call:
                        try:
                            result = future.result(timeout=30)  # 30秒超时
                            results.append(result)
                            print(f"✅ [DEBUG] 工具 {result['tool_name']} 并发执行完成")
                        except concurrent.futures.TimeoutError:
                            print(f"⏰ [DEBUG] 工具 {tool_call['function']['name']} 执行超时")
                            results.append({
                                "success": False,
                                "content": f"工具 {tool_call['function']['name']} 执行超时",
                                "tool_name": tool_call['function']['name']
                            })
                        except Exception as e:
                            print(f"❌ [DEBUG] 工具 {tool_call['function']['name']} 并发执行异常: {str(e)}")
                            results.append({
                                "success": False,
                                "content": f"工具 {tool_call['function']['name']} 执行异常: {str(e)}",
                                "tool_name": tool_call['function']['name']
                            })
                        break
        
        print(f"🔧 [DEBUG] 并发执行完成，成功: {sum(1 for r in results if r['success'])}/{len(results)}")
        return results

    def _validate_and_clean_response(self, content: str) -> str:
        """验证和清理响应内容，移除异常的工具调用标记和markdown格式"""
        if not content:
            return content
        
        original_length = len(content)
        cleaned_content = content
        
        # 1. 移除异常的工具调用标记
        tool_patterns = [
            r'function\w+',  # functionget_weather 等
            r'tool_call\w+',  # tool_call 相关
            r'\{"tool_calls"',  # JSON 工具调用残留
        ]
        
        for pattern in tool_patterns:
            matches = re.findall(pattern, cleaned_content, re.IGNORECASE)
            if matches:
                print(f"🔧 [DEBUG] 检测到异常工具调用标记: {matches}")
                cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE)
        
        # 2. 清理 markdown 格式
        markdown_patterns = [
            # 标题格式 (# ## ### 等)
            (r'^#{1,6}\s+(.+)$', r'\1'),
            # 粗体格式 (**text** 或 __text__)
            (r'\*\*(.+?)\*\*', r'\1'),
            (r'__(.+?)__', r'\1'),
            # 斜体格式 (*text* 或 _text_)
            (r'(?<!\*)\*([^*]+?)\*(?!\*)', r'\1'),
            (r'(?<!_)_([^_]+?)_(?!_)', r'\1'),
            # 代码块格式 (```code``` 或 `code`)
            (r'```[\s\S]*?```', ''),
            (r'`([^`]+?)`', r'\1'),
            # 链接格式 [text](url)
            (r'\[([^\]]+?)\]\([^\)]+?\)', r'\1'),
            # 图片格式 ![alt](url)
            (r'!\[[^\]]*?\]\([^\)]+?\)', ''),
            # 列表格式 (- 或 * 或 数字.)
            (r'^\s*[-*+]\s+', ''),
            (r'^\s*\d+\.\s+', ''),
            # 引用格式 (> text)
            (r'^\s*>\s+(.+)$', r'\1'),
            # 水平分割线
            (r'^\s*[-*_]{3,}\s*$', ''),
            # 表格分隔符
            (r'\|', ' '),
            # HTML标签
            (r'<[^>]+>', ''),
        ]
        
        print(f"🔧 [DEBUG] 开始清理markdown格式...")
        
        # 按行处理，保持换行结构
        lines = cleaned_content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            cleaned_line = line
            
            # 应用所有markdown清理规则
            for pattern, replacement in markdown_patterns:
                if pattern.startswith('^') and pattern.endswith('$'):
                    # 整行匹配的模式
                    cleaned_line = re.sub(pattern, replacement, cleaned_line, flags=re.MULTILINE)
                else:
                    # 行内匹配的模式
                    cleaned_line = re.sub(pattern, replacement, cleaned_line)
            
            # 清理多余空格但保留基本格式
            cleaned_line = re.sub(r'\s+', ' ', cleaned_line).strip()
            
            # 保留非空行
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
        
        # 重新组合内容
        cleaned_content = '\n'.join(cleaned_lines)
        
        # 3. 最终清理
        # 移除多余的换行符
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        # 清理首尾空白
        cleaned_content = cleaned_content.strip()
        
        # 4. 避免过度清理检查
        if len(cleaned_content) < original_length * 0.2:  # 如果清理后内容少于原内容的20%
            print(f"⚠️ [DEBUG] 清理后内容过短({len(cleaned_content)}/{original_length})，保留原内容")
            return content
        
        if cleaned_content != content:
            print(f"🔧 [DEBUG] 内容已清理，长度: {original_length} -> {len(cleaned_content)}")
            print(f"🔧 [DEBUG] 清理后预览: {cleaned_content[:100]}...")
        
        return cleaned_content if cleaned_content else content

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