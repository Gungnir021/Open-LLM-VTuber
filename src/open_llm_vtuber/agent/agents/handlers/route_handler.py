import json
from typing import Optional
from datetime import datetime
from .base_handler import BaseHandler
from ..intent_detectors.route_detector import RouteIntentDetector

class RouteHandler(BaseHandler):
    """
    路线处理器，负责处理路线规划请求
    """
    
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理路线规划请求
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据（路线规划不需要）
            
        Returns:
            处理结果文本
        """
        # 使用路线意图检测器提取参数
        detector = RouteIntentDetector()
        params = detector.extract_params(text)
        
        if not params.get("origin") or not params.get("destination"):
            return "抱歉，我无法确定您的出发地或目的地。请提供完整的路线信息。"
        
        # 记录工具调用信息
        self.tool_caller.increment_call_count()
        self.tool_caller.set_last_call_info(
            tool_name="get_route_traffic",
            tool_args=params,
            call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 调用路线API
        route_result = self.tool_caller.call_tool("get_route_traffic", params)
        
        # 将工具结果添加到记忆中
        self.memory_manager.add_tool_result("get_route_traffic", route_result)
        
        # 使用LLM生成最终回答
        response_text = ""
        async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
            response_text += chunk
        
        return response_text