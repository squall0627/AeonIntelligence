from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.node_functions.node_function_base import NodeFunctionBase, AgentState
from core.ai_core.rag.prompts import custom_prompts


class GenerateRag(NodeFunctionBase):
    name="generate_rag"
    is_async=False

    def __init__(self,
                 retrieval_config: RetrievalConfig,
                 llm: LLMEndpoint,
                 vector_store: VectorStore | None = None,):
        super().__init__(retrieval_config=retrieval_config, llm=llm, vector_store=vector_store)

    def run(self, state: AgentState) -> AgentState:
        docs: List[Document] | None = state["docs"]
        final_inputs = self.build_rag_prompt_inputs(state, docs)

        reduced_inputs, docs = self.reduce_rag_context(
            final_inputs, custom_prompts.RAG_ANSWER_PROMPT, docs
        )

        msg = custom_prompts.RAG_ANSWER_PROMPT.format(**reduced_inputs)
        llm = self.bind_tools_to_llm(self.name)
        response = llm.invoke(msg)

        return {**state, "messages": [response], "docs": docs if docs else []}

    async def arun(self, state: AgentState) -> AgentState:
        raise NotImplementedError