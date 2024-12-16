import asyncio

from langchain.retrievers import ContextualCompressionRetriever
from langchain_core.vectorstores import VectorStore

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.ai_rag_reranker import AIRagReranker
from core.ai_core.rag.ai_rag_retriever import AIRagRetriever
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.node_functions.node_function_base import (
    NodeFunctionBase,
    AgentState,
)


class Retrieve(NodeFunctionBase):
    name = "retrieve"
    is_async = True

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
        raise NotImplementedError

    async def arun(self, state: AgentState) -> AgentState:
        """
        Retrieve relevant chunks

        Args:
            state (messages): The current state

        Returns:
            dict: The retrieved chunks
        """

        tasks = state["tasks"]
        if not tasks:
            return {**state, "docs": []}

        kwargs = {
            "search_kwargs": {
                "k": self.retrieval_config.k,
            }
        }
        base_retriever = AIRagRetriever(self.vector_store).get_retriever(**kwargs)

        kwargs = {"top_n": self.retrieval_config.reranker_config.top_n}
        reranker = AIRagReranker(self.retrieval_config).get_reranker(**kwargs)

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=reranker, base_retriever=base_retriever
        )

        # Prepare the async tasks for all questions
        async_tasks = []
        for task in tasks:
            # Asynchronously invoke the model for each question
            async_tasks.append(compression_retriever.ainvoke(task))

        # Gather all the responses asynchronously
        responses = await asyncio.gather(*async_tasks) if async_tasks else []

        docs = []
        for response in responses:
            _docs = self.filter_chunks_by_relevance(response)
            docs += _docs

        return {**state, "docs": docs}
