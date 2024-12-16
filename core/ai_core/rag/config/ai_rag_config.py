import os
from enum import Enum

from core.ai_core.base_config import AIBaseConfig
from core.ai_core.llm.llm_config import LLMEndpointConfig
from core.ai_core.rag.ai_rag_workflow import DefaultWorkflow
from core.ai_core.rag.config.langgraph_config import WorkflowConfig
from core.ai_core.utils.utils import normalize_to_env_variable_name


class DefaultRerankers(str, Enum):
    COHERE = "cohere"
    JINA = "jina"

    @property
    def default_model(self) -> str:
        return {
            self.COHERE: "rerank-multilingual-v3.0",
            self.JINA: "jina-reranker-v2-base-multilingual",
        }[self]


class RerankerConfig(AIBaseConfig):
    supplier: DefaultRerankers | None = None
    model: str | None = None
    top_n: int = 5  # Number of chunks returned by the re-ranker
    api_key: str | None = None
    relevance_score_threshold: float | None = None
    relevance_score_key: str = "relevance_score"

    def __init__(self, **data):
        super().__init__(**data)
        self.validate_model()

    def validate_model(self):
        if self.model is None and self.supplier is not None:
            self.model = self.supplier.default_model

        if self.supplier:
            api_key_var = f"{normalize_to_env_variable_name(self.supplier)}_API_KEY"
            self.api_key = os.getenv(api_key_var)

            if self.api_key is None:
                raise ValueError(
                    f"The API key for supplier '{self.supplier}' is not set. "
                    f"Please set the environment variable: {api_key_var}"
                )


class RetrievalConfig(AIBaseConfig):
    reranker_config: RerankerConfig = RerankerConfig()
    llm_config: LLMEndpointConfig = LLMEndpointConfig()
    max_history: int = 10
    max_files: int = 20
    k: int = 40  # Number of chunks returned by the retriever
    prompt: str | None = None
    workflow_config: WorkflowConfig = WorkflowConfig(nodes=DefaultWorkflow.RAG.nodes)

    def __init__(self, **data):
        super().__init__(**data)
        self.llm_config.set_api_key(force_reset=False)
