import logging

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.documents import Document

from core.ai_core.files.file import FileExtension, AIFile

logger = logging.getLogger("ai_core")

class ProcessorBase(ABC):
    supported_extensions: list[FileExtension | str]

    def check_supported(self, file: AIFile):
        if file.file_extension not in self.supported_extensions:
            raise ValueError(f"can't process a file of type {file.file_extension}")

    async def process_file(self, file: AIFile) -> list[Document]:
        logger.debug(f"Processing file {file}")
        self.check_supported(file)
        docs = await self.process_file_impl(file)

        for idx, doc in enumerate(docs, start=1):
            if "original_file_name" in doc.metadata:
                doc.page_content = f"Filename: {doc.metadata['original_file_name']} Content: {doc.page_content}"
            doc.page_content = doc.page_content.replace("\u0000", "")
            doc.page_content = doc.page_content.encode("utf-8", "replace").decode(
                "utf-8"
            )
            doc.metadata = {
                "chunk_index": idx,
                **file.metadata,
                **doc.metadata,
                **self.processor_metadata,
            }
        return docs

    @abstractmethod
    async def process_file_impl(self, file: AIFile) -> list[Document]:
        raise NotImplementedError

    @property
    @abstractmethod
    def processor_metadata(self) -> dict[str, Any]:
        raise NotImplementedError