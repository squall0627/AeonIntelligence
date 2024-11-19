from uuid import uuid4

from langchain_core.vectorstores import VectorStore

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.entities.chat import ChatHistory
from core.ai_core.rag.node_functions.node_function_base import NodeFunctionBase, AgentState


class FilterHistory(NodeFunctionBase):
    name="filter_history"
    is_async=False

    def __init__(self,
                 retrieval_config: RetrievalConfig,
                 llm: LLMEndpoint,
                 vector_store: VectorStore | None = None,):
        super().__init__(retrieval_config=retrieval_config, llm=llm, vector_store=vector_store)

    def run(self, state: AgentState) -> AgentState:
        """
        Filter out the chat history to only include the messages that are relevant to the current question

        Takes in a chat_history= [HumanMessage(content='Who is Chin Hiroshi ? '),
        AIMessage(content="Chin Hiroshi is an employee working for the company Aeon as a Software Engineer,
        under the supervision of his manager, Nomura Tadahiro."),
        HumanMessage(content='Tell me more about him.'), AIMessage(content=''),
        HumanMessage(content='Tell me more about him.'),
        AIMessage(content="Sorry, I don’t have any more information about Chin Hiroshi from the files provided.")]
        Returns a filtered chat_history with in priority: first max_tokens, then max_history where a Human message and an AI message count as one pair
        a token is 4 characters
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