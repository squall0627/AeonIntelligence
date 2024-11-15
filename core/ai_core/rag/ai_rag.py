import logging
from operator import itemgetter
from typing import Sequence, Optional, AsyncGenerator

from langchain.retrievers import ContextualCompressionRetriever
from langchain_core.callbacks import Callbacks
from langchain_core.documents import BaseDocumentCompressor, Document
from langchain_core.messages import AIMessage, HumanMessage, AIMessageChunk
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.vectorstores import VectorStore

from core.ai_core.llm.llm_endpoint import LLMEndpoint
from core.ai_core.rag.ai_rag_config import RetrievalConfig
from core.ai_core.rag.ai_rag_utils import combine_documents, format_file_list, parse_response, parse_chunk_response, \
    get_chunk_metadata
from core.ai_core.rag.entities.chat import ChatHistory, CitedAnswer
from core.ai_core.rag.entities.models import AiKnowledge, ParsedRAGResponse, ParsedRAGChunkResponse, RAGResponseMetadata
from core.ai_core.rag.prompts import custom_prompts

logger = logging.getLogger("ai_core")

class DefaultCompressor(BaseDocumentCompressor):
    def compress_documents(
            self,
            documents: Sequence[Document],
            query: str,
            callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        return documents

class AiQARAG:
    def __init__(
            self,
            *,
            retrieval_config: RetrievalConfig,
            llm: LLMEndpoint,
            vector_store: VectorStore,
            reranker: BaseDocumentCompressor | None = None,
    ):
        self.retrieval_config = retrieval_config
        self.llm_endpoint = llm
        self.vector_store = vector_store
        self.reranker = reranker if reranker is not None else DefaultCompressor()

    @property
    def retriever(self):
        """
        vector store からドキュメントを取得する関数です。
        """
        return self.vector_store.as_retriever()

    def filter_history(
            self,
            chat_history: ChatHistory,
    ):
        """
        チャット履歴をフィルタリングして、現在の質問に関連するメッセージのみを含めます。

        入力:
        - chat_history (ChatHistory): フィルタリングするチャット履歴。

        戻り値:
        - 優先順位に従ってフィルタリングされた chat_history。まず max_tokens、次に max_history でフィルタリングされ、Human メッセージと AI メッセージが 1 ペアとしてカウントされます。
        - 1 トークンは 4 文字とします。
        """
        total_tokens = 0
        total_pairs = 0
        filtered_chat_history: list[AIMessage | HumanMessage] = []
        for human_message, ai_message in chat_history.iter_pairs():
            message_tokens = (len(human_message.content) + len(ai_message.content)) // 4
            if (
                    total_tokens + message_tokens
                    > self.retrieval_config.llm_config.max_output_tokens
                    or total_pairs >= self.retrieval_config.max_history
            ):
                break
            filtered_chat_history.append(human_message)
            filtered_chat_history.append(ai_message)
            total_tokens += message_tokens
            total_pairs += 1

        return filtered_chat_history[::-1]

    def build_chain(self, files: str):
        """
        Aeon Intelligence QA RAG のチェーンを構築します。
        """
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.reranker, base_retriever=self.retriever
        )

        loaded_memory = RunnablePassthrough.assign(
            chat_history=RunnableLambda(
                lambda x: self.filter_history(x["chat_history"]),
            ),
            question=lambda x: x["question"],
        )

        standalone_question = {
            "standalone_question": {
                                       "question": itemgetter("question"),
                                       "chat_history": itemgetter("chat_history"),
                                   }
                                   | custom_prompts.CONDENSE_QUESTION_PROMPT
                                   | self.llm_endpoint.llm
                                   | StrOutputParser(),
        }

        # retrieve the documents
        retrieved_documents = {
            "docs": itemgetter("standalone_question") | compression_retriever,
            "question": itemgetter("standalone_question"),
            "custom_instructions": lambda x: self.retrieval_config.prompt,
        }

        final_inputs = {
            "context": lambda x: combine_documents(x["docs"]),
            "question": itemgetter("question"),
            "custom_instructions": itemgetter("custom_instructions"),
            "files": lambda _: files,
        }

        llm = self.llm_endpoint.llm
        if self.llm_endpoint.supports_func_calling():
            llm = self.llm_endpoint.llm.bind_tools(
                [CitedAnswer],
                tool_choice="any",
            )

        answer = {
            "answer": final_inputs | custom_prompts.RAG_ANSWER_PROMPT | llm,
            "docs": itemgetter("docs"),
        }

        return loaded_memory | standalone_question | retrieved_documents | answer

    def answer(
            self,
            question: str,
            history: ChatHistory,
            list_files: list[AiKnowledge],
            metadata: dict[str, str] = None,
    ) -> ParsedRAGResponse:
        """
        Aeon Intelligence QA RAG を使用して質問を同期的に回答します。
        """
        if metadata is None:
            metadata = {}
        concat_list_files = format_file_list(
            list_files, self.retrieval_config.max_files
        )
        conversational_qa_chain = self.build_chain(concat_list_files)
        raw_llm_response = conversational_qa_chain.invoke(
            {
                "question": question,
                "chat_history": history,
                "custom_instructions": self.retrieval_config.prompt,
            },
            config={"metadata": metadata},
        )
        response = parse_response(
            raw_llm_response, self.retrieval_config.llm_config
        )
        return response

    async def answer_astream(
            self,
            question: str,
            history: ChatHistory,
            list_files: list[AiKnowledge],
            metadata: dict[str, str] = None,
    ) -> AsyncGenerator[ParsedRAGChunkResponse, ParsedRAGChunkResponse]:
        """
        Aeon Intelligence QA RAG を使用して非同期的に質問に回答します。
        """
        if metadata is None:
            metadata = {}
        concat_list_files = format_file_list(
            list_files, self.retrieval_config.max_files
        )
        conversational_qa_chain = self.build_chain(concat_list_files)

        rolling_message = AIMessageChunk(content="")
        sources = []
        prev_answer = ""
        chunk_id = 0

        async for chunk in conversational_qa_chain.astream(
                {
                    "question": question,
                    "chat_history": history,
                    "custom_personality": self.retrieval_config.prompt,
                },
                config={"metadata": metadata},
        ):
            if "docs" in chunk:
                sources = chunk["docs"] if "docs" in chunk else []

            if "answer" in chunk:
                # TODO Check if it is OK
                rolling_message, diff_answer, answer_str = parse_chunk_response(
                    rolling_message,
                    chunk,
                    self.llm_endpoint.supports_func_calling(),
                    prev_answer,
                )

                if len(answer_str) > 0:
                    if self.llm_endpoint.supports_func_calling():
                        # diff_answer = answer_str[len(prev_answer) :]
                        if len(diff_answer) > 0:
                            parsed_chunk = ParsedRAGChunkResponse(
                                answer=diff_answer,
                                metadata=RAGResponseMetadata(),
                            )
                            prev_answer += diff_answer

                            logger.debug(
                                f"answer_astream func_calling=True question={question} rolling_msg={rolling_message} chunk_id={chunk_id}, chunk={parsed_chunk}"
                            )
                            yield parsed_chunk
                    else:
                        parsed_chunk = ParsedRAGChunkResponse(
                            answer=answer_str,
                            metadata=RAGResponseMetadata(),
                        )
                        logger.debug(
                            f"answer_astream func_calling=False question={question} rolling_msg={rolling_message} chunk_id={chunk_id}, chunk={parsed_chunk}"
                        )
                        yield parsed_chunk

                    chunk_id += 1

        last_chunk = ParsedRAGChunkResponse(
            answer="",
            metadata=get_chunk_metadata(rolling_message, sources),
            last_chunk=True,
        )
        logger.debug(
            f"answer_astream last_chunk={last_chunk} question={question} rolling_msg={rolling_message} chunk_id={chunk_id}"
        )
        yield last_chunk