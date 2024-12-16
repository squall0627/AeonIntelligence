from pathlib import Path
from typing import Dict, Any, Union, TypeAlias, Literal
from uuid import UUID
from pydantic import BaseModel, Field

from core.ai_core.embedder.embedder_config import default_embedder_type, EmbedderType
from core.ai_core.files.file import AIFileSerialized
from core.ai_core.llm.llm_config import LLMEndpointConfig, LLMName
from core.ai_core.rag.entities.chat import ChatMessage
from core.ai_core.storage.storage_config import StorageType
from core.ai_core.vectordb.vectordb_config import VectordbType


class EmbedderConfig(BaseModel):
    embedder_type: Literal[EmbedderType.OllamaEmbeddings] = default_embedder_type()
    llm_name: LLMName
    config: Dict[str, Any]


class FAISSConfig(BaseModel):
    vectordb_type: Literal[VectordbType.FaissCPU, VectordbType.FaissGPU] = (
        VectordbType.FaissCPU
    )
    vectordb_folder_path: str


VectordbConfig: TypeAlias = Union[FAISSConfig]


class LocalStorageConfig(BaseModel):
    storage_type: Literal[StorageType.LocalStorage] = StorageType.LocalStorage
    storage_path: Path
    files: dict[UUID, AIFileSerialized]


class TransparentStorageConfig(BaseModel):
    storage_type: Literal[StorageType.TransparentStorage] = (
        StorageType.TransparentStorage
    )
    files: dict[UUID, AIFileSerialized]


StorageConfig: TypeAlias = Union[TransparentStorageConfig, LocalStorageConfig]


class KWSerialized(BaseModel):
    kw_id: UUID
    kw_name: str
    chat_history: list[ChatMessage]
    vectordb_config: VectordbConfig = Field(..., discriminator="vectordb_type")
    storage_config: StorageConfig = Field(..., discriminator="storage_type")
    llm_config: LLMEndpointConfig
    embedding_config: EmbedderConfig
