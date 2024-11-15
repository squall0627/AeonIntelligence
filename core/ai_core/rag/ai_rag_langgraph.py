
from core.ai_core.rag.entities.chat import ChatHistory
from core.ai_core.rag.entities.models import AiKnowledge, ParsedRAGChunkResponse
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypedDict,
)

class AiQARAGLangGraph:
    """TODO"""

    async def answer_astream(
            self,
            question: str,
            history: ChatHistory,
            list_files: list[AiKnowledge],
            metadata: dict[str, str] = {},
    ) -> AsyncGenerator[ParsedRAGChunkResponse, ParsedRAGChunkResponse]:
        """TODO"""