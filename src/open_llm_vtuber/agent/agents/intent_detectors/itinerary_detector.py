import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .base_detector import BaseIntentDetector

class ItineraryIntentDetector(BaseIntentDetector):
    """
    行程规划意图检测器
    """
    
    def detect(self, text: str) -> bool:
        """
        检测文本中是否包含行程规划意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否检测到行程规划意图
        """
        itinerary_patterns = [
            r'(?:帮我|help|请|please|)(?:规划|plan|制定|make|生成|generate)\s*(?:.*?)(?:行程|旅行|旅游|trip|travel|itinerary|计划|plan)',
            r'(?:去|to|前往|visit)\s*(.+?)\s*(?:旅游|旅行|玩|游玩|travel|trip|tour)\s*(?:行程|计划|规划|itinerary|plan)',
            r'(?:.*?)(?:几天|days|天数|duration)\s*(?:的|)\s*(?:行程|旅行|旅游|trip|travel|itinerary|计划|plan)'
        ]
        
        for pattern in itinerary_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取行程规划相关的参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            包含destination、start_date、end_date和user_preferences的字典
        """
        params = {}
        
        # 提取目的地
        destination_patterns = [
            r'(?:去|to|前往|visit)\s*(.+?)\s*(?:旅游|旅行|玩|游玩|travel|trip|tour)',
            r'(?:在|at|in)\s*(.+?)\s*(?:的|)(?:行程|旅行|旅游|trip|travel|itinerary)',
            r'(?:规划|plan|制定|make|生成|generate)\s*(.+?)\s*(?:的|)(?:行程|旅行|旅游|trip|travel|itinerary)'
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
            
            params["start_date"] = start_date_str
            params["end_date"] = end_date_str
        else:
            # 尝试提取天数
            days_pattern = r'(\d+)\s*(?:天|days|日)'
            days_match = re.search(days_pattern, text)
            
            if days_match:
                days = int(days_match.group(1))
                start_date = today
                end_date = today + timedelta(days=days-1)
                
                params["start_date"] = start_date.strftime("%Y-%m-%d")
                params["end_date"] = end_date.strftime("%Y-%m-%d")
            else:
                # 默认3天行程
                params["start_date"] = today.strftime("%Y-%m-%d")
                params["end_date"] = (today + timedelta(days=2)).strftime("%Y-%m-%d")
        
        # 提取用户偏好
        preferences = {}
        
        # 提取预算
        budget_pattern = r'(?:预算|budget)\s*(\d+)\s*(?:元|块|yuan|rmb|cny)'
        budget_match = re.search(budget_pattern, text, re.IGNORECASE)
        if budget_match:
            preferences["budget"] = int(budget_match.group(1))
        
        # 提取旅行风格
        style_keywords = {
            "文化": ["文化", "历史", "古迹", "博物馆", "culture", "history", "museum"],
            "美食": ["美食", "吃", "餐厅", "food", "cuisine", "eat", "restaurant"],
            "购物": ["购物", "买", "商场", "shopping", "shop", "mall"],
            "自然": ["自然", "风景", "景色", "公园", "nature", "scenery", "park"],
            "冒险": ["冒险", "刺激", "极限", "adventure", "exciting", "extreme"],
            "放松": ["放松", "休闲", "spa", "relax", "leisure"],
            "家庭": ["家庭", "孩子", "亲子", "family", "kid", "child"]
        }
        
        for style, keywords in style_keywords.items():
            for keyword in keywords:
                if keyword in text.lower():
                    preferences["style"] = style
                    break
            if "style" in preferences:
                break
        
        # 提取饮食限制
        diet_keywords = {
            "素食": ["素食", "素", "vegetarian", "vegan"],
            "无麸质": ["无麸质", "gluten-free"],
            "无乳糖": ["无乳糖", "lactose-free"],
            "清真": ["清真", "halal"],
            "无坚果": ["无坚果", "nut-free", "坚果过敏"]
        }
        
        diet_restrictions = []
        for diet, keywords in diet_keywords.items():
            for keyword in keywords:
                if keyword in text.lower():
                    diet_restrictions.append(diet)
                    break
        
        if diet_restrictions:
            preferences["diet_restrictions"] = diet_restrictions
        
        params["user_preferences"] = preferences
        
        return params