import stopwatch
import asyncio

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Self, AsyncGenerator, Any

from core.ai_core.translation.file_translator.file_translator_type import (
    FileTranslatorType,
)
from core.ai_core.translation.file_translator.models.file_translation_status import (
    FileTranslationStatus,
    Status,
)
from core.ai_core.translation.language import Language
from core.ai_core.translation.text_translator import TextTranslator
from core.utils.async_handler import sync_run_task
from core.utils.log_handler import rotating_file_logger

logger = rotating_file_logger("ai_core")


class FileTranslatorBase(ABC):
    input_file_path: Path | str
    source_language: Language | str
    target_language: Language | str
    keywords_map: dict | None
    text_translator: TextTranslator
    status: FileTranslationStatus
    kwargs: dict | None = {}

    def __init__(
        self,
        file_translator_type: FileTranslatorType | str,
    ):
        self.file_translator_type = file_translator_type

    async def astream_translate(self, output_dir: Path | str):
        logger.info(f"Starting translation for {self.input_file_path}")
        sw = stopwatch.Stopwatch()
        sw.start()

        # Initialize the status
        self.status.status = Status.PROCESSING
        self.status.progress = 0.0

        async for status in self.translate_impl(output_dir):
            yield status
            await asyncio.sleep(0.01)

        # Set the status when all tasks done
        if Status.ERROR != self.status.status:
            self.status.status = Status.COMPLETED
        sw.stop()
        duration = sw.duration
        self.status.duration = duration
        yield self.status
        await asyncio.sleep(0.01)
        logger.info(f"Translation completed in {duration:.2f} seconds")

    async def atranslate(self, output_dir: Path | str) -> FileTranslationStatus:
        async for _ in self.astream_translate(output_dir):
            pass
        return self.status

    def translate(self, output_dir: Path | str) -> FileTranslationStatus:
        return sync_run_task(self.atranslate(output_dir))

    @abstractmethod
    async def translate_impl(
        self, output_dir: Path | str
    ) -> AsyncGenerator[FileTranslationStatus, Any]:
        yield self.status

    def build(
        self,
        input_file_path: Path | str,
        source_language: Language | str,
        target_language: Language | str,
        *,
        status: FileTranslationStatus,
        keywords_map: dict | None = None,
        **kwargs,
    ) -> Self:
        logger.debug(f"Building File translator for {self.file_translator_type}")
        self.input_file_path = input_file_path
        self.source_language = (
            source_language.value
            if isinstance(source_language, Language)
            else source_language
        )
        self.target_language = (
            target_language.value
            if isinstance(target_language, Language)
            else target_language
        )
        self.status = status
        self.keywords_map = keywords_map if keywords_map else {}
        self.text_translator = TextTranslator(
            source_language, target_language, keywords_map
        )
        self.kwargs = kwargs
        return self
