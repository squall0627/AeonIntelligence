from enum import Enum
from typing import Any, Optional, Dict
from uuid import UUID
from datetime import datetime

from langchain_core.documents import Document
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class SearchResult(BaseModel):
    chunk: Document
    distance: float

class KnowledgeStatus(str, Enum):
    ERROR = "ERROR"
    RESERVED = "RESERVED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    UPLOADED = "UPLOADED"

class AIKnowledge(BaseModel):
    id: UUID
    file_name: str
    brain_ids: list[UUID] | None = None
    url: Optional[str] = None
    extension: str = ".txt"
    mime_type: str = "txt"
    status: KnowledgeStatus = KnowledgeStatus.PROCESSING
    source: Optional[str] = None
    source_link: str | None = None
    file_size: int | None = None
    file_sha1: str | None = None
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, str]] = None

class RawRAGResponse(TypedDict):
    answer: dict[str, Any]
    docs: dict[str, Any]

class ChatLLMMetadata(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    image_url: str | None = None
    kw_id: str | None = None
    kw_name: str | None = None

class RAGResponseMetadata(BaseModel):
    citations: list[int] = Field(default_factory=list)
    followup_questions: list[str] = Field(default_factory=list)
    sources: list[Any] = Field(default_factory=list)
    metadata_model: ChatLLMMetadata | None = None

class ParsedRAGResponse(BaseModel):
    answer: str
    metadata: RAGResponseMetadata | None = None

class ParsedRAGChunkResponse(BaseModel):
    answer: str
    metadata: RAGResponseMetadata
    last_chunk: bool = False