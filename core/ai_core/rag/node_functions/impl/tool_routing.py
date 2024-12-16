from typing import List, Any, Optional

from langchain_core.vectorstores import VectorStore
from langgraph.types import Send
from pydantic import BaseModel, Field

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.node_functions.node_function_base import (
    NodeFunctionBase,
    AgentState,
)
from core.ai_core.rag.prompts import custom_prompts


class TasksCompletion(BaseModel):
    """Determine whether all tasks can be completed fully and in the best possible way using the provided context and chat history."""

    completable_tasks_reasoning: List[str] | str | None = Field(
        ...,
        description="The reasoning that leads to identifying the user tasks or questions that can be completed using the provided context and chat history.",
    )
    completable_tasks: List[str] | None = Field(
        ...,
        default_factory=list,
        description="The user tasks or questions that can be completed using the provided context and chat history.",
    )

    non_completable_tasks_reasoning: List[str] | str | None = Field(
        ...,
        description="The reasoning that leads to identifying the user tasks or questions that cannot be completed using the provided context and chat history.",
    )
    non_completable_tasks: List[str] | None = Field(
        ...,
        default_factory=list,
        description="The user tasks or questions that need a tool to be completed.",
    )

    tool_reasoning: List[str] | str | None = Field(
        ...,
        description="The reasoning that leads to identifying the tool that shall be used to complete the tasks.",
    )
    tool: str = Field(
        ...,
        default_factory=list,
        description="The tool that shall be used to complete the tasks.",
    )


class ToolRouting(NodeFunctionBase):
    name = "tool_routing"
    is_async = False

    def __init__(
        self,
        retrieval_config: RetrievalConfig,
        llm: LLMEndpoint,
        vector_store: VectorStore | None = None,
    ):
        super().__init__(
            retrieval_config=retrieval_config, llm=llm, vector_store=vector_store
        )

    def run(self, state: AgentState) -> Any:
        tasks = state["tasks"]
        if not tasks:
            return [Send("generate_rag", state)]

        docs = state["docs"]

        _, activated_tools = (
            self.retrieval_config.workflow_config.collect_tools_prompt()
        )

        p_input = {
            "chat_history": state["chat_history"].to_list(),
            "tasks": state["tasks"],
            "context": docs,
            "activated_tools": activated_tools,
        }

        p_input, _ = self.reduce_rag_context(
            inputs=p_input,
            prompt=custom_prompts.TOOL_ROUTING_PROMPT,
            docs=docs,
        )

        msg = custom_prompts.TOOL_ROUTING_PROMPT.format(**p_input)

        response: TasksCompletion = self.invoke_structured_output(msg, TasksCompletion)

        print(f"############## The result of TasksCompletion is: {response}")

        send_list: List[Send] = []

        if response and response.non_completable_tasks and response.tool:
            print(
                f"############## Will run run_tool with tasks: {response.non_completable_tasks} and tool: {response.tool}"
            )
            payload = {
                **state,
                "tasks": response.non_completable_tasks,
                "tool": response.tool,
            }
            send_list.append(Send("run_tool", payload))
        else:
            print(f"############## Will run generate_rag with state: {state}")
            send_list.append(Send("generate_rag", state))

        return send_list

    async def arun(self, state: AgentState) -> Any:
        raise NotImplementedError
