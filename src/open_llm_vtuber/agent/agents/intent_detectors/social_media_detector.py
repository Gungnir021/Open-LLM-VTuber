import re
from typing import Dict, Any, Optional
from .base_detector import BaseIntentDetector

class SocialMediaIntentDetector(BaseIntentDetector):
    """
    社交媒体文案意图检测器
    """
    
    def detect(self, text: str) -> bool:
        """
        检测文本中是否包含社交媒体文案生成意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            是否检测到社交媒体文案生成意图
        """
        social_media_patterns = [
            r'(?:帮我|help|请|please|)(?:写|生成|创建|制作|make|write|generate|create)\s*(?:.*?)(?:社交媒体|social media|朋友圈|微博|微信|ins|instagram|facebook)\s*(?:文案|内容|post|content|caption)',
            r'(?:发|post|分享|share)\s*(?:.*?)(?:社交媒体|social media|朋友圈|微博|微信|ins|instagram|facebook)\s*(?:文案|内容|post|content|caption)',
            r'(?:.*?)(?:旅行|旅游|trip|travel|游玩)\s*(?:照片|图片|photo|picture)\s*(?:配文|文案|caption|description)'
        ]
        
        for pattern in social_media_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def extract_params(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取社交媒体文案相关的参数
        
        Args:
            text: 用户输入文本
            
        Returns:
            包含platform、style和keywords的字典
        """
        params = {}
        
        # 提取平台
        platform_mapping = {
            "朋友圈": "微信",
            "wechat": "微信",
            "weixin": "微信",
            "微信": "微信",
            "微博": "微博",
            "weibo": "微博",
            "ins": "Instagram",
            "instagram": "Instagram",
            "facebook": "Facebook",
            "fb": "Facebook",
            "twitter": "Twitter",
            "推特": "Twitter",
            "小红书": "小红书",
            "red book": "小红书",
            "tiktok": "TikTok",
            "抖音": "抖音",
            "douyin": "抖音"
        }
        
        for platform, value in platform_mapping.items():
            if platform.lower() in text.lower():
                params["platform"] = value
                break
        
        if "platform" not in params:
            params["platform"] = "通用"  # 默认通用平台
        
        # 提取风格
        style_mapping = {
            "幽默": ["幽默", "搞笑", "有趣", "humor", "funny", "joke"],
            "文艺": ["文艺", "诗意", "artistic", "poetic", "literary"],
            "简洁": ["简洁", "简短", "concise", "brief", "short"],
            "专业": ["专业", "正式", "professional", "formal"],
            "感性": ["感性", "情感", "emotional", "touching", "moving"],
            "励志": ["励志", "激励", "motivational", "inspiring"],
            "商务": ["商务", "business", "professional"],
            "旅行": ["旅行", "旅游", "travel", "trip", "journey"]
        }
        
        for style, keywords in style_mapping.items():
            for keyword in keywords:
                if keyword in text.lower():
                    params["style"] = style
                    break
            if "style" in params:
                break
        
        if "style" not in params:
            params["style"] = "旅行"  # 默认旅行风格
        
        # 提取关键词
        keywords = []
        keyword_pattern = r'(?:关键词|keywords|标签|tags|话题|topics)[:：]\s*(.+?)(?:\.|。|$)'
        keyword_match = re.search(keyword_pattern, text, re.IGNORECASE)
        
        if keyword_match:
            keyword_text = keyword_match.group(1).strip()
            # 分割关键词（可能用逗号、空格等分隔）
            keywords = [k.strip() for k in re.split(r'[,，、\s]+', keyword_text) if k.strip()]
        
        if keywords:
            params["keywords"] = keywords
        
        # 提取地点（如果有）
        location_pattern = r'(?:在|at|in)\s*(.+?)\s*(?:拍的|拍摄的|taken|shot)'
        location_match = re.search(location_pattern, text, re.IGNORECASE)
        
        if location_match:
            params["location"] = location_match.group(1).strip()
        
        return params