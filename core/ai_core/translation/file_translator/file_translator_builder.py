import os
from pathlib import Path

from core.ai_core.translation.file_translator.file_translator_base import (
    FileTranslatorBase,
)
from core.ai_core.translation.file_translator.file_translator_registry import (
    get_translator_class,
)
from core.ai_core.translation.file_translator.file_translator_type import (
    FileTranslatorType,
)
from core.ai_core.translation.language import Language


class FileTranslatorBuilder:
    @classmethod
    def build_file_translator(
        cls,
        input_file_path: Path | str,
        source_language: Language | str,
        target_language: Language | str,
        keywords_map: dict | None = None,
    ) -> FileTranslatorBase:
        # get extension of input file
        _, ext = os.path.splitext(input_file_path)
        ext = ext.replace(".", "")

        # get translator type by extension
        file_translator_type = FileTranslatorType(ext.lower())

        # get translator class by translator type
        file_translator_cls = get_translator_class(file_translator_type)

        # build translator class
        return file_translator_cls().build(
            input_file_path, source_language, target_language, keywords_map
        )
