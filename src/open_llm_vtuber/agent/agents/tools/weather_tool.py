from typing import Dict, Any
from .tool_base import ToolBase
from .get_weather import get_weather

class WeatherTool(ToolBase):
    """天气查询工具"""
    
    @property
    def name(self) -> str:
        return "get_weather"
    
    @property
    def description(self) -> str:
        return "获取指定城市的当前天气信息"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市名称，如：北京、上海、广州等"
                }
            },
            "required": ["location"]
        }
    
    def execute(self, location: str) -> str:
        """执行天气查询"""
        return get_weather(location)