from abc import ABC, abstractmethod
from typing import Dict, Any, List
import json

class ToolBase(ABC):
    """工具基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """工具参数定义"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具"""
        pass
    
    def to_function_definition(self) -> Dict[str, Any]:
        """转换为 DeepSeek Function Calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        self._tools: Dict[str, ToolBase] = {}
    
    def register_tool(self, tool: ToolBase):
        """注册工具"""
        self._tools[tool.name] = tool
        print(f"🔧 [DEBUG] 注册工具: {tool.name}")
    
    def get_tool(self, name: str) -> ToolBase:
        """获取工具"""
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[ToolBase]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """获取所有工具的函数定义"""
        return [tool.to_function_definition() for tool in self._tools.values()]
    
    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """执行工具"""
        tool = self.get_tool(name)
        if not tool:
            return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
        
        try:
            print(f"🔧 [DEBUG] 执行工具: {name}，参数: {arguments}")
            result = tool.execute(**arguments)
            print(f"🔧 [DEBUG] 工具执行结果: {result[:100]}...")
            return result
        except Exception as e:
            error_msg = f"工具执行失败: {str(e)}"
            print(f"❌ [DEBUG] {error_msg}")
            return json.dumps({"error": error_msg}, ensure_ascii=False)