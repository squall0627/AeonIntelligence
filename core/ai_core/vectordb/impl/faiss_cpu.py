import logging
import os

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from core.ai_core.knowledge_warehouse.serialization import VectordbConfig, FAISSConfig
from core.ai_core.vectordb.vectordb_base import VectordbBase
from core.ai_core.vectordb.vectordb_builder import VectordbType

logger = logging.getLogger("ai_core")

class FaissCpu(VectordbBase):
    def __init__(self) -> None:
        super().__init__(VectordbType.FaissCPU)

    async def build_impl(self,  docs: list[Document], embedder: Embeddings) -> VectorStore:
        logger.debug(f"Using {VectordbType.FaissCPU} as vector store.")
        vector_db = await FAISS.afrom_documents(documents=docs, embedding=embedder)
        return vector_db

    async def save_impl(self, kw_path: str) -> VectordbConfig:
        if isinstance(self.vector_db, FAISS):
            vectordb_path = os.path.join(kw_path, "vector_store_faiss")
            os.makedirs(vectordb_path, exist_ok=True)
            self.vector_db.save_local(folder_path=vectordb_path)
            return FAISSConfig(vectordb_folder_path=vectordb_path)
        else:
            raise Exception(f"Can't serialize other vector stores {self.vector_db} for now")

    def load_impl(self, config: VectordbConfig, embedder: Embeddings) -> VectorStore:
        vector_db = FAISS.load_local(
            folder_path=config.vectordb_folder_path,
            embeddings=embedder,
            allow_dangerous_deserialization=True,
        )
        return vector_db