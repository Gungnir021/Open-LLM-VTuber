import re
from typing import Dict, Any, Optional
from .base_detector import BaseIntentDetector

class RouteIntentDetector(BaseIntentDetector):
    """
    路线查询意图检测器
    """
    
    def detect(self, text: str) -> bool:
        """
        检测文本中是否包含路线查询意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否检测到路线查询意图
        """
        route_patterns = [
            r'(?:从|from)\s*(.+?)\s*(?:到|去|至|to)\s*(.+?)\s*(?:怎么走|怎么去|如何到达|路线|route|path|direction)',
            r'(?:到|去|至|to)\s*(.+?)\s*(?:怎么走|怎么去|如何到达|路线|route|path|direction)',
            r'(.+?)\s*(?:到|去|至|to)\s*(.+?)\s*(?:的|)(?:路线|route|path|direction|交通)'
        ]
        
        for pattern in route_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取路线查询相关的参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            包含origin和destination的字典
        """
        params = {}
        
        # 提取起点和终点
        route_patterns = [
            r'(?:从|from)\s*(.+?)\s*(?:到|去|至|to)\s*(.+?)\s*(?:怎么走|怎么去|如何到达|路线|route|path|direction)',
            r'(?:从|from)\s*(.+?)\s*(?:到|去|至|to)\s*(.+)',
            r'(.+?)\s*(?:到|去|至|to)\s*(.+?)\s*(?:的|)(?:路线|route|path|direction|交通)'
        ]
        
        for pattern in route_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and len(match.groups()) >= 2:
                origin = match.group(1).strip() if match.group(1) else None
                destination = match.group(2).strip() if match.group(2) else None
                
                if origin and destination:
                    params["origin"] = origin
                    params["destination"] = destination
                    break
                elif destination and not origin:
                    # 如果只有目的地，起点可能是当前位置
                    params["destination"] = destination
                    params["origin"] = "当前位置"
                    break
        
        return params