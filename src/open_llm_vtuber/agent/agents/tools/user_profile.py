import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

class UserProfileManager:
    """用户信息管理器
    
    负责收集、存储和管理用户的旅行相关信息，包括基本信息、旅行偏好、饮食禁忌等。
    同时提供用户反馈收集和个性化优化功能。
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """初始化用户信息管理器
        
        Args:
            storage_path: 用户数据存储路径，如果为None则不进行持久化存储
        """
        self.user_profiles = {}
        self.storage_path = storage_path
        
        # 如果指定了存储路径且文件存在，则加载已有数据
        if storage_path and os.path.exists(storage_path):
            try:
                with open(storage_path, 'r', encoding='utf-8') as f:
                    self.user_profiles = json.load(f)
            except Exception as e:
                print(f"加载用户数据失败: {e}")
    
    def _save_profiles(self) -> None:
        """保存用户数据到文件"""
        if self.storage_path:
            try:
                with open(self.storage_path, 'w', encoding='utf-8') as f:
                    json.dump(self.user_profiles, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存用户数据失败: {e}")
    
    def collect_user_info(self, user_id: str, info: Dict[str, Any]) -> Dict:
        """收集用户基本信息
        
        Args:
            user_id: 用户ID
            info: 用户信息字典，可包含以下字段：
                - name: 姓名
                - age: 年龄
                - gender: 性别
                - travel_dates: 旅行时间 {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
                - destination: 目的地
                - dietary_restrictions: 饮食禁忌列表
                - preferences: 偏好字典 {"activity": [], "food": [], "accommodation": []}
                - budget: 预算范围 {"min": 数值, "max": 数值, "currency": "CNY"}
                - travel_style: 旅行风格 (如"休闲", "探险", "文化", "美食"等)
                - transportation: 交通方式
                - accommodation_type: 住宿类型偏好
                - special_needs: 特殊需求
                - language: 语言偏好
        
        Returns:
            包含状态和消息的字典
        """
        required_fields = [
            'travel_dates',  # 旅行时间
            'destination',  # 目的地
            'dietary_restrictions',  # 饮食禁忌
            'preferences',  # 偏好
            'budget',  # 预算
            'travel_style'  # 旅行风格
        ]
        
        # 检查必填字段
        missing_fields = [field for field in required_fields if field not in info]
        if missing_fields:
            return {
                "status": "error", 
                "message": f"缺少必填字段: {', '.join(missing_fields)}"
            }
        
        # 验证日期格式
        if 'travel_dates' in info:
            try:
                start_date = datetime.strptime(info['travel_dates']['start_date'], '%Y-%m-%d')
                end_date = datetime.strptime(info['travel_dates']['end_date'], '%Y-%m-%d')
                if end_date < start_date:
                    return {"status": "error", "message": "结束日期不能早于开始日期"}
            except (KeyError, ValueError):
                return {"status": "error", "message": "旅行日期格式错误，请使用YYYY-MM-DD格式"}
        
        # 初始化用户档案（如果不存在）
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                "basic_info": {},
                "travel_history": [],
                "feedback": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        
        # 更新基本信息
        self.user_profiles[user_id]["basic_info"].update(info)
        self.user_profiles[user_id]["updated_at"] = datetime.now().isoformat()
        
        # 保存数据
        self._save_profiles()
        
        return {"status": "success", "message": "用户信息已更新"}
    
    def get_user_profile(self, user_id: str) -> Dict:
        """获取用户档案
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户档案字典，如果用户不存在则返回空字典
        """
        return self.user_profiles.get(user_id, {})
    
    def add_travel_history(self, user_id: str, travel_info: Dict) -> Dict:
        """添加用户旅行历史记录
        
        Args:
            user_id: 用户ID
            travel_info: 旅行信息，包含目的地、日期、活动等
            
        Returns:
            操作状态
        """
        if user_id not in self.user_profiles:
            return {"status": "error", "message": "用户不存在"}
        
        # 添加时间戳
        travel_info["recorded_at"] = datetime.now().isoformat()
        
        # 添加到旅行历史
        if "travel_history" not in self.user_profiles[user_id]:
            self.user_profiles[user_id]["travel_history"] = []
            
        self.user_profiles[user_id]["travel_history"].append(travel_info)
        self.user_profiles[user_id]["updated_at"] = datetime.now().isoformat()
        
        # 保存数据
        self._save_profiles()
        
        return {"status": "success", "message": "旅行历史已添加"}
    
    def collect_feedback(self, user_id: str, feedback: Dict) -> Dict:
        """收集用户反馈
        
        Args:
            user_id: 用户ID
            feedback: 反馈信息，包含评分、评论、建议等
            
        Returns:
            操作状态
        """
        if user_id not in self.user_profiles:
            return {"status": "error", "message": "用户不存在"}
        
        # 添加时间戳
        feedback["submitted_at"] = datetime.now().isoformat()
        
        # 添加到反馈列表
        if "feedback" not in self.user_profiles[user_id]:
            self.user_profiles[user_id]["feedback"] = []
            
        self.user_profiles[user_id]["feedback"].append(feedback)
        self.user_profiles[user_id]["updated_at"] = datetime.now().isoformat()
        
        # 保存数据
        self._save_profiles()
        
        return {"status": "success", "message": "反馈已收集"}
    
    def analyze_preferences(self, user_id: str) -> Dict:
        """分析用户偏好
        
        基于用户的基本信息、旅行历史和反馈，分析用户的偏好
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户偏好分析结果
        """
        if user_id not in self.user_profiles:
            return {"status": "error", "message": "用户不存在"}
        
        profile = self.user_profiles[user_id]
        basic_info = profile.get("basic_info", {})
        travel_history = profile.get("travel_history", [])
        feedback = profile.get("feedback", [])
        
        # 提取偏好信息
        preferences = basic_info.get("preferences", {})
        travel_style = basic_info.get("travel_style", "")
        dietary_restrictions = basic_info.get("dietary_restrictions", [])
        
        # 从旅行历史中提取常去的地点类型
        destinations = [trip.get("destination", "") for trip in travel_history]
        
        # 从反馈中提取高评分的项目
        liked_items = []
        for fb in feedback:
            if fb.get("rating", 0) >= 4:  # 假设评分是1-5
                if "liked_items" in fb:
                    liked_items.extend(fb["liked_items"])
        
        # 构建分析结果
        analysis = {
            "preferred_destinations": destinations,
            "travel_style": travel_style,
            "dietary_restrictions": dietary_restrictions,
            "activity_preferences": preferences.get("activity", []),
            "food_preferences": preferences.get("food", []),
            "accommodation_preferences": preferences.get("accommodation", []),
            "liked_items": liked_items
        }
        
        return {
            "status": "success", 
            "message": "偏好分析完成",
            "analysis": analysis
        }
    
    def update_user_preferences(self, user_id: str, new_preferences: Dict) -> Dict:
        """更新用户偏好
        
        Args:
            user_id: 用户ID
            new_preferences: 新的偏好信息
            
        Returns:
            操作状态
        """
        if user_id not in self.user_profiles:
            return {"status": "error", "message": "用户不存在"}
        
        if "basic_info" not in self.user_profiles[user_id]:
            self.user_profiles[user_id]["basic_info"] = {}
            
        if "preferences" not in self.user_profiles[user_id]["basic_info"]:
            self.user_profiles[user_id]["basic_info"]["preferences"] = {}
        
        # 更新偏好
        self.user_profiles[user_id]["basic_info"]["preferences"].update(new_preferences)
        self.user_profiles[user_id]["updated_at"] = datetime.now().isoformat()
        
        # 保存数据
        self._save_profiles()
        
        return {"status": "success", "message": "用户偏好已更新"}
    
    def get_travel_recommendations(self, user_id: str) -> Dict:
        """基于用户档案生成旅行推荐
        
        Args:
            user_id: 用户ID
            
        Returns:
            旅行推荐结果
        """
        if user_id not in self.user_profiles:
            return {"status": "error", "message": "用户不存在"}
        
        # 获取用户偏好分析
        preference_analysis = self.analyze_preferences(user_id)
        if preference_analysis["status"] != "success":
            return preference_analysis
        
        analysis = preference_analysis["analysis"]
        
        # 这里可以实现更复杂的推荐逻辑，目前返回简单的基于偏好的推荐
        recommendations = {
            "destinations": [],
            "activities": [],
            "accommodations": [],
            "restaurants": []
        }
        
        # 基于用户偏好填充推荐内容
        # 实际应用中，这里可能需要调用外部API或数据库来获取真实的推荐
        
        return {
            "status": "success",
            "message": "旅行推荐生成完成",
            "recommendations": recommendations
        }