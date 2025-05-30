import json
from typing import Optional, Dict, Any
from datetime import datetime
from .base_handler import BaseHandler
from ..intent_detectors.user_info_detector import UserInfoIntentDetector

class UserInfoHandler(BaseHandler):
    """
    用户信息处理器，负责处理用户信息收集和查询请求
    """
    
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理用户信息收集和查询请求
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据（用户信息处理不需要）
            
        Returns:
            处理结果文本
        """
        # 使用用户信息意图检测器提取参数
        detector = UserInfoIntentDetector()
        params = detector.extract_params(text)
        
        # 判断是查询还是更新用户信息
        if params.get("action") == "query":
            # 查询用户信息
            user_info = self.user_manager.get_user_info(self.current_user_id)
            if not user_info:
                return "您还没有设置个人信息。您可以告诉我您的旅行偏好、兴趣爱好等信息，以便我为您提供更个性化的服务。"
            
            # 将用户信息添加到记忆中
            self.memory_manager.add_tool_result("get_user_info", user_info)
            
            # 使用LLM生成最终回答
            response_text = ""
            async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
                response_text += chunk
            
            return response_text
        else:
            # 更新用户信息
            if not params.get("info"):
                return "抱歉，我无法确定您想要更新的信息内容。请提供更详细的个人信息。"
            
            # 记录工具调用信息
            self.tool_caller.increment_call_count()
            self.tool_caller.set_last_call_info(
                tool_name="collect_user_info",
                tool_args={"user_id": self.current_user_id, "info": params["info"]},
                call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            # 调用用户信息收集API
            user_info_result = self.tool_caller.call_tool(
                "collect_user_info", 
                {"user_id": self.current_user_id, "info": params["info"]}
            )
            
            # 将工具结果添加到记忆中
            self.memory_manager.add_tool_result("collect_user_info", user_info_result)
            
            # 使用LLM生成最终回答
            response_text = ""
            async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
                response_text += chunk
            
            return response_text