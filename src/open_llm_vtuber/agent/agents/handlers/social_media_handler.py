import json
from typing import Optional, List, Dict
from datetime import datetime
from .base_handler import BaseHandler
from ..intent_detectors.social_media_detector import SocialMediaIntentDetector

class SocialMediaHandler(BaseHandler):
    """
    社交媒体处理器，负责处理社交媒体内容生成请求
    """
    
    async def handle(self, text: str, image_data: Optional[str] = None) -> str:
        """
        处理社交媒体内容生成请求
        
        Args:
            text: 用户输入文本
            image_data: 可选的图片数据（用于分析生成社交媒体内容）
            
        Returns:
            处理结果文本
        """
        # 使用社交媒体意图检测器提取参数
        detector = SocialMediaIntentDetector()
        params = detector.extract_params(text)
        
        # 如果有图片数据，先分析图片
        photos_analysis = []
        if image_data:
            # 记录工具调用信息
            self.tool_caller.increment_call_count()
            self.tool_caller.set_last_call_info(
                tool_name="analyze_travel_photo",
                tool_args={"image_data": "[图片数据]"}, # 不记录实际图片数据
                call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            # 调用图片分析API
            photo_result = self.tool_caller.call_tool("analyze_travel_photo", {"image_data": image_data})
            photos_analysis.append(photo_result)
            
            # 将工具结果添加到记忆中
            self.memory_manager.add_tool_result("analyze_travel_photo", photo_result)
        
        # 获取用户旅行信息
        trip_info = self.user_manager.get_user_trip_info(self.current_user_id)
        if not trip_info and not params.get("destination"):
            return "抱歉，我无法确定您的旅行目的地。请提供更多旅行信息以生成社交媒体内容。"
        
        # 合并用户旅行信息和参数
        if trip_info:
            for key, value in trip_info.items():
                if key not in params or not params[key]:
                    params[key] = value
        
        # 记录工具调用信息
        self.tool_caller.increment_call_count()
        self.tool_caller.set_last_call_info(
            tool_name="generate_social_media_post",
            tool_args={"trip_info": params, "photos_analysis": photos_analysis},
            call_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 调用社交媒体内容生成API
        social_media_result = self.tool_caller.call_tool(
            "generate_social_media_post", 
            {"trip_info": params, "photos_analysis": photos_analysis}
        )
        
        # 将工具结果添加到记忆中
        self.memory_manager.add_tool_result("generate_social_media_post", social_media_result)
        
        # 使用LLM生成最终回答
        response_text = ""
        async for chunk in self.llm.chat_completion(messages=self.memory_manager.get_messages()):
            response_text += chunk
        
        return response_text