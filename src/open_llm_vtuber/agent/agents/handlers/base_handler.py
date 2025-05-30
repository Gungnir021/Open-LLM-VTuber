from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime

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

class DefaultHandler(BaseHandler):
    """
    默认处理器，处理无法识别特定意图的请求
    """
    
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理默认请求
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据
            
        Returns:
            处理结果文本
        """
        # 将用户输入添加到记忆中
        self.memory_manager.add_user_message(text)
        
        # 如果有图片数据，添加图片描述
        if image_data:
            self.memory_manager.add_system_message("用户上传了一张图片，但我无法确定您想让我做什么。请告诉我您需要什么帮助。")
        
        # 使用LLM生成回答
        response_text = ""
        async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
            response_text += chunk
        
        return response_text