import re
from typing import Dict, Any, Optional
from .base_detector import BaseIntentDetector

class NearbyFacilityIntentDetector(BaseIntentDetector):
    """
    附近设施查询意图检测器
    """
    
    def detect(self, text: str) -> bool:
        """
        检测文本中是否包含附近设施查询意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否检测到附近设施查询意图
        """
        facility_types = ["洗手间", "厕所", "卫生间", "toilet", "wc", "休息", "休息处", "休息点", "rest", 
                        "餐厅", "餐馆", "吃饭", "restaurant", "food", "商场", "购物", "mall", "shop", 
                        "医院", "诊所", "医疗", "hospital", "clinic", "医疗点", "急救"]
        
        facility_pattern = "|".join(facility_types)
        nearby_patterns = [
            rf'(?:附近|周边|nearby|around)(?:的|有|)\s*({facility_pattern})',
            rf'(?:最近的|nearest|closest)\s*({facility_pattern})',
            rf'({facility_pattern})\s*(?:在哪里|在哪|where)'
        ]
        
        for pattern in nearby_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取附近设施查询相关的参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            包含location、facility_type和radius的字典
        """
        params = {}
        
        # 设施类型映射
        facility_mapping = {
            "洗手间": "洗手间", "厕所": "洗手间", "卫生间": "洗手间", "toilet": "洗手间", "wc": "洗手间",
            "休息": "休息点", "休息处": "休息点", "休息点": "休息点", "rest": "休息点",
            "餐厅": "餐厅", "餐馆": "餐厅", "吃饭": "餐厅", "restaurant": "餐厅", "food": "餐厅",
            "商场": "商场", "购物": "商场", "mall": "商场", "shop": "商场",
            "医院": "医院", "诊所": "医院", "医疗": "医院", "hospital": "医院", "clinic": "医院", 
            "医疗点": "医院", "急救": "医院"
        }
        
        # 提取设施类型
        facility_types = list(facility_mapping.keys())
        facility_pattern = "|".join(facility_types)
        facility_match = re.search(rf'({facility_pattern})', text, re.IGNORECASE)
        
        if facility_match:
            facility_type = facility_match.group(1).lower()
            params["facility_type"] = facility_mapping.get(facility_type, "餐厅")
        else:
            params["facility_type"] = "餐厅"  # 默认查找餐厅
        
        # 提取位置（如果有）
        location_match = re.search(r'(?:在|at|in)\s*(.+?)\s*(?:附近|周边|nearby|around)', text, re.IGNORECASE)
        if location_match:
            params["location"] = location_match.group(1).strip()
        else:
            params["location"] = "当前位置"  # 默认当前位置
        
        # 提取半径（如果有）
        radius_match = re.search(r'(?:半径|radius|范围)\s*(\d+)\s*(?:米|m|公里|km|千米)', text, re.IGNORECASE)
        if radius_match:
            radius = int(radius_match.group(1))
            # 如果单位是公里，转换为米
            if "公里" in text or "km" in text.lower() or "千米" in text:
                radius *= 1000
            params["radius"] = radius
        else:
            params["radius"] = 1000  # 默认1000米
        
        return params