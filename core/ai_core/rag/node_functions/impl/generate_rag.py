from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.node_functions.base_node_function import BaseNodeFunction, AgentState
from core.ai_core.rag.prompts import custom_prompts


class GenerateRag(BaseNodeFunction):
    name="generate_rag"
    is_async=False

    def __init__(self,
                 retrieval_config: RetrievalConfig,
                 llm: LLMEndpoint,
                 vector_store: VectorStore | None = None,):
        super().__init__(retrieval_config=retrieval_config, llm=llm, vector_store=vector_store)

    def run(self, state: AgentState) -> AgentState:
        docs: List[Document] | None = state["docs"]
        final_inputs = self._build_rag_prompt_inputs(state, docs)

        reduced_inputs, docs = self.reduce_rag_context(
            final_inputs, custom_prompts.RAG_ANSWER_PROMPT, docs
        )

        msg = custom_prompts.RAG_ANSWER_PROMPT.format(**reduced_inputs)
        llm = self.bind_tools_to_llm(self.name)
        response = llm.invoke(msg)

        return {**state, "messages": [response], "docs": docs if docs else []}

    async def arun(self, state: AgentState) -> AgentState:
        raise NotImplementedError

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
            "context": self.combine_documents(docs) if docs else "None",
            "question": user_question,
            "rephrased_task": state["tasks"],
            "custom_instructions": prompt if prompt else "None",
            "files": files if files else "None",
            "chat_history": state["chat_history"].to_list(),
            "reasoning": state["reasoning"] if "reasoning" in state else "None",
            "tools": available_tools,
        }