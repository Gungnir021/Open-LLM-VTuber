import re
from typing import Dict, Any, Optional, Tuple
from .base_detector import BaseIntentDetector

class WeatherIntentDetector(BaseIntentDetector):
    """
    天气意图检测器
    """
    
    def detect(self, text: str) -> bool:
        """
        检测文本中是否包含天气查询意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否检测到天气查询意图
        """
        weather_patterns = [
            r'(.*?)(?:的|在|at|in)\s*(.+?)(?:的|)\s*(?:天气|weather)(?:怎么样|如何|情况|forecast|report|condition)',
            r'(.+?)(?:今天|today|现在|now|当前|current)(?:的|)\s*(?:天气|weather)',
            r'(?:天气|weather)(?:怎么样|如何|情况|forecast|report|condition)(?:.*?)(?:在|at|in)\s*(.+)'
        ]
        
        for pattern in weather_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取天气查询相关的参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            包含location和unit的字典
        """
        params = {}
        
        # 提取地点
        weather_patterns = [
            r'(.*?)(?:的|在|at|in)\s*(.+?)(?:的|)\s*(?:天气|weather)(?:怎么样|如何|情况|forecast|report|condition)',
            r'(.+?)(?:今天|today|现在|now|当前|current)(?:的|)\s*(?:天气|weather)',
            r'(?:天气|weather)(?:怎么样|如何|情况|forecast|report|condition)(?:.*?)(?:在|at|in)\s*(.+)'
        ]
        
        for pattern in weather_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # 提取地点名称
                groups = match.groups()
                location = next((g for g in groups if g and len(g.strip()) > 0), None)
                if location:
                    params["location"] = location.strip()
                    break
        
        # 提取温度单位（如果有）
        if "华氏" in text or "fahrenheit" in text.lower():
            params["unit"] = "fahrenheit"
        else:
            params["unit"] = "celsius"
        
        return params