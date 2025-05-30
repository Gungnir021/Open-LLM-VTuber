import json
from typing import Optional, Dict, Any
from datetime import datetime
from .base_handler import BaseHandler

class ImageAnalysisHandler(BaseHandler):
    """
    图片分析处理器，负责处理图片分析请求
    """
    
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理图片分析请求
        
        Args:
            text: 用户输入文本
            image_data: 图片数据（Base64编码）
            
        Returns:
            处理结果文本
        """
        if not image_data:
            return "抱歉，我没有收到任何图片。请上传一张图片以便我进行分析。"
        
        # 判断是否需要生成社交媒体内容
        is_social_media = "朋友圈" in text or "微信" in text or "微博" in text or "社交" in text
        
        # 记录工具调用信息
        self.tool_caller.increment_call_count()
        self.tool_caller.set_last_call_info(
            tool_name="analyze_travel_photo",
            tool_args={"image_data": "[图片数据]"}, # 不记录实际图片数据
            call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 调用图片分析API
        photo_result = self.tool_caller.call_tool("analyze_travel_photo", {"image_data": image_data})
        
        # 将工具结果添加到记忆中
        self.memory_manager.add_tool_result("analyze_travel_photo", photo_result)
        
        # 如果需要生成社交媒体内容
        if is_social_media:
            # 获取用户旅行信息
            trip_info = self.user_manager.get_user_trip_info(self.current_user_id) or {}
            
            # 记录工具调用信息
            self.tool_caller.increment_call_count()
            self.tool_caller.set_last_call_info(
                tool_name="generate_social_media_post",
                tool_args={"trip_info": trip_info, "photos_analysis": [photo_result]},
                call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            # 调用社交媒体内容生成API
            social_media_result = self.tool_caller.call_tool(
                "generate_social_media_post", 
                {"trip_info": trip_info, "photos_analysis": [photo_result]}
            )
            
            # 将工具结果添加到记忆中
            self.memory_manager.add_tool_result("generate_social_media_post", social_media_result)
        
        # 使用LLM生成最终回答
        response_text = ""
        async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
            response_text += chunk
        
        return response_text