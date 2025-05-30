import re
from typing import Dict, Any, Optional
from .base_detector import BaseIntentDetector

class ScenicInfoIntentDetector(BaseIntentDetector):
    """
    景点信息查询意图检测器
    """
    
    def detect(self, text: str) -> bool:
        """
        检测文本中是否包含景点信息查询意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否检测到景点信息查询意图
        """
        scenic_patterns = [
            r'(?:介绍|introduce|tell|讲解|explain|about)\s*(?:一下|me|)\s*(.+?)\s*(?:这个|这座|这处|this|the|)\s*(?:景点|景区|名胜|古迹|attraction|site|spot|place)',
            r'(.+?)\s*(?:景点|景区|名胜|古迹|attraction|site|spot|place)\s*(?:的|)\s*(?:介绍|简介|历史|信息|讲解|introduction|history|info|guide)',
            r'(?:这|this|that|)\s*(?:是|is|)\s*(?:什么|哪个|which|what)\s*(?:景点|景区|名胜|古迹|attraction|site|spot|place)'
        ]
        
        for pattern in scenic_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取景点信息查询相关的参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            包含spot_name和detail_level的字典
        """
        params = {}
        
        # 提取景点名称
        scenic_patterns = [
            r'(?:介绍|introduce|tell|讲解|explain|about)\s*(?:一下|me|)\s*(.+?)\s*(?:这个|这座|这处|this|the|)\s*(?:景点|景区|名胜|古迹|attraction|site|spot|place)',
            r'(.+?)\s*(?:景点|景区|名胜|古迹|attraction|site|spot|place)\s*(?:的|)\s*(?:介绍|简介|历史|信息|讲解|introduction|history|info|guide)'
        ]
        
        for pattern in scenic_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                spot_name = match.group(1).strip()
                if spot_name and len(spot_name) > 0:
                    params["spot_name"] = spot_name
                    break
        
        # 如果没有找到景点名称，可能是在询问当前位置的景点
        if "spot_name" not in params:
            current_location_patterns = [
                r'(?:这|this|that|)\s*(?:是|is|)\s*(?:什么|哪个|which|what)\s*(?:景点|景区|名胜|古迹|attraction|site|spot|place)',
                r'(?:我|I)\s*(?:现在|now|当前|current)\s*(?:在|at|in)\s*(?:哪里|哪个|什么|where|which|what)\s*(?:景点|景区|名胜|古迹|attraction|site|spot|place)'
            ]
            
            for pattern in current_location_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    params["spot_name"] = "当前位置"  # 表示需要获取当前位置的景点信息
                    break
        
        # 提取详细程度
        detail_level = "standard"  # 默认标准详细程度
        
        if re.search(r'(?:详细|具体|完整|全面|detailed|complete|full|comprehensive)', text, re.IGNORECASE):
            detail_level = "detailed"
        elif re.search(r'(?:简单|简略|简短|brief|short|concise)', text, re.IGNORECASE):
            detail_level = "brief"
        
        params["detail_level"] = detail_level
        
        return params