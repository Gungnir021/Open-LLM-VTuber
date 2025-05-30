import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .base_detector import BaseIntentDetector

class PackingIntentDetector(BaseIntentDetector):
    """
    出行清单意图检测器
    """
    
    def detect(self, text: str) -> bool:
        """
        检测文本中是否包含出行清单生成意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否检测到出行清单生成意图
        """
        packing_patterns = [
            r'(?:帮我|help|请|please|)(?:准备|prepare|制作|make|生成|generate)\s*(?:.*?)(?:出行|旅行|旅游|trip|travel)\s*(?:清单|物品|list|packing|物品清单)',
            r'(?:去|to|前往|visit)\s*(.+?)\s*(?:需要|should|必须|must|要|have to)\s*(?:带|pack|准备|prepare)\s*(?:什么|哪些|what)\s*(?:东西|物品|item|thing)',
            r'(?:出行|旅行|旅游|trip|travel)\s*(?:清单|物品|list|packing|物品清单)'
        ]
        
        for pattern in packing_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取出行清单相关的参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            包含destination、travel_dates和travel_style的字典
        """
        params = {}
        
        # 提取目的地
        destination_patterns = [
            r'(?:去|to|前往|visit)\s*(.+?)\s*(?:旅游|旅行|玩|游玩|travel|trip|tour)',
            r'(?:去|to|前往|visit)\s*(.+?)\s*(?:需要|should|必须|must|要|have to)\s*(?:带|pack|准备|prepare)',
            r'(?:在|at|in)\s*(.+?)\s*(?:的|)(?:出行|旅行|旅游|trip|travel)',
            r'(?:规划|plan)\s*(?:一下|)\s*(?:去|to|)\s*(.+?)\s*(?:\d+|几|)\s*(?:天|日|days)\s*(?:旅游|旅行|玩|游玩|travel|trip|tour)'
        ]
        
        for pattern in destination_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                destination = match.group(1).strip()
                params["destination"] = destination
                break
        
        # 提取日期
        today = datetime.now()
        
        # 尝试提取具体日期范围
        date_pattern = r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)\s*(?:至|到|-)\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)'
        date_match = re.search(date_pattern, text)
        
        if date_match:
            # 处理具体的日期范围
            start_date_str = date_match.group(1)
            end_date_str = date_match.group(2)
            
            # 标准化日期格式
            start_date_str = start_date_str.replace('年', '-').replace('月', '-').replace('日', '').replace('/', '-')
            end_date_str = end_date_str.replace('年', '-').replace('月', '-').replace('日', '').replace('/', '-')
            
            params["travel_dates"] = {
                "start_date": start_date_str,
                "end_date": end_date_str
            }
        else:
            # 尝试提取天数
            days_pattern = r'(\d+)\s*(?:天|days|日)'
            days_match = re.search(days_pattern, text)
            
            if days_match:
                days = int(days_match.group(1))
                start_date = today
                end_date = today + timedelta(days=days-1)
                
                params["travel_dates"] = {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }
            else:
                # 默认3天行程
                params["travel_dates"] = {
                    "start_date": today.strftime("%Y-%m-%d"),
                    "end_date": (today + timedelta(days=2)).strftime("%Y-%m-%d")
                }
        
        # 提取旅行风格
        style_keywords = {
            "商务": ["商务", "出差", "business", "work"],
            "休闲": ["休闲", "放松", "casual", "relax"],
            "冒险": ["冒险", "探险", "户外", "adventure", "outdoor"],
            "家庭": ["家庭", "孩子", "亲子", "family", "kid", "child"],
            "奢华": ["奢华", "豪华", "luxury", "high-end"],
            "经济": ["经济", "省钱", "budget", "economic", "cheap"]
        }
        
        for style, keywords in style_keywords.items():
            for keyword in keywords:
                if keyword in text.lower():
                    params["travel_style"] = style
                    break
            if "travel_style" in params:
                break
        
        if "travel_style" not in params:
            params["travel_style"] = "休闲"  # 默认休闲风格
        
        return params