import asyncio

from langchain_core.vectorstores import VectorStore

from core.ai_core.llm import LLMEndpoint
from core.ai_core.rag.config.ai_rag_config import RetrievalConfig
from core.ai_core.rag.node_functions.base_node_function import BaseNodeFunction, AgentState
from core.ai_core.rag.prompts import custom_prompts


class RephraseQuestion(BaseNodeFunction):
    name="rephrase_question"
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