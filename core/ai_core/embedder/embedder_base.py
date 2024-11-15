import logging

from abc import ABC, abstractmethod
from typing import Self

from langchain_core.embeddings import Embeddings

from core.ai_core.embedder.embedder_config import EmbedderType
from core.ai_core.knowledge_warehouse.serialization import EmbedderConfig
from core.ai_core.llm.llm_config import LLMName

logger = logging.getLogger("ai_core")

class EmbedderBase(ABC):
    supported_embedder: list[EmbedderType]
    embedder: Embeddings | None
    llm_name: LLMName | None

    def __init__(self, embedder_type: EmbedderType) -> None:
        self.embedder_type = embedder_type

    def check_build(self):
        if self.embedder is None:
            raise ValueError("Can't save/load embedder without building it first")

    def build(self, llm_name: LLMName | None) -> Self:
        logger.debug(f"Building embedder {self.embedder_type}")
        self.llm_name = llm_name
        self.embedder = self.build_impl(llm_name)
        return self

    @abstractmethod
    def build_impl(self, llm_name: LLMName | None) -> Embeddings:
        raise NotImplementedError

    def save(self) -> EmbedderConfig:
        logger.debug(f"Saving embedder {self.embedder_type}")
        self.check_build()
        return self.save_impl()

    @abstractmethod
    def save_impl(self) -> EmbedderConfig:
        raise NotImplementedError

    def load(self, config: EmbedderConfig) -> Self:
        logger.debug(f"Loading embedder {self.embedder_type}")
        self.llm_name = config.llm_name
        self.embedder = self.load_impl(self.llm_name)
        return self

    @abstractmethod
    def load_impl(self, llm_name: LLMName) -> Embeddings:
        raise NotImplementedError