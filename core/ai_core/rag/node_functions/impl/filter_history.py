from uuid import uuid4

from langchain_core.vectorstores import VectorStore

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.entities.chat import ChatHistory
from core.ai_core.rag.node_functions.base_node_function import BaseNodeFunction, AgentState


class FilterHistory(BaseNodeFunction):
    name="filter_history"
    is_async=False

    def __init__(self,
                 retrieval_config: RetrievalConfig,
                 llm: LLMEndpoint,
                 vector_store: VectorStore | None = None,):
        super().__init__(retrieval_config=retrieval_config, llm=llm, vector_store=vector_store)

    def run(self, state: AgentState) -> AgentState:
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

    async def arun(self, state: AgentState) -> AgentState:
        raise NotImplementedError