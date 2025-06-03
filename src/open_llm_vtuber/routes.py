import json
from uuid import uuid4
from fastapi import APIRouter, WebSocket, UploadFile, File, Response
from starlette.websockets import WebSocketDisconnect
from loguru import logger
from .service_context import ServiceContext
from .websocket_handler import WebSocketHandler
from .services.travel_agent_service import TravelAgentService
from .services.image_service import ImageService

def init_client_ws_route(default_context_cache: ServiceContext) -> APIRouter:
    router = APIRouter()
    ws_handler = WebSocketHandler(default_context_cache)
    
    # 设置 websocket_handler 引用
    default_context_cache.websocket_handler = ws_handler
    
    @router.websocket("/client-ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for client connections"""
        await websocket.accept()
        client_uid = str(uuid4())

        try:
            await ws_handler.handle_new_connection(websocket, client_uid)
            await ws_handler.handle_websocket_communication(websocket, client_uid)
        except WebSocketDisconnect:
            await ws_handler.handle_disconnect(client_uid)
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
            await ws_handler.handle_disconnect(client_uid)
            raise

    return router


def init_webtool_routes(default_context_cache: ServiceContext) -> APIRouter:
    router = APIRouter()
    
    # 初始化服务，传入 websocket_handler
    travel_agent = TravelAgentService(default_context_cache.websocket_handler)
    image_service = ImageService()
    
    @router.post("/upload-image")
    async def upload_image_for_landmark(file: UploadFile = File(...)):
        """上传图片进行地标识别和AI讲解"""
        logger.info(f"收到图片上传请求: {file.filename}")
        
        try:
            # 1. 验证文件
            contents = await file.read()
            is_valid, error_msg = image_service.validate_image_file(
                file.content_type, len(contents)
            )
            
            if not is_valid:
                return Response(
                    content=json.dumps({"error": error_msg}),
                    status_code=400,
                    media_type="application/json"
                )
            
            # 2. 处理图片并获取讲解
            result = await travel_agent.process_landmark_image(contents)
            
            if not result["success"]:
                return Response(
                    content=json.dumps({"error": result["error"]}),
                    status_code=500,
                    media_type="application/json"
                )
            
            # 3. 地标识别成功，AI讲解已通过对话系统异步处理
            landmark_name = result["landmark_name"]
            
            logger.info(f"地标识别成功：{landmark_name}，已触发AI讲解") 
            
            # 4. 返回 HTTP 响应
            result["message"] = "地标识别和讲解获取成功，已发送到对话界面"
            
            logger.info("地标识别和讲解处理完成")
            return result
            
        except Exception as e:
            logger.error(f"处理图片上传请求时发生错误: {e}")
            return Response(
                content=json.dumps({"error": f"处理图片时发生错误: {str(e)}"}),
                status_code=500,
                media_type="application/json"
            )

    return router