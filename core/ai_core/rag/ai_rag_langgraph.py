import logging

from langchain_core.documents import Document
from langchain_core.messages import AIMessageChunk
from langchain_core.vectorstores import VectorStore
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from core.ai_core.llm import LLMEndpoint
from core.ai_core.llm_tools.cited_answer_tool import CitedAnswerToolsList
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.entities.chat import ChatHistory
from core.ai_core.rag.entities.models import AIKnowledge, ParsedRAGChunkResponse, RAGResponseMetadata
from typing import (
    Any,
    AsyncGenerator,
    Tuple,
)


from core.ai_core.rag.node_functions.base_node_function import AgentState
from core.ai_core.rag.node_functions.node_functions_factory import NodeFunctionsFactory

logger = logging.getLogger("ai_core")

class AiQARAGLangGraph:
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

        self.graph = None
        self.final_nodes = []

    async def answer_astream(
            self,
            question: str,
            history: ChatHistory,
            list_files: list[AIKnowledge],
            metadata=None,
    ) -> AsyncGenerator[ParsedRAGChunkResponse, ParsedRAGChunkResponse]:

        if metadata is None:
            metadata = {}

        concat_list_files = self._format_file_list(
            list_files, self.retrieval_config.max_files
        )
        conversational_qa_chain = self.create_graph()

        rolling_message = AIMessageChunk(content="")
        docs: list[Document] | None = None
        previous_content = ""

        async for event in conversational_qa_chain.astream_events(
                {
                    "messages": [("user", question)],
                    "chat_history": history,
                    "files": concat_list_files,
                },
                version="v1",
                config={"metadata": metadata},
        ):
            if self._is_final_node_with_docs(event):
                docs = event["data"]["output"]["docs"]

            if self._is_final_node_and_chat_model_stream(event):
                chunk = event["data"]["chunk"]
                rolling_message, new_content, previous_content = self._parse_chunk_response(
                    rolling_message,
                    chunk,
                    self.llm_endpoint.supports_func_calling(),
                    previous_content,
                )

                if new_content:
                    chunk_metadata = self._get_chunk_metadata(rolling_message, docs)
                    yield ParsedRAGChunkResponse(
                        answer=new_content, metadata=chunk_metadata
                    )

        # Yield final metadata chunk
        yield ParsedRAGChunkResponse(
            answer="",
            metadata=self._get_chunk_metadata(rolling_message, docs),
            last_chunk=True,
        )

    def create_graph(self):
        if not self.graph:
            workflow = StateGraph(AgentState)

            self._build_workflow(workflow)

            self.graph = workflow.compile()
        return self.graph

    def _build_workflow(self, workflow: StateGraph):
        # Add nodes to the workflow
        for node in self.retrieval_config.workflow_config.nodes:
            if node.name not in [START, END]:
                workflow.add_node(node.name, NodeFunctionsFactory.get_node_function(node.name,
                                                                                    retrieval_config=self.retrieval_config,
                                                                                    llm=self.llm_endpoint,
                                                                                    vector_store=self.vector_store))

        # Add edges to the workflow
        for node in self.retrieval_config.workflow_config.nodes:
            if node.edges:
                for edge in node.edges:
                    workflow.add_edge(node.name, edge)
                    if edge == END:
                        self.final_nodes.append(node.name)
            elif node.conditional_edge:
                routing_function = getattr(self, node.conditional_edge.routing_function)
                workflow.add_conditional_edges(
                    node.name, routing_function, node.conditional_edge.conditions
                )
                if END in node.conditional_edge.conditions:
                    self.final_nodes.append(node.name)
            else:
                raise ValueError("Node should have at least one edge or conditional_edge")

    def _is_final_node_with_docs(self, event: dict) -> bool:
        return (
                "output" in event["data"]
                and event["data"]["output"] is not None
                and "docs" in event["data"]["output"]
                and event["metadata"]["langgraph_node"] in self.final_nodes
        )

    def _is_final_node_and_chat_model_stream(self, event: dict) -> bool:
        return (
                event["event"] == "on_chat_model_stream"
                and "langgraph_node" in event["metadata"]
                and event["metadata"]["langgraph_node"] in self.final_nodes
        )

    @classmethod
    def _format_file_list(cls, list_files_array: list[AIKnowledge], max_files: int = 20) -> str:
        list_files = [file.file_name or file.url for file in list_files_array]
        files: list[str] = list(filter(lambda n: n is not None, list_files))
        files = files[:max_files]

        files_str = "\n".join(files) if list_files_array else "None"
        return files_str

    @classmethod
    def _parse_chunk_response(
            cls,
            rolling_msg: AIMessageChunk,
            raw_chunk: AIMessageChunk,
            supports_func_calling: bool,
            previous_content: str = "",
    ) -> Tuple[AIMessageChunk, str, str]:

        rolling_msg += raw_chunk

        if not supports_func_calling or not rolling_msg.tool_calls:
            new_content = raw_chunk.content
            full_content = rolling_msg.content
            return rolling_msg, new_content, full_content

        current_answers = cls._get_answers_from_tool_calls(rolling_msg.tool_calls)
        full_answer = "\n\n".join(current_answers)
        new_content = full_answer[len(previous_content) :]

        return rolling_msg, new_content, full_answer

    @classmethod
    def _get_answers_from_tool_calls(cls, tool_calls):
        answers = []
        for tool_call in tool_calls:
            if tool_call.get("name") == CitedAnswerToolsList.SIMPLE_CITED_ANSWER.value and "args" in tool_call:
                answers.append(tool_call["args"].get("answer", ""))
        return answers

    @classmethod
    def _get_chunk_metadata(cls,
            msg: AIMessageChunk, sources: list[Any] | None = None
    ) -> RAGResponseMetadata:
        metadata = {"sources": sources or []}

        if not msg.tool_calls:
            return RAGResponseMetadata(**metadata, metadata_model=None)

        all_citations = []
        all_followup_questions = []

        for tool_call in msg.tool_calls:
            if tool_call.get("name") == CitedAnswerToolsList.SIMPLE_CITED_ANSWER.value and "args" in tool_call:
                args = tool_call["args"]
                all_citations.extend(args.get("citations", []))
                all_followup_questions.extend(args.get("followup_questions", []))

        metadata["citations"] = all_citations
        metadata["followup_questions"] = all_followup_questions[:3]  # Limit to 3

        return RAGResponseMetadata(**metadata, metadata_model=None)