from enum import Enum
from typing import List

from langgraph.constants import START, END

from core.ai_core.llm_tools.cited_answer_tool import CitedAnswerToolsList
from core.ai_core.rag.config.langgraph_config import NodeConfig


class DefaultWorkflow(str, Enum):
    RAG = "rag"

    @property
    def nodes(self) -> List[NodeConfig]:
        workflows = {
            self.RAG: [
                NodeConfig(name=START, edges=["filter_history"]),
                NodeConfig(name="filter_history", edges=["rephrase_question"]),
                NodeConfig(name="rephrase_question", edges=["retrieve"]),
                NodeConfig(name="retrieve", edges=["generate_rag"]),
                NodeConfig(
                    name="generate_rag",
                    edges=[END],
                    tools=[{"name": CitedAnswerToolsList.SIMPLE_CITED_ANSWER}],
                ),
            ]
        }
        return workflows[self]
