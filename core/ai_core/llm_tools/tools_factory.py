from typing import Dict, Any, Type, Union

from core.ai_core.llm_tools.cited_answer_tool import CitedAnswerTools
from core.ai_core.llm_tools.tool_helper import ToolWrapper
from core.ai_core.llm_tools.web_search_tools import WebSearchTools

TOOLS_CATEGORIES = {
    CitedAnswerTools.name: CitedAnswerTools,
    WebSearchTools.name: WebSearchTools,
}

TOOLS_LISTS = {
    **{tool.value: tool for tool in CitedAnswerTools.tools},
    **{tool.value: tool for tool in WebSearchTools.tools},
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
