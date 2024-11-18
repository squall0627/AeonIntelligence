from enum import Enum
from typing import Dict, Any, Union, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.ai_core.llm_tools.entity import ToolsCategory


class SimpleCitedAnswer(BaseModel):
    """Answer the user question based only on the given sources, and cite the sources used."""

    answer: str = Field(
        ...,
        description="The answer to the user question, which is based only on the given sources.",
    )
    citations: list[int] = Field(
        ...,
        description="The integer IDs of the SPECIFIC sources which justify the answer.",
    )

    followup_questions: list[str] = Field(
        ...,
        description="You must generate up to 3 follow-up questions that could be asked based on the answer given or context provided.",
    )

class CitedAnswerToolsList(str, Enum):
    SIMPLE_CITED_ANSWER = "cited_answer"

def create_other_tool(tool_name: str, config: Dict[str, Any]) -> Union[BaseTool, Type]:
    if tool_name == CitedAnswerToolsList.SIMPLE_CITED_ANSWER:
        return SimpleCitedAnswer
    else:
        raise ValueError(f"Tool {tool_name} is not supported.")

CitedAnswerTools = ToolsCategory(
    name="cited_answer",
    description="Cited answer tools",
    tools=[CitedAnswerToolsList.SIMPLE_CITED_ANSWER],
    create_tool=create_other_tool,
)