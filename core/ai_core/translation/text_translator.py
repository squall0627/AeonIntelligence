from core.ai_core.llm import LLMEndpoint
from core.ai_core.llm.llm_config import (
    LLMEndpointConfig,
    DefaultModelSuppliers,
    LLMName,
)
from core.ai_core.translation.language import Language
from core.ai_core.translation.prompts import translation_prompts
from core.utils.log_handler import rotating_file_logger

logger = rotating_file_logger("ai_core")


def default_translate_llm() -> LLMEndpoint:
    try:
        llm = LLMEndpoint.from_config(
            LLMEndpointConfig(
                supplier=DefaultModelSuppliers.ALIBABA, model=LLMName.qwen_2_5_32b
            )
        )
        return llm
    except ImportError as e:
        raise ImportError("Please provide a valid BaseLLM") from e


class TextTranslator:
    def __init__(
        self,
        source_language: Language | str,
        target_language: Language | str,
        keywords_map: dict | None = None,
        llm: LLMEndpoint | None = None,
    ):
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
        self.keywords_map = keywords_map if keywords_map else {}
        self.llm = llm if llm else default_translate_llm()
        logger.debug(
            f"Translator initialized with source_language: {self.source_language}, "
            f"target_language: {self.target_language}, keywords_map: {self.keywords_map}, llm: {self.llm.get_config()}"
        )

    def translate(self, input_text: str) -> str:
        # if input_text is empty, return empty string
        if not input_text or input_text.strip() == "":
            return ""
        # if input_text is "-", return "-"
        if input_text in ["-", "ー", "‐"]:
            return input_text

        msg = translation_prompts.SIMPLE_TRANSLATE_PROMPT.format(
            keywords_map=self.keywords_map,
            instruction=f"Translate {self.source_language} to {self.target_language}.",
            input_text=input_text,
        )
        logger.debug(f"Message: {msg}")

        # Invoke the model
        response = self.llm.llm.invoke(msg)
        logger.debug(f"Response: {response}")

        return response.content
