from typing import List, Any

from langchain_core.vectorstores import VectorStore
from langgraph.types import Send

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.entities.node_result import TasksCompletion
from core.ai_core.rag.node_functions.base_node_function import BaseNodeFunction, AgentState
from core.ai_core.rag.prompts import custom_prompts


class ToolRouting(BaseNodeFunction):
    name="tool_routing"
    is_async=False

    def __init__(self,
                 retrieval_config: RetrievalConfig,
                 llm: LLMEndpoint,
                 vector_store: VectorStore | None = None,):
        super().__init__(retrieval_config=retrieval_config, llm=llm, vector_store=vector_store)

    def run(self, state: AgentState) -> Any:
        tasks = state["tasks"]
        if not tasks:
            return [Send("generate_rag", state)]

        docs = state["docs"]

        _, activated_tools = self.retrieval_config.workflow_config.collect_tools_prompt()

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

        send_list: List[Send] = []

        if response.non_completable_tasks and response.tool:
            payload = {
                **state,
                "tasks": response.non_completable_tasks,
                "tool": response.tool,
            }
            send_list.append(Send("run_tool", payload))
        else:
            send_list.append(Send("generate_rag", state))

        return send_list

    async def arun(self, state: AgentState) -> Any:
        raise NotImplementedError