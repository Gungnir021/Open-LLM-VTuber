from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from .tool_registry import ToolRegistry

class ToolCaller:
    """
    工具调用器，负责调用各种工具函数
    """
    
    def __init__(self, tool_registry: ToolRegistry, api_key: Optional[str] = None):
        """
        初始化工具调用器
        
        Args:
            tool_registry: 工具注册表
            api_key: 可选的API密钥
        """
        self.tool_registry = tool_registry
        self.tool_call_count = 0
        self.last_tool_call_time = None
        self.last_tool_name = None
        self.last_tool_args = None
        
        # 如果提供了API密钥，设置到天气和交通工具中
        if api_key:
            from ..tools.get_weather import AMAP_API_KEY
            from ..tools.get_traffic import AMAP_API_KEY as TRAFFIC_AMAP_API_KEY
            AMAP_API_KEY = api_key
            TRAFFIC_AMAP_API_KEY = api_key
    
    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用工具函数
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具调用结果
        """
        logger.debug(f"调用工具: {name} 参数: {arguments}")
        try:
            tool_func = self.tool_registry.get_tool_function(name)
            if tool_func:
                return tool_func(**arguments)
            return {"error": f"未知工具: {name}"}
        except Exception as e:
            logger.error(f"工具调用失败: {str(e)}")
            return {"error": f"工具调用失败: {str(e)}"}
    
    def increment_call_count(self) -> None:
        """
        增加工具调用计数
        """
        self.tool_call_count += 1
    
    def get_call_count(self) -> int:
        """
        获取工具调用计数
        
        Returns:
            工具调用计数
        """
        return self.tool_call_count
    
    def set_last_call_info(self, tool_name: str, tool_args: Dict[str, Any], call_time: str) -> None:
        """
        设置最后一次工具调用信息
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            call_time: 调用时间
        """
        self.last_tool_name = tool_name
        self.last_tool_args = tool_args
        self.last_tool_call_time = call_time