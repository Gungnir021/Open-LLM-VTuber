from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, Tuple

class BaseIntentDetector(ABC):
    """
    意图检测器基类
    """
    
    @abstractmethod
    def detect(self, text: str) -> bool:
        """
        检测文本中是否包含特定意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否检测到意图
        """
        pass
    
    @abstractmethod
    def extract_params(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取意图相关的参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            提取的参数字典
        """
        pass