from typing import Sequence, Optional

from langchain.retrievers.document_compressors import CohereRerank
from langchain_community.document_compressors import JinaRerank
from langchain_core.callbacks import Callbacks
from langchain_core.documents import BaseDocumentCompressor, Document

from core.ai_core.rag.config.ai_rag_config import RetrievalConfig, DefaultRerankers


class IdempotentCompressor(BaseDocumentCompressor):
    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """
        与えられたドキュメントをそのまま返す、操作を行わないドキュメント圧縮ツール。

        これは、より高度なドキュメント圧縮アルゴリズムが実装されるまでのプレースホルダーです。
        """
        return documents


class AIRagReranker:
    def __init__(
        self,
        retrieval_config: RetrievalConfig,
    ):
        self.retrieval_config = retrieval_config

    def get_reranker(self, **kwargs):
        # Extract the reranker configuration from self
        config = self.retrieval_config.reranker_config

        # Allow kwargs to override specific config values
        supplier = kwargs.pop("supplier", config.supplier)
        model = kwargs.pop("model", config.model)
        top_n = kwargs.pop("top_n", config.top_n)
        api_key = kwargs.pop("api_key", config.api_key)

        if supplier == DefaultRerankers.COHERE:
            reranker = CohereRerank(
                model=model, top_n=top_n, cohere_api_key=api_key, **kwargs
            )
        elif supplier == DefaultRerankers.JINA:
            reranker = JinaRerank(
                model=model, top_n=top_n, jina_api_key=api_key, **kwargs
            )
        else:
            reranker = IdempotentCompressor()

        return reranker
