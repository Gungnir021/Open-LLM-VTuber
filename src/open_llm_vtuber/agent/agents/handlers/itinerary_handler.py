import json
from typing import Optional
from datetime import datetime
from .base_handler import BaseHandler
from ..intent_detectors.itinerary_detector import ItineraryIntentDetector

class ItineraryHandler(BaseHandler):
    """
    行程处理器，负责处理行程规划请求
    """
    
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理行程规划请求
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据（行程规划不需要）
            
        Returns:
            处理结果文本
        """
        # 使用行程意图检测器提取参数
        detector = ItineraryIntentDetector()
        params = detector.extract_params(text)
        
        if not params.get("destination") or not params.get("duration"):
            return "抱歉，我无法确定您想规划的目的地或行程天数。请提供完整的行程信息。"
        
        # 获取用户偏好信息
        user_preferences = self.user_manager.get_user_preferences(self.current_user_id)
        if user_preferences:
            params["preferences"] = user_preferences
        
        # 记录工具调用信息
        self.tool_caller.increment_call_count()
        self.tool_caller.set_last_call_info(
            tool_name="generate_travel_itinerary",
            tool_args=params,
            call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 调用行程规划API
        itinerary_result = self.tool_caller.call_tool("generate_travel_itinerary", params)
        
        # 将工具结果添加到记忆中
        self.memory_manager.add_tool_result("generate_travel_itinerary", itinerary_result)
        
        # 使用LLM生成最终回答
        response_text = ""
        async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
            response_text += chunk
        
        return response_text