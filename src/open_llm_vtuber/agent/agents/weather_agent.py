from typing import AsyncIterator
import json
import re
from datetime import datetime
from loguru import logger

from .agent_interface import AgentInterface
from ..input_types import BatchInput
from ..output_types import SentenceOutput
from ..stateless_llm.stateless_llm_interface import StatelessLLMInterface
from agents.tools.get_weather import get_current_temperature, get_temperature_date

class WeatherAgent(AgentInterface):
    def __init__(self, llm: StatelessLLMInterface, system_prompt: str):
        self.llm = llm
        self.system_prompt = system_prompt
        self.memory = [
            {"role": "system", "content": self.system_prompt}
        ]
        logger.info("WeatherAgent initialized with system prompt.")

    async def chat(self, input_data: BatchInput) -> AsyncIterator[SentenceOutput]:
        user_text = "\n".join([t.content for t in input_data.texts])
        self.memory.append({"role": "user", "content": user_text})

        messages = self.memory.copy()

        # First call: check if tool should be used
        first_response = await self.llm.chat_completion(messages=messages, tools=self.tools())
        response_message = first_response.get("message", {})
        tool_calls = response_message.get("tool_calls", [])

        if tool_calls:
            self.memory.append(response_message)
            for tool_call in tool_calls:
                function_name = tool_call['function']['name']
                function_args = tool_call['function']['arguments']

                tool_result = self.call_tool(function_name, function_args)
                self.memory.append({
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result),
                })

            # Second call: return final answer
            second_response = await self.llm.chat_completion(messages=self.memory)
            answer = second_response.get("message", {}).get("content", "")
        else:
            answer = response_message.get("content", "")

        self.memory.append({"role": "assistant", "content": answer})

        # Yield as SentenceOutput
        yield SentenceOutput(display_text=answer, sentence=answer)

    def handle_interrupt(self, heard_response: str) -> None:
        if self.memory and self.memory[-1]["role"] == "assistant":
            self.memory[-1]["content"] = heard_response + "..."
        self.memory.append({"role": "system", "content": "[interrupted by user]"})

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        # You can implement loading history if needed
        pass

    def call_tool(self, name: str, arguments: dict):
        if name == "get_current_temperature":
            return get_current_temperature(**arguments)
        elif name == "get_temperature_date":
            return get_temperature_date(**arguments)
        return {"error": f"Unknown tool: {name}"}

    def tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_current_temperature",
                    "description": "获取指定地点当前的实时天气信息，包括温度、天气状况、湿度、风向和风力。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "需要查询天气的城市名称，例如 '北京', '上海市'。",
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "温度单位，'celsius' (摄氏度) 或 'fahrenheit' (华氏度)。默认为 'celsius'。",
                            },
                        },
                        "required": ["location"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_temperature_date",
                    "description": "获取指定地点和日期的天气预报。可以查询特定日期 (YYYY-MM-DD)、'明天' 或 '未来X天'（例如 '未来3天'）的天气。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "需要查询天气预报的城市名称，例如 '上海', '杭州市'。",
                            },
                            "date": {
                                "type": "string",
                                "description": "需要查询的日期。可以是 'YYYY-MM-DD' 格式的具体日期，也可以是 '明天'，或 '未来X天' (例如 '未来2天', '未来两天')这样的描述。",
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "温度单位，'celsius' (摄氏度) 或 'fahrenheit' (华氏度)。默认为 'celsius'。",
                            },
                        },
                        "required": ["location", "date"],
                    },
                },
            },
        ]