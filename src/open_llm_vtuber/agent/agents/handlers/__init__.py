from typing import Dict, Type
from .base_handler import BaseHandler
from .weather_handler import WeatherHandler
from .traffic_handler import TrafficHandler
from .route_handler import RouteHandler
from .nearby_facility_handler import NearbyFacilityHandler
from .itinerary_handler import ItineraryHandler
from .packing_handler import PackingHandler
from .social_media_handler import SocialMediaHandler
from .user_info_handler import UserInfoHandler
from .scenic_info_handler import ScenicInfoHandler
from .image_analysis_handler import ImageAnalysisHandler
from ...stateless_llm.stateless_llm_interface import StatelessLLMInterface
from ..utils.memory_manager import MemoryManager
from ..utils.tool_caller import ToolCaller
from ..tools.user_profile import UserProfileManager

class HandlerFactory:
    """
    处理器工厂，负责创建和管理各种处理器
    """
    
    def __init__(self, llm: StatelessLLMInterface, memory_manager: MemoryManager, 
                 tool_caller: ToolCaller, user_manager: UserProfileManager, current_user_id: str):
        """
        初始化处理器工厂
        
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
        
        # 初始化处理器映射
        self._handlers: Dict[str, BaseHandler] = {
            "weather": WeatherHandler(llm, memory_manager, tool_caller, user_manager, current_user_id),
            "traffic": TrafficHandler(llm, memory_manager, tool_caller, user_manager, current_user_id),
            "route": RouteHandler(llm, memory_manager, tool_caller, user_manager, current_user_id),
            "nearby_facility": NearbyFacilityHandler(llm, memory_manager, tool_caller, user_manager, current_user_id),
            "itinerary": ItineraryHandler(llm, memory_manager, tool_caller, user_manager, current_user_id),
            "packing": PackingHandler(llm, memory_manager, tool_caller, user_manager, current_user_id),
            "social_media": SocialMediaHandler(llm, memory_manager, tool_caller, user_manager, current_user_id),
            "user_info": UserInfoHandler(llm, memory_manager, tool_caller, user_manager, current_user_id),
            "scenic_info": ScenicInfoHandler(llm, memory_manager, tool_caller, user_manager, current_user_id),
            "image_analysis": ImageAnalysisHandler(llm, memory_manager, tool_caller, user_manager, current_user_id)
        }
    
    def get_handler(self, intent_type: str) -> BaseHandler:
        """
        获取指定类型的处理器
        
        Args:
            intent_type: 意图类型
            
        Returns:
            处理器实例
            
        Raises:
            ValueError: 如果意图类型不存在
        """
        if intent_type not in self._handlers:
            raise ValueError(f"未知的意图类型: {intent_type}")
        return self._handlers[intent_type]