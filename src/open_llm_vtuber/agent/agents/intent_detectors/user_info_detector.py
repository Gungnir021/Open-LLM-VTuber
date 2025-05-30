import re
from typing import Dict, Any, Optional
from .base_detector import BaseIntentDetector

class UserInfoIntentDetector(BaseIntentDetector):
    """
    用户信息收集意图检测器
    """
    
    def detect(self, text: str) -> bool:
        """
        检测文本中是否包含用户信息收集意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否检测到用户信息收集意图
        """
        user_info_patterns = [
            r'(?:我|I)\s*(?:想|want|would like|plan)\s*(?:去|to|visit)\s*(.+?)\s*(?:旅游|旅行|玩|游玩|travel|trip|tour)',
            r'(?:我|I)\s*(?:的|my|)\s*(?:旅行|旅游|travel|trip)\s*(?:偏好|喜好|风格|preference|style)',
            r'(?:更新|update|修改|change|设置|set)\s*(?:我|my|)\s*(?:的|)\s*(?:信息|个人信息|旅行偏好|information|profile|preference)'
        ]
        
        for pattern in user_info_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取用户信息相关的参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            用户信息参数字典
        """
        params = {}
        
        # 提取目的地
        destination_pattern = r'(?:我|I)\s*(?:想|want|would like|plan)\s*(?:去|to|visit)\s*(.+?)\s*(?:旅游|旅行|玩|游玩|travel|trip|tour)'
        destination_match = re.search(destination_pattern, text, re.IGNORECASE)
        
        if destination_match:
            params["destination"] = destination_match.group(1).strip()
        
        # 提取日期
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
        
        # 提取预算
        budget_pattern = r'(?:预算|budget)\s*(\d+)\s*(?:元|块|yuan|rmb|cny)'
        budget_match = re.search(budget_pattern, text, re.IGNORECASE)
        if budget_match:
            params["budget"] = int(budget_match.group(1))
        
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
                    params["travel_style"] = style
                    break
            if "travel_style" in params:
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
            params["diet_restrictions"] = diet_restrictions
        
        return params