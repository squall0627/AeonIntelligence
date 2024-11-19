import asyncio

from langchain_core.vectorstores import VectorStore

from core.ai_core.llm import LLMEndpoint
from core.ai_core.llm_tools.tools_factory import LLMToolFactory
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.node_functions.node_function_base import NodeFunctionBase, AgentState


class RunTool(NodeFunctionBase):
    name="run_tool"
    is_async=True

    def __init__(self,
                 retrieval_config: RetrievalConfig,
                 llm: LLMEndpoint,
                 vector_store: VectorStore | None = None,):
        super().__init__(retrieval_config=retrieval_config, llm=llm, vector_store=vector_store)

    def run(self, state: AgentState) -> AgentState:
        raise NotImplementedError

    async def arun(self, state: AgentState) -> AgentState:
        tool = state["tool"]
        if tool not in [
            t.name for t in self.retrieval_config.workflow_config.activated_tools
        ]:
            raise ValueError(f"Tool {tool} not activated")

        tasks = state["tasks"]

        tool_wrapper = LLMToolFactory.create_tool(tool, {})

        # Prepare the async tasks for all questions
        async_tasks = []
        for task in tasks:
            print(f"##########Tool {tool_wrapper.tool.name} Run##########")
            formatted_input = tool_wrapper.format_input(task)
            # Asynchronously invoke the model for each question
            async_tasks.append(tool_wrapper.tool.ainvoke(formatted_input))

        # Gather all the responses asynchronously
        responses = await asyncio.gather(*async_tasks) if async_tasks else []

        docs = []
        for response in responses:
            _docs = tool_wrapper.format_output(response)
            _docs = self.filter_chunks_by_relevance(_docs)
            docs += _docs

        return {**state, "docs": state["docs"] + docs}