import re
from typing import Dict, Any, Optional
from .base_detector import BaseIntentDetector

class TrafficIntentDetector(BaseIntentDetector):
    """
    交通状况意图检测器
    """
    
    def detect(self, text: str) -> bool:
        """
        检测文本中是否包含交通状况查询意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否检测到交通状况查询意图
        """
        traffic_patterns = [
            r'(.+?)(?:的|在|at|in)\s*(.+?)(?:的|)\s*(?:交通|traffic|路况)(?:怎么样|如何|情况|状况|condition)',
            r'(.+?)(?:现在|now|当前|current)(?:的|)\s*(?:交通|traffic|路况)(?:怎么样|如何|情况|状况|condition)',
            r'(?:交通|traffic|路况)(?:怎么样|如何|情况|状况|condition)(?:.*?)(?:在|at|in)\s*(.+)'
        ]
        
        for pattern in traffic_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取交通状况查询相关的参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            包含location和radius的字典
        """
        params = {}
        
        # 提取地点
        traffic_patterns = [
            r'(.+?)(?:的|在|at|in)\s*(.+?)(?:的|)\s*(?:交通|traffic|路况)(?:怎么样|如何|情况|状况|condition)',
            r'(.+?)(?:现在|now|当前|current)(?:的|)\s*(?:交通|traffic|路况)(?:怎么样|如何|情况|状况|condition)',
            r'(?:交通|traffic|路况)(?:怎么样|如何|情况|状况|condition)(?:.*?)(?:在|at|in)\s*(.+)'
        ]
        
        for pattern in traffic_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # 提取地点名称
                groups = match.groups()
                location = next((g for g in groups if g and len(g.strip()) > 0), None)
                if location:
                    params["location"] = location.strip()
                    break
        
        # 提取半径（如果有）
        radius_match = re.search(r'(?:半径|radius|范围)\s*(\d+)\s*(?:公里|km|千米)', text, re.IGNORECASE)
        if radius_match:
            params["radius"] = float(radius_match.group(1))
        else:
            params["radius"] = 2.0  # 默认2公里
        
        return params