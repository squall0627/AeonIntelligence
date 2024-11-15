from typing import Dict, Hashable, List, Union, Any, Type
from enum import Enum

from rapidfuzz import process, fuzz

from langchain_core.tools import BaseTool
from langgraph.graph import START, END

from core.ai_core.base_config import AIBaseConfig
from core.ai_core.llm_tools.tools_factory import LLMToolFactory, TOOLS_CATEGORIES, TOOLS_LISTS


class SpecialEdges(str, Enum):
    start = "START"
    end = "END"

class ConditionalEdgeConfig(AIBaseConfig):
    routing_function: str
    conditions: Union[list, Dict[Hashable, str]]

    def __init__(self, **data):
        super().__init__(**data)
        self.resolve_special_edges()

    def resolve_special_edges(self):
        if isinstance(self.conditions, dict):
            for key, value in self.conditions.items():
                if value == SpecialEdges.end:
                    self.conditions[key] = END
                elif value == SpecialEdges.start:
                    self.conditions[key] = START
        elif isinstance(self.conditions, list):
            for index, value in enumerate(self.conditions):
                if value == SpecialEdges.end:
                    self.conditions[index] = END
                elif value == SpecialEdges.start:
                    self.conditions[index] = START

class NodeConfig(AIBaseConfig):
    name: str
    edges: List[str] | None = None
    conditional_edge: ConditionalEdgeConfig | None = None
    tools: List[Dict[str, Any]] | None = None
    instantiated_tools: List[BaseTool | Type] | None = None

    def __init__(self, **data):
        super().__init__(**data)
        self._instantiate_tools()
        self.resolve_special_edges_in_name_and_edges()

    def _instantiate_tools(self):
        if self.tools:
            self.instantiated_tools = [
                LLMToolFactory.create_tool(tool_config.pop("name"), tool_config)
                for tool_config in self.tools
            ]

    def resolve_special_edges_in_name_and_edges(self):
        if self.name == SpecialEdges.start:
            self.name = START
        elif self.name == SpecialEdges.end:
            self.name = END

        if self.edges:
            for i, edge in enumerate(self.edges):
                if edge == SpecialEdges.start:
                    self.edges[i] = START
                elif edge == SpecialEdges.end:
                    self.edges[i] = END

class DefaultWorkflow(str, Enum):
    RAG = "rag"

    @property
    def nodes(self) -> List[NodeConfig]:
        workflows = {
            self.RAG: [
                NodeConfig(name=START, edges=["filter_history"]),
                NodeConfig(name="filter_history", edges=["rewrite"]),
                NodeConfig(name="rewrite", edges=["retrieve"]),
                NodeConfig(name="retrieve", edges=["generate_rag"]),
                NodeConfig(name="generate_rag", edges=[END]),
            ]
        }
        return workflows[self]

class WorkflowConfig(AIBaseConfig):
    name: str | None = None
    nodes: List[NodeConfig] = []
    available_tools: List[str] | None = None
    validated_tools: List[BaseTool | Type] = []
    activated_tools: List[BaseTool | Type] = []

    def __init__(self, **data):
        super().__init__(**data)
        self.check_first_node_is_start()
        self.validate_available_tools()

    def check_first_node_is_start(self):
        if self.nodes and self.nodes[0].name != START:
            raise ValueError(f"The first node should be a {SpecialEdges.start} node")

    def validate_available_tools(self):
        if self.available_tools:
            valid_tools = list(TOOLS_CATEGORIES.keys()) + list(TOOLS_LISTS.keys())
            for tool in self.available_tools:
                if tool.lower() in valid_tools:
                    self.validated_tools.append(
                        LLMToolFactory.create_tool(tool, {}).tool
                    )
                else:
                    matches = process.extractOne(
                        tool.lower(), valid_tools, scorer=fuzz.WRatio
                    )
                    if matches:
                        raise ValueError(
                            f"Tool {tool} is not a valid ToolsCategory or ToolsList. Did you mean {matches[0]}?"
                        )
                    else:
                        raise ValueError(
                            f"Tool {tool} is not a valid ToolsCategory or ToolsList"
                        )

    def get_node_tools(self, node_name: str) -> List[Any]:
        for node in self.nodes:
            if node.name == node_name and node.instantiated_tools:
                return node.instantiated_tools
        return []