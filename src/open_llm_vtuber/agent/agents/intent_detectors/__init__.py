from typing import Dict, Type, List
from .base_detector import BaseIntentDetector
from .weather_detector import WeatherIntentDetector
from .traffic_detector import TrafficIntentDetector
from .route_detector import RouteIntentDetector
from .nearby_facility_detector import NearbyFacilityIntentDetector
from .itinerary_detector import ItineraryIntentDetector
from .packing_detector import PackingIntentDetector
from .social_media_detector import SocialMediaIntentDetector
from .user_info_detector import UserInfoIntentDetector
from .scenic_info_detector import ScenicInfoIntentDetector

class IntentDetectorFactory:
    """
    意图检测器工厂，负责创建和管理各种意图检测器
    """
    
    def __init__(self):
        self._detectors: Dict[str, BaseIntentDetector] = {
            "weather": WeatherIntentDetector(),
            "traffic": TrafficIntentDetector(),
            "route": RouteIntentDetector(),
            "nearby_facility": NearbyFacilityIntentDetector(),
            "itinerary": ItineraryIntentDetector(),
            "packing": PackingIntentDetector(),
            "social_media": SocialMediaIntentDetector(),
            "user_info": UserInfoIntentDetector(),
            "scenic_info": ScenicInfoIntentDetector()
        }
    
    def get_detector(self, intent_type: str) -> BaseIntentDetector:
        """
        获取指定类型的意图检测器
        
        Args:
            intent_type: 意图类型
            
        Returns:
            意图检测器实例
            
        Raises:
            ValueError: 如果意图类型不存在
        """
        if intent_type not in self._detectors:
            raise ValueError(f"未知的意图类型: {intent_type}")
        return self._detectors[intent_type]
    
    def get_available_intents(self) -> List[str]:
        """
        获取所有可用的意图类型
        
        Returns:
            意图类型列表
        """
        return list(self._detectors.keys())