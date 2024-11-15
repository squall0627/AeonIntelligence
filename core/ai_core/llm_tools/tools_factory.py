from typing import Dict, Any, Type, Union

from core.ai_core.llm_tools.entity import ToolWrapper

TOOLS_CATEGORIES = {
    """TODO"""""
}

TOOLS_LISTS = {
    """TODO"""""
}

class LLMToolFactory:
    @staticmethod
    def create_tool(tool_name: str, config: Dict[str, Any]) -> Union[ToolWrapper, Type]:
        for category, tools_class in TOOLS_CATEGORIES.items():
            if tool_name in tools_class.tools:
                return tools_class.create_tool(tool_name, config)
            elif tool_name.lower() == category and tools_class.default_tool:
                return tools_class.create_tool(tools_class.default_tool, config)
        raise ValueError(f"Tool {tool_name} is not supported.")