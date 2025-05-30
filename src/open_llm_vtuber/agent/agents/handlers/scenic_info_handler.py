import json
from typing import Optional
from datetime import datetime
from .base_handler import BaseHandler
from ..intent_detectors.scenic_info_detector import ScenicInfoIntentDetector

class ScenicInfoHandler(BaseHandler):
    """
    景点信息处理器，负责处理景点信息查询请求
    """
    
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理景点信息查询请求
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据（景点信息查询不需要）
            
        Returns:
            处理结果文本
        """
        # 使用景点信息意图检测器提取参数
        detector = ScenicInfoIntentDetector()
        params = detector.extract_params(text)
        
        if not params.get("spot_name"):
            return "抱歉，我无法确定您想查询哪个景点的信息。请提供具体的景点名称。"
        
        # 记录工具调用信息
        self.tool_caller.increment_call_count()
        self.tool_caller.set_last_call_info(
            tool_name="get_scenic_spot_info",
            tool_args=params,
            call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 调用景点信息API
        scenic_result = self.tool_caller.call_tool("get_scenic_spot_info", params)
        
        # 将工具结果添加到记忆中
        self.memory_manager.add_tool_result("get_scenic_spot_info", scenic_result)
        
        # 使用LLM生成最终回答
        response_text = ""
        async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
            response_text += chunk
        
        return response_text