import json
from typing import Optional
from datetime import datetime
from .base_handler import BaseHandler
from ..intent_detectors.weather_detector import WeatherIntentDetector

class WeatherHandler(BaseHandler):
    """
    天气处理器，负责处理天气查询请求
    """
    
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理天气查询请求
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据（天气查询不需要）
            
        Returns:
            处理结果文本
        """
        # 使用天气意图检测器提取参数
        detector = WeatherIntentDetector()
        params = detector.extract_params(text)
        
        if not params.get("location"):
            return "抱歉，我无法确定您想查询哪个地点的天气。请提供具体的地点名称。"
        
        # 记录工具调用信息
        self.tool_caller.increment_call_count()
        self.tool_caller.set_last_call_info(
            tool_name="get_current_temperature",
            tool_args=params,
            call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 调用天气API
        weather_result = self.tool_caller.call_tool("get_current_temperature", params)
        
        # 将工具结果添加到记忆中
        self.memory_manager.add_tool_result("get_current_temperature", weather_result)
        
        # 使用LLM生成最终回答
        response_text = ""
        async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
            response_text += chunk
        
        return response_text