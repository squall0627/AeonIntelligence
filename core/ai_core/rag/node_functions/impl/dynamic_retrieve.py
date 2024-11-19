import logging
import asyncio

from typing import List

from langchain.retrievers import ContextualCompressionRetriever
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.ai_rag_reranker import AIRagReranker
from core.ai_core.rag.ai_rag_retriever import AIRagRetriever
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.node_functions.node_function_base import NodeFunctionBase, AgentState
from core.ai_core.rag.prompts import custom_prompts

logger = logging.getLogger("ai_core")

class DynamicRetrieve(NodeFunctionBase):
    name="dynamic_retrieve"
    is_async=True

    def __init__(self,
                 retrieval_config: RetrievalConfig,
                 llm: LLMEndpoint,
                 vector_store: VectorStore | None = None,):
        super().__init__(retrieval_config=retrieval_config, llm=llm, vector_store=vector_store)

    def run(self, state: AgentState) -> AgentState:
        raise NotImplementedError

    async def arun(self, state: AgentState) -> AgentState:
        """
        Retrieve relevant chunks
        Number of chunks is increased until the context length is more than the max context tokens or more than the re-ranker's top_n

        Args:
            state (messages): The current state

        Returns:
            dict: The retrieved chunks
        """

        tasks = state["tasks"]
        if not tasks:
            return {**state, "docs": []}

        k = self.retrieval_config.k
        top_n = self.retrieval_config.reranker_config.top_n
        number_of_relevant_chunks = top_n
        i = 1

        while number_of_relevant_chunks == top_n:
            top_n = self.retrieval_config.reranker_config.top_n * i
            kwargs = {"top_n": top_n}
            reranker = AIRagReranker(self.retrieval_config).get_reranker(**kwargs)

            k = max([top_n * 2, self.retrieval_config.k])
            kwargs = {"search_kwargs": {"k": k}}
            base_retriever = AIRagRetriever(self.vector_store).get_retriever(**kwargs)

            if i > 1:
                logging.info(
                    f"Increasing top_n to {top_n} and k to {k} to retrieve more relevant chunks"
                )

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
            _n = []
            for response in responses:
                _docs = self.filter_chunks_by_relevance(response)
                _n.append(len(_docs))
                docs += _docs

            if not docs:
                break

            context_length = self.get_rag_context_length(state, docs)
            if context_length >= self.retrieval_config.llm_config.max_context_tokens:
                logging.warning(
                    f"The context length is {context_length} which is greater than "
                    f"the max context tokens of {self.retrieval_config.llm_config.max_context_tokens}"
                )
                break

            number_of_relevant_chunks = max(_n)
            i += 1

        return {**state, "docs": docs}

    def get_rag_context_length(self, state: AgentState, docs: List[Document]) -> int:
        final_inputs = self.build_rag_prompt_inputs(state, docs)
        msg = custom_prompts.RAG_ANSWER_PROMPT.format(**final_inputs)
        return self.llm_endpoint.count_tokens(msg)