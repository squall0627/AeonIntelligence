import stopwatch
import asyncio

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Self

from core.ai_core.translation.file_translator.file_translator_type import (
    FileTranslatorType,
)
from core.ai_core.translation.file_translator.models.file_translation_status import (
    FileTranslationStatus,
    Status,
)
from core.ai_core.translation.language import Language
from core.ai_core.translation.text_translator import TextTranslator
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

    async def atranslate(self, output_dir: Path | str) -> FileTranslationStatus:
        sw = stopwatch.Stopwatch()
        sw.start()

        self.status.status = Status.PROCESSING
        try:
            output_file_path = await self.translate_impl(output_dir)
            self.status.output_file_path = output_file_path
            self.status.status = Status.COMPLETED
            self.status.progress = 100
        except Exception as e:
            self.status.error = str(e)
            self.status.status = Status.ERROR

        sw.stop()
        duration = sw.duration
        logger.info(f"Translation completed in {duration:.2f} seconds")
        self.status.duration = duration
        await self.status.persist()
        return self.status

    def translate(self, output_dir: Path | str) -> FileTranslationStatus:
        return asyncio.run(self.atranslate(output_dir))

    @abstractmethod
    async def translate_impl(self, output_dir: Path | str) -> Path | str:
        raise NotImplementedError

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
