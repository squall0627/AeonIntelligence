import logging

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from core.ai_core.knowledge_warehouse.serialization import VectordbConfig
from core.ai_core.vectordb.vectordb_registry import get_vectordb_class
from core.ai_core.vectordb.vectordb_base import VectordbBase
from core.ai_core.vectordb.vectordb_config import default_vectordb_type, VectordbType

logger = logging.getLogger("ai_core")

class VectordbBuilder:

    @classmethod
    async def build_default_vectordb(cls, docs: list[Document], embedder: Embeddings) -> VectordbBase:
        return await cls.build_vectordb(default_vectordb_type(), docs, embedder)

    @classmethod
    async def build_vectordb(cls, vectordb_type: VectordbType, docs: list[Document], embedder: Embeddings) -> VectordbBase:
        vectordb_cls = get_vectordb_class(vectordb_type)
        return await vectordb_cls().build(docs, embedder)

    @classmethod
    def load_vectordb(cls, config: VectordbConfig, embeddings: Embeddings) -> VectordbBase:
        vectordb_cls = get_vectordb_class(config.vectordb_type)
        return vectordb_cls().load(config, embeddings)