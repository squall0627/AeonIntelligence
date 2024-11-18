import asyncio
import logging
from uuid import uuid4

import openai
from langchain.retrievers import ContextualCompressionRetriever
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, AIMessageChunk
from langchain_core.prompts import BasePromptTemplate, format_document
from langchain_core.vectorstores import VectorStore
from langgraph.constants import START, END
from langgraph.graph import add_messages, StateGraph
from langgraph.types import Send
from pydantic import BaseModel

from core.ai_core.llm import LLMEndpoint
from core.ai_core.llm_tools.cited_answer_tool import CitedAnswerToolsList
from core.ai_core.llm_tools.tools_factory import LLMToolFactory
from core.ai_core.rag.ai_rag_config import RetrievalConfig
from core.ai_core.rag.ai_rag_reranker import AIRagReranker
from core.ai_core.rag.ai_rag_retriever import AIRagRetriever
from core.ai_core.rag.entities.chat import ChatHistory
from core.ai_core.rag.entities.models import AiKnowledge, ParsedRAGChunkResponse, RAGResponseMetadata
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Dict,
    List,
    Sequence,
    Tuple,
    Type,
    TypedDict
)

from core.ai_core.rag.entities.node_result import TasksCompletion
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

    ### Node Functions ###
    def filter_history(self, state: AgentState) -> AgentState:
        """
        チャット履歴をフィルタリングして、現在の質問に関連するメッセージのみを含めます。

        引数:
        - state (AgentState) = チャット履歴を含む Graph State [HumanMessage(content='Hello! '), AIMessage(content="Hello! What can I do for you."), HumanMessage(content='What is the weather today'), AIMessage(content='It's sunny today.')]

        戻り値:
        - 優先順位に基づいてフィルタリングされた Graph State。
          1. max_tokens（トークン数を制限）
          2. max_history（最大履歴数を制限）
          の順に適用し、1つの HumanMessage と1つの AIMessage が1ペアとしてカウントされます。
          ※1トークンは4文字として計算されます。
        """

        chat_history = state["chat_history"]
        total_tokens = 0
        total_pairs = 0
        _chat_id = uuid4()
        _chat_history = ChatHistory(chat_id=_chat_id, kw_id=chat_history.kw_id)
        for human_message, ai_message in reversed(list(chat_history.iter_pairs())):
            message_tokens = self.llm_endpoint.count_tokens(
                human_message.content
            ) + self.llm_endpoint.count_tokens(ai_message.content)
            if (
                    total_tokens + message_tokens
                    > self.retrieval_config.llm_config.max_context_tokens
                    or total_pairs >= self.retrieval_config.max_history
            ):
                break
            _chat_history.append(human_message)
            _chat_history.append(ai_message)
            total_tokens += message_tokens
            total_pairs += 1

        return {**state, "chat_history": _chat_history}

    ### Node Functions ###
    async def rephrase_question(self, state: AgentState) -> AgentState:
        """
        クエリを変換して、より良い質問を作成します。

        引数:
        - state (AgentState): Graph State

        戻り値:
        - 言い換えられた質問を含む更新された Graph State
        """

        tasks = (
            state["tasks"]
            if "tasks" in state and state["tasks"]
            else [state["messages"][0].content]
        )

        # Prepare the async tasks for all user tasks
        async_tasks = []
        for task in tasks:
            msg = custom_prompts.CONDENSE_QUESTION_PROMPT.format(
                chat_history=state["chat_history"].to_list(),
                question=task,
            )

            model = self.llm_endpoint.llm
            # Asynchronously invoke the model for each question
            async_tasks.append(model.ainvoke(msg))

        # Gather all the responses asynchronously
        responses = await asyncio.gather(*async_tasks) if async_tasks else []

        # Replace each question with its condensed version
        condensed_questions = []
        for response in responses:
            condensed_questions.append(response.content)

        return {**state, "tasks": condensed_questions}

    ### Node Functions ###
    def tool_routing(self, state: AgentState):
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

        p_input, _ = self._reduce_rag_context(
            inputs=p_input,
            prompt=custom_prompts.TOOL_ROUTING_PROMPT,
            docs=docs,
        )

        msg = custom_prompts.TOOL_ROUTING_PROMPT.format(**p_input)

        response: TasksCompletion = self._invoke_structured_output(msg, TasksCompletion)

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

    ### Node Functions ###
    async def run_tool(self, state: AgentState) -> AgentState:
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
            formatted_input = tool_wrapper.format_input(task)
            # Asynchronously invoke the model for each question
            async_tasks.append(tool_wrapper.tool.ainvoke(formatted_input))

        # Gather all the responses asynchronously
        responses = await asyncio.gather(*async_tasks) if async_tasks else []

        docs = []
        for response in responses:
            _docs = tool_wrapper.format_output(response)
            _docs = self._filter_chunks_by_relevance(_docs)
            docs += _docs

        return {**state, "docs": state["docs"] + docs}

    ### Node Functions ###
    async def retrieve(self, state: AgentState) -> AgentState:
        """
        関連するチャンクを取得します。

        引数:
        - state (AgentState): Graph State

        戻り値:
        - 取得された関連するチャンク
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
            _docs = self._filter_chunks_by_relevance(response)
            docs += _docs

        return {**state, "docs": docs}

    ### Node Functions ###
    def generate_rag(self, state: AgentState) -> AgentState:
        docs: List[Document] | None = state["docs"]
        final_inputs = self._build_rag_prompt_inputs(state, docs)

        reduced_inputs, docs = self._reduce_rag_context(
            final_inputs, custom_prompts.RAG_ANSWER_PROMPT, docs
        )

        msg = custom_prompts.RAG_ANSWER_PROMPT.format(**reduced_inputs)
        llm = self._bind_tools_to_llm(self.generate_rag.__name__)
        response = llm.invoke(msg)

        return {**state, "messages": [response], "docs": docs if docs else []}

    def _filter_chunks_by_relevance(self, chunks: List[Document], **kwargs):
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

    def _build_rag_prompt_inputs(
            self, state: AgentState, docs: List[Document] | None
    ) -> Dict[str, Any]:
        """
        RAG_ANSWER_PROMPT の入力辞書を構築します。

        引数:
        - state: Graph State
        - docs: ドキュメントのリスト、または `None`

        戻り値:
        - RAG_ANSWER_PROMPT に必要なすべての入力を含む辞書
        """
        messages = state["messages"]
        user_question = messages[0].content
        files = state["files"]
        prompt = self.retrieval_config.prompt
        available_tools, _ = self.retrieval_config.workflow_config.collect_tools_prompt()

        return {
            "context": self._combine_documents(docs) if docs else "None",
            "question": user_question,
            "rephrased_task": state["tasks"],
            "custom_instructions": prompt if prompt else "None",
            "files": files if files else "None",
            "chat_history": state["chat_history"].to_list(),
            "reasoning": state["reasoning"] if "reasoning" in state else "None",
            "tools": available_tools,
        }

    def _reduce_rag_context(
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
                inputs["context"] = self._combine_documents(docs)

            msg = prompt.format(**inputs)
            n = self.llm_endpoint.count_tokens(msg)

            iteration += 1
            if iteration > max_iteration:
                logging.warning(
                    f"Attained the maximum number of iterations ({max_iteration})"
                )
                break

        return inputs, docs

    def _bind_tools_to_llm(self, node_name: str):
        if self.llm_endpoint.supports_func_calling():
            tools = self.retrieval_config.workflow_config.get_node_tools(node_name)
            if tools:
                return self.llm_endpoint.llm.bind_tools(tools, tool_choice="any")
        return self.llm_endpoint.llm

    def _invoke_structured_output(
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

    async def answer_astream(
            self,
            question: str,
            history: ChatHistory,
            list_files: list[AiKnowledge],
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
                workflow.add_node(node.name, getattr(self, node.name))

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
    def _format_file_list(cls, list_files_array: list[AiKnowledge], max_files: int = 20) -> str:
        list_files = [file.file_name or file.url for file in list_files_array]
        files: list[str] = list(filter(lambda n: n is not None, list_files))
        files = files[:max_files]

        files_str = "\n".join(files) if list_files_array else "None"
        return files_str

    # @no_type_check
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

    @classmethod
    def _combine_documents(
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