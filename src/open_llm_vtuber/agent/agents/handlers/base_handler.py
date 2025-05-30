from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from ..utils.memory_manager import MemoryManager
from ..utils.tool_caller import ToolCaller
from ...stateless_llm.stateless_llm_interface import StatelessLLMInterface
from ..tools.user_profile import UserProfileManager

class BaseHandler(ABC):
    """
    处理器基类，负责处理特定类型的用户意图
    """
    
    def __init__(self, llm: StatelessLLMInterface, memory_manager: MemoryManager, 
                 tool_caller: ToolCaller, user_manager: UserProfileManager, current_user_id: str):
        """
        初始化处理器
        
        Args:
            llm: 无状态LLM接口实例
            memory_manager: 内存管理器
            tool_caller: 工具调用器
            user_manager: 用户管理器
            current_user_id: 当前用户ID
        """
        self.llm = llm
        self.memory_manager = memory_manager
        self.tool_caller = tool_caller
        self.user_manager = user_manager
        self.current_user_id = current_user_id
    
    @abstractmethod
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理用户请求
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据
            
        Returns:
            处理结果文本
        """
        pass

class WeatherHandler(BaseHandler):
    """天气查询处理器"""
    
    def __init__(self, llm, memory_manager, tool_caller, user_manager, location: str):
        super().__init__(llm, memory_manager, tool_caller, user_manager)
        self.location = location
    
    async def process(self) -> str:
        # 调用天气API
        weather_result = self.tool_caller.call_tool(
            "get_current_temperature", 
            {"location": self.location}
        )
        
        # 将工具结果添加到记忆中
        self.memory_manager.add_tool_result(
            "get_current_temperature", 
            weather_result
        )
        
        # 使用LLM生成最终回答
        response_text = ""
        async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
            response_text += chunk
            
        return response_text

# 其他处理器类似实现...

class HandlerFactory:
    """处理器工厂"""
    
    def __init__(self, llm, memory_manager, tool_caller, user_manager):
        self.llm = llm
        self.memory_manager = memory_manager
        self.tool_caller = tool_caller
        self.user_manager = user_manager
    
    def get_handler(self, intents: Dict[str, Any], image_data: Optional[str] = None) -> BaseHandler:
        """根据意图获取合适的处理器"""
        # 优先处理图片分析
        if image_data and ("分析" in intents.get("text", "") or "识别" in intents.get("text", "")):
            return ImageAnalysisHandler(
                self.llm, self.memory_manager, self.tool_caller, 
                self.user_manager, image_data, intents.get("social_media", False)
            )
        
        # 处理天气查询
        if "weather" in intents and intents["weather"].get("location"):
            return WeatherHandler(
                self.llm, self.memory_manager, self.tool_caller, 
                self.user_manager, intents["weather"]["location"]
            )
            
        # 其他处理器的选择逻辑...
        
        # 默认使用通用处理器
        return DefaultHandler(self.llm, self.memory_manager, self.tool_caller, self.user_manager)