from typing import List, Optional

from langchain_core.vectorstores import VectorStore
from langgraph.types import Send
from pydantic import BaseModel, Field

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.node_functions.node_function_base import NodeFunctionBase, AgentState
from core.ai_core.rag.prompts import custom_prompts


class SplitInput(BaseModel):
    """Given a chat history and the user input, split and rephrase the input into instructions and tasks."""

    instructions_reasoning: List[str] | dict | str | None = Field(
        ...,
        description="The reasoning that leads to identifying the user instructions to the system",
    )
    instructions: List[str] | dict | str | None = Field(
        ..., description="The instructions to the system"
    )

    tasks_reasoning: List[str] | dict | str | None = Field(
        ...,
        description="The reasoning that leads to identifying the explicit or implicit user tasks and questions",
    )
    tasks: List[str] | str | None = Field(
        ...,
        default_factory=lambda: ["No explicit or implicit tasks found"],
        description="The list of standalone, self-contained tasks or questions.",
    )

class RoutingSplit(NodeFunctionBase):
    name="routing_split"
    is_async=False

    def __init__(self,
                 retrieval_config: RetrievalConfig,
                 llm: LLMEndpoint,
                 vector_store: VectorStore | None = None,):
        super().__init__(retrieval_config=retrieval_config, llm=llm, vector_store=vector_store)

    def run(self, state: AgentState) -> List[Send]:
        response = self.invoke_structured_output(
            custom_prompts.SPLIT_PROMPT.format(
                chat_history=state["chat_history"].to_list(),
                user_input=state["messages"][0].content,
            ),
            SplitInput,
        )

        print(f"############## The result of SplitInput is: {response}")

        instructions = None
        tasks = None
        if response:
            instructions = response.instructions or self.retrieval_config.prompt
            tasks = response.tasks or []

        print(f"############## The instructions are: {instructions}")
        if instructions:
            print(f"############## Will run edit_system_prompt with instructions: {instructions} and tasks: {tasks}")
            return [
                Send(
                    "edit_system_prompt",
                    {**state, "instructions": instructions, "tasks": tasks},
                )
            ]
        elif tasks:
            print(f"############## Will run filter_history with tasks: {tasks}")
            return [Send("filter_history", {**state, "tasks": tasks})]
        else:
            print(f"############## Will run filter_history with tasks: {tasks}")
            tasks = (
                state["tasks"]
                if "tasks" in state and state["tasks"]
                else [state["messages"][0].content]
            )
            return [Send("filter_history", {**state, "tasks": tasks})]

        # return []

    async def arun(self, state: AgentState) -> List[Send]:
        raise NotImplementedError