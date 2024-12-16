import logging

from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from core.ai_core.embedder.embedder_base import EmbedderBase
from core.ai_core.embedder.embedder_builder import EmbedderType
from core.ai_core.knowledge_warehouse.serialization import EmbedderConfig
from core.ai_core.llm.llm_config import LLMName

logger = logging.getLogger("ai_core")


class OllamaEmbedder(EmbedderBase):
    def __init__(self) -> None:
        super().__init__(EmbedderType.OllamaEmbeddings)

    def build_impl(self, llm_name: LLMName | None) -> Embeddings:
        logger.debug(
            f"Loaded {EmbedderType.OllamaEmbeddings}.{llm_name} as default Embedder LLM for knowledge warehouse"
        )
        embedder = OllamaEmbeddings(model=llm_name)
        return embedder

    def save_impl(self) -> EmbedderConfig:
        if isinstance(self.embedder, OllamaEmbeddings):
            return EmbedderConfig(
                llm_name=self.llm_name, config=self.embedder.model_dump()
            )
        else:
            raise Exception(f"Can't serialize other embedder {self.embedder} for now")

    def load_impl(self, llm_name: LLMName) -> Embeddings:
        return self.build(llm_name).embedder
