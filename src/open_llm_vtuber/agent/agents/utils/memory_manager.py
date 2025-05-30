from typing import List, Dict, Any
import json

class MemoryManager:
    """
    内存管理器，负责管理对话历史和工具调用结果
    """
    
    def __init__(self, system_prompt: str):
        """
        初始化内存管理器
        
        Args:
            system_prompt: 系统提示词
        """
        self.memory = [
            {"role": "system", "content": system_prompt}
        ]
    
    def add_user_message(self, message: str) -> None:
        """
        添加用户消息
        
        Args:
            message: 用户消息内容
        """
        self.memory.append({"role": "user", "content": message})
    
    def add_assistant_message(self, message: str) -> None:
        """
        添加助手消息
        
        Args:
            message: 助手消息内容
        """
        self.memory.append({"role": "assistant", "content": message})
    
    def add_tool_result(self, tool_name: str, result: Dict[str, Any]) -> None:
        """
        添加工具调用结果
        
        Args:
            tool_name: 工具名称
            result: 工具调用结果
        """
        self.memory.append({
            "role": "tool",
            "name": tool_name,
            "content": json.dumps(result, ensure_ascii=False),
        })
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """
        获取所有消息
        
        Returns:
            消息列表
        """
        return self.memory.copy()
    
    def handle_interrupt(self, heard_response: str) -> None:
        """
        处理用户中断
        
        Args:
            heard_response: 用户听到的响应部分
        """
        if self.memory and self.memory[-1]["role"] == "assistant":
            self.memory[-1]["content"] = heard_response + "..."
        self.memory.append({"role": "system", "content": "[用户打断了对话]"})