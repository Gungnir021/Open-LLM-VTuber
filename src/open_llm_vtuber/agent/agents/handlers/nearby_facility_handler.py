import json
from typing import Optional
from datetime import datetime
from .base_handler import BaseHandler
from ..intent_detectors.nearby_facility_detector import NearbyFacilityIntentDetector

class NearbyFacilityHandler(BaseHandler):
    """
    周边设施处理器，负责处理周边设施查询请求
    """
    
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理周边设施查询请求
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据（周边设施查询不需要）
            
        Returns:
            处理结果文本
        """
        # 使用周边设施意图检测器提取参数
        detector = NearbyFacilityIntentDetector()
        params = detector.extract_params(text)
        
        if not params.get("location") or not params.get("facility_type"):
            return "抱歉，我无法确定您想查询哪个地点的什么类型的设施。请提供完整的查询信息。"
        
        # 记录工具调用信息
        self.tool_caller.increment_call_count()
        self.tool_caller.set_last_call_info(
            tool_name="find_nearby_facilities",
            tool_args=params,
            call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 调用周边设施API
        facility_result = self.tool_caller.call_tool("find_nearby_facilities", params)
        
        # 将工具结果添加到记忆中
        self.memory_manager.add_tool_result("find_nearby_facilities", facility_result)
        
        # 使用LLM生成最终回答
        response_text = ""
        async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
            response_text += chunk
        
        return response_text