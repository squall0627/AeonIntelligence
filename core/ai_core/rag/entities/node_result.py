from typing import Optional, List

from pydantic import BaseModel, Field


class TasksCompletion(BaseModel):
    completable_tasks_reasoning: Optional[str] = Field(
        default=None,
        description="The reasoning that leads to identifying the user tasks or questions that can be completed using the provided context and chat history.",
    )
    completable_tasks: Optional[List[str]] = Field(
        default_factory=list,
        description="The user tasks or questions that can be completed using the provided context and chat history.",
    )

    non_completable_tasks_reasoning: Optional[str] = Field(
        default=None,
        description="The reasoning that leads to identifying the user tasks or questions that cannot be completed using the provided context and chat history.",
    )
    non_completable_tasks: Optional[List[str]] = Field(
        default_factory=list,
        description="The user tasks or questions that need a tool to be completed.",
    )

    tool_reasoning: Optional[str] = Field(
        default=None,
        description="The reasoning that leads to identifying the tool that shall be used to complete the tasks.",
    )
    tool: Optional[str] = Field(
        default_factory=list,
        description="The tool that shall be used to complete the tasks.",
    )