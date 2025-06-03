import json
import asyncio
from typing import Optional, Dict, Any
from loguru import logger
from ..conversations.conversation_handler import handle_conversation_trigger
from ..agent.input_types import BatchInput, TextData, ImageData, TextSource, ImageSource
from .image_service import ImageService
from .baidu_service import BaiduLandmarkService

class TravelAgentService:
    """旅游助手服务 - 整合图片识别和AI讲解"""
    
    def __init__(self, websocket_handler=None):
        self.image_service = ImageService()
        self.baidu_service = BaiduLandmarkService()
        self.websocket_handler = websocket_handler
    
    async def process_landmark_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        处理地标图片：识别 + 通过对话系统流式输出讲解
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            包含识别结果的字典
        """
        try:
            # 1. 处理图片
            logger.info("开始处理图片")
            processed_image = await self.image_service.process_image_for_api(image_data)
            
            # 2. 调用百度识图API
            logger.info("调用百度地标识别API")
            landmark_result = await self.baidu_service.recognize_landmark(processed_image)
            
            # 3. 提取地标名称
            landmark_name = self._extract_landmark_name(landmark_result)
            
            # 4. 通过对话系统处理，实现流式输出
            await self._trigger_landmark_conversation(landmark_name, landmark_result)
            
            return {
                "success": True,
                "landmark_name": landmark_name,
                "landmark_info": landmark_result,
                "message": "地标识别成功，正在通过AI助手进行讲解"
            }
            
        except Exception as e:
            logger.error(f"处理地标图片失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "地标识别失败"
            }
    
    def _extract_landmark_name(self, landmark_result: Dict) -> str:
        """
        从识别结果中提取地标名称
        """
        try:
            if 'result' in landmark_result:
                result = landmark_result['result']
                if isinstance(result, dict) and 'landmark' in result:
                    return result['landmark']
                elif isinstance(result, list) and result:
                    return result[0].get('name', '未知地标')
            return '未知地标'
        except Exception:
            return '未知地标'
    
    async def _trigger_landmark_conversation(self, landmark_name: str, landmark_result: Dict):
        """
        通过对话系统触发地标讲解，实现流式输出和历史记录保存
        """
        try:
            if not self.websocket_handler or not self.websocket_handler.client_connections:
                logger.warning("没有活跃的WebSocket连接")
                return
            
            # 构建用户输入消息，包含地标信息
            user_message = f"我刚刚上传了一张图片，识别出的地标是：{landmark_name}。请为我详细介绍这个地标的历史背景、文化意义、建筑特色、最佳游览时间和实用建议。"
            
            # 为每个连接的客户端触发对话
            for client_uid, websocket in self.websocket_handler.client_connections.items():
                try:
                    context = self.websocket_handler.client_contexts[client_uid]
                    
                    # 构建包含地标信息的BatchInput
                    batch_input = BatchInput(
                        texts=[
                            TextData(
                                source=TextSource.INPUT,
                                content=user_message,
                                from_name=context.character_config.human_name
                            )
                        ],
                        images=[
                            ImageData(
                                source=ImageSource.UPLOAD,
                                data=landmark_result,  # 传递地标识别结果作为上下文
                                mime_type="application/json"
                            )
                        ]
                    )
                    
                    # 通过正常的对话处理流程触发
                    await handle_conversation_trigger(
                        msg_type="text-input",
                        data={
                            "text": user_message,
                            "images": None  # 图片已经在batch_input中处理
                        },
                        client_uid=client_uid,
                        context=context,
                        websocket=websocket,
                        client_contexts=self.websocket_handler.client_contexts,
                        client_connections=self.websocket_handler.client_connections,
                        chat_group_manager=self.websocket_handler.chat_group_manager,
                        received_data_buffers=self.websocket_handler.received_data_buffers,
                        current_conversation_tasks=self.websocket_handler.current_conversation_tasks,
                        broadcast_to_group=self.websocket_handler.broadcast_to_group,
                    )
                    
                    logger.info(f"已为客户端 {client_uid} 触发地标讲解对话")
                    
                except Exception as e:
                    logger.error(f"为客户端 {client_uid} 触发对话失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"触发地标对话失败: {str(e)}")
            raise
    
    async def send_landmark_result_to_clients(self, landmark_info: str):
        """
        发送地标识别结果给所有客户端（保留兼容性）
        注意：建议使用_trigger_landmark_conversation来获得更好的用户体验
        """
        try:
            if not self.websocket_handler or not self.websocket_handler.client_connections:
                logger.warning("没有活跃的WebSocket连接")
                return
                
            # 发送简单的文本消息
            for client_uid, websocket in self.websocket_handler.client_connections.items():
                try:
                    await websocket.send_text(json.dumps({
                        "type": "landmark_recognition_result",
                        "message": landmark_info
                    }))
                    
                    logger.info(f"地标信息已发送给客户端 {client_uid}")
                    
                except Exception as e:
                    logger.error(f"发送地标信息给客户端 {client_uid} 失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"发送地标结果失败: {str(e)}")
            raise