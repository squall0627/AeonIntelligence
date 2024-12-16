import logging

from abc import ABC, abstractmethod
from typing import Self, List

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from core.ai_core.knowledge_warehouse.serialization import VectordbConfig
from core.ai_core.vectordb.vectordb_config import VectordbType

logger = logging.getLogger("ai_core")


class VectordbBase(ABC):
    supported_vectordb: list[VectordbType]
    vector_db: VectorStore | None
    # docs: list[Document] | None
    embedder: Embeddings | None

    def __init__(self, vectordb_type: VectordbType) -> None:
        self.vectordb_type = vectordb_type

    def check_build(self):
        if self.vector_db is None:
            raise ValueError("Can't save/load vectordb without building it first")

    async def build(self, docs: list[Document], embedder: Embeddings) -> Self:
        logger.debug(f"Building vectordb {self.vectordb_type}")
        if docs is None or len(docs) == 0:
            raise ValueError("Can't initialize knowledge warehouse without documents")
        if embedder is None:
            raise ValueError("Can't initialize knowledge warehouse without an embedder")
        # self.docs = docs
        self.embedder = embedder
        self.vector_db = await self.build_impl(docs, embedder)
        return self

    @abstractmethod
    async def build_impl(
        self, docs: list[Document], embedder: Embeddings
    ) -> VectorStore:
        raise NotImplementedError

    async def save(self, kw_path: str) -> VectordbConfig:
        logger.debug(f"Saving vectordb {self.vectordb_type} to {kw_path}")
        self.check_build()
        return await self.save_impl(kw_path)

    @abstractmethod
    async def save_impl(self, kw_path: str) -> VectordbConfig:
        raise NotImplementedError

    def load(self, config: VectordbConfig, embedder: Embeddings) -> Self:
        logger.debug(
            f"Loading vectordb {self.vectordb_type} from {config.vectordb_folder_path}"
        )
        # get docs from vector db
        # self.docs = self.vector_db.get_by_ids(config.docs_ids)
        self.embedder = embedder
        self.vector_db = self.load_impl(config, embedder)
        return self

    @abstractmethod
    def load_impl(self, config: VectordbConfig, embedder: Embeddings) -> VectorStore:
        raise NotImplementedError

    def get_all_ids(self) -> List[str]:
        """Get all document IDs from the vector store."""
        if hasattr(self.vector_db, "docstore"):
            return list(self.vector_db.docstore._dict.keys())
        return []
