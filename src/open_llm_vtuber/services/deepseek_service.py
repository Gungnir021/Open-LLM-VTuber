import os
import requests
from loguru import logger
from typing import Dict

class DeepSeekService:
    """DeepSeek AI讲解服务"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
    
    def _extract_landmark_info(self, landmark_data: Dict) -> tuple[str, str, float]:
        """
        从百度API结果中提取地标信息
        
        Args:
            landmark_data: 百度API返回的地标数据
            
        Returns:
            (地标名称, 位置, 置信度)
        """
        if 'result' not in landmark_data:
            raise Exception("地标识别结果格式异常")
        
        landmarks = landmark_data['result']
        
        if isinstance(landmarks, dict) and 'landmark' in landmarks:
            # 百度API返回格式
            landmark_name = landmarks['landmark']
            location = '未知位置'
            score = 1.0
        elif isinstance(landmarks, list) and landmarks:
            # 其他可能的格式
            landmark_info = landmarks[0]
            landmark_name = landmark_info.get('name', '未知地标')
            location = landmark_info.get('location', '未知位置')
            score = landmark_info.get('score', 0)
        else:
            raise Exception("未识别到明确的地标信息")
        
        return landmark_name, location, score
    
    def _build_prompt(self, landmark_name: str, location: str, score: float) -> str:
        """
        构建DeepSeek提示词
        """
        return f"""
地标名称: {landmark_name}
位置: {location}
识别置信度: {score}

请作为一位专业的旅游向导，用自然、生动的语言为我详细介绍这个地标。请包含以下内容：
1. 地标的历史背景和文化意义
2. 建筑特色或自然景观特点
3. 最佳游览时间和方式
4. 周边值得游览的景点
5. 实用的旅游建议和注意事项

请用温馨、专业的语调，让介绍既有知识性又有趣味性。
"""
    
    async def get_landmark_explanation(self, landmark_data: Dict) -> str:
        """
        获取地标讲解
        
        Args:
            landmark_data: 百度API返回的地标识别结果
            
        Returns:
            地标讲解文本
        """
        if not self.api_key:
            raise Exception("未配置DeepSeek API密钥")
        
        try:
            # 提取地标信息
            landmark_name, location, score = self._extract_landmark_info(landmark_data)
            logger.info(f"处理地标: {landmark_name} at {location} (score: {score})")
            
            # 构建提示词
            prompt = self._build_prompt(landmark_name, location, score)
            
            # 准备API请求
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一位专业的旅游向导，擅长用生动有趣的语言介绍世界各地的著名地标和景点。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            # 调用API
            logger.info("调用DeepSeek API")
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=60
            )
            
            logger.info(f"DeepSeek API响应状态: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                explanation = result['choices'][0]['message']['content']
                logger.info("成功获取DeepSeek讲解")
                return explanation
            else:
                logger.error(f"DeepSeek API失败: {response.status_code} - {response.text}")
                raise Exception(f"调用DeepSeek API失败: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning("DeepSeek API超时")
            raise Exception("DeepSeek API连接超时，请稍后重试")
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API请求错误: {str(e)}")
            raise Exception(f"DeepSeek API请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"获取地标讲解异常: {str(e)}")
            raise