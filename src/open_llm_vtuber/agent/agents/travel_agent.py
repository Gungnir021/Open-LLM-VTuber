from typing import AsyncIterator, Dict, Any, List, Optional, Union
import json
from loguru import logger
from datetime import datetime

from .agent_interface import AgentInterface
from ..input_types import BatchInput
from ..output_types import SentenceOutput, DisplayText, Actions
from ...utils.sentence_divider import SentenceWithTags
from ...config_manager import TTSPreprocessorConfig
from ..transformers import tts_filter
from ..stateless_llm.stateless_llm_interface import StatelessLLMInterface
from .tools.user_profile import UserProfileManager

# 导入意图检测器工厂
from .intent_detectors import IntentDetectorFactory

# 导入处理器工厂
from .handlers import HandlerFactory

# 导入工具注册表和调用器
from .utils.tool_registry import ToolRegistry
from .utils.tool_caller import ToolCaller
from .utils.memory_manager import MemoryManager

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
        
        # 初始化内存管理器
        self.memory_manager = MemoryManager(system_prompt)
        
        # 初始化用户管理器
        self.user_manager = UserProfileManager()
        self.current_user_id = "default"  # 当前用户ID
        
        # 初始化工具注册表和调用器
        self.tool_registry = ToolRegistry()
        self.tool_caller = ToolCaller(self.tool_registry, api_key)
        
        # 初始化意图检测器工厂和处理器工厂
        self.intent_detector_factory = IntentDetectorFactory()
        self.handler_factory = HandlerFactory(
            llm=self.llm,
            memory_manager=self.memory_manager,
            tool_caller=self.tool_caller,
            user_manager=self.user_manager,
            current_user_id=self.current_user_id
        )
        
        logger.info("TravelAgent初始化完成，系统提示词已设置")

    @tts_filter()
    async def chat(self, input_data: BatchInput) -> AsyncIterator[tuple[SentenceWithTags, DisplayText, Actions]]:
        # 合并所有文本输入
        user_text = "\n".join([t.content for t in input_data.texts])
        self.memory_manager.add_user_message(user_text)
        
        logger.debug(f"发送消息到LLM: {len(self.memory_manager.get_messages())}条消息")
        logger.info(f"当前工具调用次数: {self.tool_caller.get_call_count()}")
        
        # 处理图片输入
        image_data = None
        if input_data.images and len(input_data.images) > 0:
            # 获取第一张图片的数据
            image_data = input_data.images[0].data
            logger.info("检测到图片输入，将进行图片分析")
        
        try:
            response_text = ""
            
            # 检测意图
            detected_intent = self._detect_intent(user_text, image_data)
            
            if detected_intent:
                # 获取对应的处理器
                handler = self.handler_factory.get_handler(detected_intent)
                
                # 处理请求并获取响应
                response_text = await handler.handle(user_text, image_data)
            else:
                # 常规LLM对话
                logger.info("未检测到明确的查询意图，使用常规对话")
                async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
                    response_text += chunk
            
            # 将回答添加到记忆中
            self.memory_manager.add_assistant_message(response_text)
            
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

    def _detect_intent(self, text: str, image_data: Optional[str] = None) -> Optional[str]:
        """
        检测用户意图
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据
            
        Returns:
            检测到的意图类型或None
        """
        # 检查是否有图片分析意图
        if image_data and ("分析" in text or "识别" in text or "照片" in text or "图片" in text):
            return "image_analysis"
        
        # 使用意图检测器工厂检测其他意图
        for intent_type in self.intent_detector_factory.get_available_intents():
            detector = self.intent_detector_factory.get_detector(intent_type)
            if detector.detect(text):
                return intent_type
        
        return None

    def handle_interrupt(self, heard_response: str) -> None:
        """
        处理用户中断
        
        Args:
            heard_response: 用户听到的响应部分
        """
        self.memory_manager.handle_interrupt(heard_response)
        logger.info("用户中断了对话，已更新对话记录")

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        """
        从历史记录中设置记忆
        
        Args:
            conf_uid: 配置ID
            history_uid: 历史记录ID
        """
        logger.info(f"尝试从历史记录加载对话: conf_uid={conf_uid}, history_uid={history_uid}")
        # 可以实现从历史记录加载对话，此处为空实现
        pass

    def tools(self) -> List[Dict[str, Any]]:
        """
        返回可用工具列表
        
        Returns:
            工具定义列表
        """
        return self.tool_registry.get_tools()