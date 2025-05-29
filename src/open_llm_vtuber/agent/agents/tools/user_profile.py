import json
from typing import Dict, List, Optional
from datetime import datetime

class UserProfileManager:
    """用户信息管理器"""
    
    def __init__(self):
        self.user_profiles = {}
    
    def collect_user_info(self, user_id: str, info: Dict) -> Dict:
        """收集用户基本信息"""
        required_fields = [
            'travel_dates',  # 旅行时间
            'dietary_restrictions',  # 饮食禁忌
            'preferences',  # 偏好
            'budget',  # 预算
            'travel_style'  # 旅行风格
        ]
        
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {}
        
        self.user_profiles[user_id].update(info)
        return {"status": "success", "message": "用户信息已更新"}
    
    def get_user_profile(self, user_id: str) -> Dict:
        """获取用户档案"""
        return self.user_profiles.get(user_id, {})