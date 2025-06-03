import os
import requests
from loguru import logger
from typing import Dict

class BaiduLandmarkService:
    """百度地标识别服务"""
    
    def __init__(self):
        self.api_key = os.getenv("BAIDU_API_KEY")
        self.secret_key = os.getenv("BAIDU_SECRET_KEY")
        self._access_token = None
    
    async def _get_access_token(self) -> str:
        """
        获取百度API访问令牌
        """
        if not self.api_key or not self.secret_key:
            raise Exception("未配置百度API密钥，请在.env文件中设置BAIDU_API_KEY和BAIDU_SECRET_KEY")
        
        try:
            token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"
            response = requests.get(token_url, timeout=10)
            result = response.json()
            
            access_token = result.get('access_token')
            if not access_token:
                raise Exception("获取百度API访问令牌失败")
            
            return access_token
            
        except Exception as e:
            logger.error(f"获取访问令牌失败: {str(e)}")
            raise
    
    async def recognize_landmark(self, img_base64: str) -> Dict:
        """
        识别地标
        
        Args:
            img_base64: base64编码的图片
            
        Returns:
            地标识别结果
        """
        try:
            access_token = await self._get_access_token()
            
            # 调用地标识别API
            api_url = f"https://aip.baidubce.com/rest/2.0/image-classify/v1/landmark?access_token={access_token}"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            payload = {'image': img_base64}
            
            response = requests.post(api_url, headers=headers, data=payload, timeout=15)
            result = response.json()
            
            logger.info(f"百度API响应: {result}")
            
            if 'error_code' in result:
                logger.error(f"百度API错误: {result}")
                raise Exception(f"百度API调用失败 - {result.get('error_msg', '未知错误')}")
            
            return result
            
        except Exception as e:
            logger.error(f"地标识别异常: {str(e)}")
            raise