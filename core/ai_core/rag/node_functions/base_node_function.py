import logging

from abc import ABC, abstractmethod
from typing import Any, Type, Dict, List, Tuple, TypedDict, Annotated, Sequence

import openai
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.prompts import BasePromptTemplate, format_document
from langchain_core.vectorstores import VectorStore
from langgraph.graph import add_messages
from pydantic import BaseModel

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.entities.chat import ChatHistory
from core.ai_core.rag.prompts import custom_prompts

logger = logging.getLogger("ai_core")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    reasoning: List[str]
    chat_history: ChatHistory
    docs: list[Document]
    files: str
    tasks: List[str]
    instructions: str
    tool: str

class BaseNodeFunction(ABC):

    def __init__(
            self,
            *,
            retrieval_config: RetrievalConfig,
            llm: LLMEndpoint,
            vector_store: VectorStore | None = None,
    ):
        self.retrieval_config = retrieval_config
        self.vector_store = vector_store
        self.llm_endpoint = llm

    @abstractmethod
    def run(self, state: AgentState) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def arun(self, state: AgentState) -> Any:
        raise NotImplementedError

    def reduce_rag_context(
            self,
            inputs: Dict[str, Any],
            prompt: BasePromptTemplate,
            docs: List[Document] | None = None,
            max_context_tokens: int | None = None,
    ) -> Tuple[Dict[str, Any], List[Document] | None]:
        max_iteration = 100
        security_factor = 0.85
        iteration = 0

        msg = prompt.format(**inputs)
        n = self.llm_endpoint.count_tokens(msg)

        max_context_tokens = (
            max_context_tokens
            if max_context_tokens
            else self.retrieval_config.llm_config.max_context_tokens
        )

        while n > max_context_tokens * security_factor:
            chat_history = inputs["chat_history"] if "chat_history" in inputs else []

            if len(chat_history) > 0:
                inputs["chat_history"] = chat_history[2:]
            elif docs and len(docs) > 1:
                docs = docs[:-1]
            else:
                logging.warning(
                    f"Not enough context to reduce. The context length is {n} "
                    f"which is greater than the max context tokens of {max_context_tokens}"
                )
                break

            if docs and "context" in inputs:
                inputs["context"] = self.combine_documents(docs)

            msg = prompt.format(**inputs)
            n = self.llm_endpoint.count_tokens(msg)

            iteration += 1
            if iteration > max_iteration:
                logging.warning(
                    f"Attained the maximum number of iterations ({max_iteration})"
                )
                break

        return inputs, docs

    def invoke_structured_output(
            self, prompt: str, output_class: Type[BaseModel]
    ) -> Any:
        try:
            structured_llm = self.llm_endpoint.llm.with_structured_output(
                output_class, method="json_schema"
            )
            return structured_llm.invoke(prompt)
        except openai.BadRequestError:
            structured_llm = self.llm_endpoint.llm.with_structured_output(output_class)
            return structured_llm.invoke(prompt)

    @classmethod
    def combine_documents(
            cls,
            docs,
            document_prompt=custom_prompts.DEFAULT_DOCUMENT_PROMPT,
            document_separator="\n\n",
    ):
        # 各ドキュメントに対して、ソースを引用できるようにメタデータにインデックスを追加します。
        for doc, index in zip(docs, range(len(docs)), strict=False):
            doc.metadata["index"] = index
        doc_strings = [format_document(doc, document_prompt) for doc in docs]
        return document_separator.join(doc_strings)

    def filter_chunks_by_relevance(self, chunks: List[Document], **kwargs):
        config = self.retrieval_config.reranker_config
        relevance_score_threshold = kwargs.get(
            "relevance_score_threshold", config.relevance_score_threshold
        )

        if relevance_score_threshold is None:
            return chunks

        filtered_chunks = []
        for chunk in chunks:
            if config.relevance_score_key not in chunk.metadata:
                logger.warning(
                    f"Relevance score key {config.relevance_score_key} not found in metadata, cannot filter chunks by relevance"
                )
                filtered_chunks.append(chunk)
            elif (
                    chunk.metadata[config.relevance_score_key] >= relevance_score_threshold
            ):
                filtered_chunks.append(chunk)

        return filtered_chunks

    def bind_tools_to_llm(self, node_name: str):
        if self.llm_endpoint.supports_func_calling():
            tools = self.retrieval_config.workflow_config.get_node_tools(node_name)
            if tools:
                return self.llm_endpoint.llm.bind_tools(tools, tool_choice="any")
        return self.llm_endpoint.llm