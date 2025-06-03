import base64
import io
from PIL import Image
from loguru import logger

class ImageService:
    """图片处理服务"""
    
    @staticmethod
    async def process_image_for_api(image_data: bytes, max_size: int = 1024) -> str:
        """
        处理图片：调整大小并转换为base64格式
        
        Args:
            image_data: 图片二进制数据
            max_size: 最大尺寸限制
            
        Returns:
            base64编码的图片字符串
        """
        try:
            # 打开图片
            image = Image.open(io.BytesIO(image_data))
            
            # 转换为RGB格式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 调整图片大小
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # 转换为JPEG格式并编码为base64
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return img_base64
            
        except Exception as e:
            logger.error(f"图片处理失败: {str(e)}")
            raise Exception(f"图片处理失败: {str(e)}")
    
    @staticmethod
    def validate_image_file(content_type: str, file_size: int, max_size_mb: int = 5) -> tuple[bool, str]:
        """
        验证图片文件
        
        Args:
            content_type: 文件MIME类型
            file_size: 文件大小（字节）
            max_size_mb: 最大文件大小（MB）
            
        Returns:
            (是否有效, 错误信息)
        """
        if not content_type.startswith('image/'):
            return False, "请上传图片文件"
        
        if file_size > max_size_mb * 1024 * 1024:
            return False, f"图片文件过大，请上传小于{max_size_mb}MB的图片"
        
        return True, ""