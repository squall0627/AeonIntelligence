import logging

from core.ai_core.embedder.embedder_base import EmbedderBase
from core.ai_core.embedder.embedder_config import EmbedderType, default_embedder_type
from core.ai_core.embedder.embedder_registry import get_embedder_class
from core.ai_core.knowledge_warehouse.serialization import EmbedderConfig
from core.ai_core.llm.llm_config import DEFAULT_LLM_NAME, LLMName

logger = logging.getLogger("ai_core")

class EmbedderBuilder:

    @classmethod
    def build_default_embedder(cls) -> EmbedderBase:
        return cls.build_embedder(default_embedder_type(), DEFAULT_LLM_NAME)

    @classmethod
    def build_embedder(cls, embedder_type: EmbedderType, llm_name: LLMName) -> EmbedderBase:
        embedder_cls = get_embedder_class(embedder_type)
        return embedder_cls().build(llm_name)


    @classmethod
    def load_embedder(cls, config: EmbedderConfig) -> EmbedderBase:
        embedder_cls = get_embedder_class(config.embedder_type)
        return embedder_cls().load(config)