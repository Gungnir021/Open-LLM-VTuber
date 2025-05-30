import json
from typing import Optional
from datetime import datetime
from .base_handler import BaseHandler
from ..intent_detectors.packing_detector import PackingIntentDetector

class PackingHandler(BaseHandler):
    """
    行李清单处理器，负责处理行李清单生成请求
    """
    
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理行李清单生成请求
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据（行李清单生成不需要）
            
        Returns:
            处理结果文本
        """
        # 使用行李清单意图检测器提取参数
        detector = PackingIntentDetector()
        params = detector.extract_params(text)
        
        if not params.get("destination") or not params.get("duration"):
            return "抱歉，我无法确定您的目的地或行程天数。请提供完整的行程信息以生成行李清单。"
        
        # 获取用户偏好信息
        user_preferences = self.user_manager.get_user_preferences(self.current_user_id)
        if user_preferences:
            params["preferences"] = user_preferences
        
        # 记录工具调用信息
        self.tool_caller.increment_call_count()
        self.tool_caller.set_last_call_info(
            tool_name="generate_packing_list",
            tool_args=params,
            call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 调用行李清单生成API
        packing_result = self.tool_caller.call_tool("generate_packing_list", params)
        
        # 将工具结果添加到记忆中
        self.memory_manager.add_tool_result("generate_packing_list", packing_result)
        
        # 使用LLM生成最终回答
        response_text = ""
        async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
            response_text += chunk
        
        return response_text