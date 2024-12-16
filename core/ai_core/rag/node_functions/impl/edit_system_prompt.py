from typing import List, Optional

from langchain_core.vectorstores import VectorStore
from pydantic import BaseModel, Field

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.node_functions.node_function_base import (
    NodeFunctionBase,
    AgentState,
)
from core.ai_core.rag.prompts import custom_prompts


class UpdatedPromptAndTools(BaseModel):
    """Update the prompt to include the instruction and decide which tools to activate."""

    prompt_reasoning: str | None = Field(
        ...,
        description="The step-by-step reasoning that leads to the updated system prompt",
    )
    prompt: str | None = Field(..., description="The updated system prompt")

    tools_reasoning: str | None = Field(
        ...,
        description="The reasoning that leads to activating and deactivating the tools",
    )
    tools_to_activate: List[str] | None = Field(
        ..., default_factory=list, description="The list of tools to activate"
    )
    tools_to_deactivate: List[str] | None = Field(
        ..., default_factory=list, description="The list of tools to deactivate"
    )


class EditSystemPrompt(NodeFunctionBase):
    name = "edit_system_prompt"
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

    def run(self, state: AgentState) -> AgentState:
        user_instruction = state["instructions"]
        prompt = self.retrieval_config.prompt
        available_tools, activated_tools = (
            self.retrieval_config.workflow_config.collect_tools_prompt()
        )

        inputs = {
            "instruction": user_instruction,
            "system_prompt": prompt if prompt else "",
            "available_tools": available_tools,
            "activated_tools": activated_tools,
        }

        msg = custom_prompts.UPDATE_PROMPT.format(**inputs)

        response: UpdatedPromptAndTools = self.invoke_structured_output(
            msg, UpdatedPromptAndTools
        )

        print(f"############## The result of UpdatedPromptAndTools is: {response}")
        reasoning = []
        if response:
            print(f"############## Will update active tools with response: {response}")
            self._update_active_tools(response)
            self.retrieval_config.prompt = response.prompt

            reasoning = [response.prompt_reasoning] if response.prompt_reasoning else []
            reasoning += [response.tools_reasoning] if response.tools_reasoning else []

        return {**state, "messages": [], "reasoning": reasoning}

    async def arun(self, state: AgentState) -> AgentState:
        raise NotImplementedError

    def _update_active_tools(self, updated_prompt_and_tools: UpdatedPromptAndTools):
        if updated_prompt_and_tools.tools_to_activate:
            for tool in updated_prompt_and_tools.tools_to_activate:
                for (
                    validated_tool
                ) in self.retrieval_config.workflow_config.validated_tools:
                    if tool == validated_tool.name:
                        self.retrieval_config.workflow_config.activated_tools.append(
                            validated_tool
                        )

        if updated_prompt_and_tools.tools_to_deactivate:
            for tool in updated_prompt_and_tools.tools_to_deactivate:
                for (
                    activated_tool
                ) in self.retrieval_config.workflow_config.activated_tools:
                    if tool == activated_tool.name:
                        self.retrieval_config.workflow_config.activated_tools.remove(
                            activated_tool
                        )
