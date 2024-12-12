import logging
import os

from enum import Enum
from typing import Dict, Optional

from core.ai_core.base_config import AIBaseConfig
from core.ai_core.rag.prompts import CustomPromptsModel
from core.ai_core.utils.utils import normalize_to_env_variable_name

logger = logging.getLogger("ai_core")

class LLMName(str, Enum):
    gpt_4o = "gpt-4o"
    gpt_4o_mini = "gpt-4o-mini"
    gpt_4_turbo = "gpt-4-turbo"
    gpt_4 = "gpt-4"
    gpt_35_turbo = "gpt-3.5-turbo"
    text_embedding_3_large = "text-embedding-3-large"
    text_embedding_3_small = "text-embedding-3-small"
    text_embedding_ada_002 = "text-embedding-ada-002"
    claude_3_5_sonnet = "claude-3-5-sonnet"
    claude_3_opus = "claude-3-opus"
    claude_3_sonnet = "claude-3-sonnet"
    claude_3_haiku = "claude-3-haiku"
    claude_2_1 = "claude-2-1"
    claude_2_0 = "claude-2-0"
    claude_instant_1_2 = "claude-instant-1-2"
    llama3_2_vision_11b = "llama3.2-vision:11b"
    llama_3_1_8b = "llama3.1:8b"
    llama_3_1_70b = "llama3.1:70b"
    llama_3 = "llama-3"
    llama_2 = "llama-2"
    code_llama = "code-llama"
    mistral_large = "mistral-large"
    mistral_small = "mistral-small"
    mistral_nemo = "mistral-nemo"
    mistral_7b = "mistral"
    codestral = "codestral"
    qwen_32b = "qwen:32b"
    qwq = "qwq"


DEFAULT_LLM_NAME = LLMName.mistral_small

class DefaultModelSuppliers(str, Enum):
    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    META = "meta"
    MISTRAL = "mistral"
    ALIBABA = "alibaba"

class LLMConfig(AIBaseConfig):
    context: int | None = None
    tokenizer_hub: str | None = None
    supports_func_calling: bool = True

class LLMModelConfig:
    _model_defaults: Dict[DefaultModelSuppliers, Dict[LLMName, LLMConfig]] = {
        DefaultModelSuppliers.OPENAI: {
            LLMName.gpt_4o: LLMConfig(context=128000, tokenizer_hub="Xenova/gpt-4o"),
            LLMName.gpt_4o_mini: LLMConfig(context=128000, tokenizer_hub="Xenova/gpt-4o"),
            LLMName.gpt_4_turbo: LLMConfig(context=128000, tokenizer_hub="Xenova/gpt-4"),
            LLMName.gpt_4: LLMConfig(context=8192, tokenizer_hub="Xenova/gpt-4"),
            LLMName.gpt_35_turbo: LLMConfig(
                context=16385, tokenizer_hub="Xenova/gpt-3.5-turbo"
            ),
            LLMName.text_embedding_3_large: LLMConfig(
                context=8191, tokenizer_hub="Xenova/text-embedding-ada-002"
            ),
            LLMName.text_embedding_3_small: LLMConfig(
                context=8191, tokenizer_hub="Xenova/text-embedding-ada-002"
            ),
            LLMName.text_embedding_ada_002: LLMConfig(
                context=8191, tokenizer_hub="Xenova/text-embedding-ada-002"
            ),
        },
        DefaultModelSuppliers.ANTHROPIC: {
            LLMName.claude_3_5_sonnet: LLMConfig(
                context=200000, tokenizer_hub="Xenova/claude-tokenizer"
            ),
            LLMName.claude_3_opus: LLMConfig(
                context=200000, tokenizer_hub="Xenova/claude-tokenizer"
            ),
            LLMName.claude_3_sonnet: LLMConfig(
                context=200000, tokenizer_hub="Xenova/claude-tokenizer"
            ),
            LLMName.claude_3_haiku: LLMConfig(
                context=200000, tokenizer_hub="Xenova/claude-tokenizer"
            ),
            LLMName.claude_2_1: LLMConfig(
                context=200000, tokenizer_hub="Xenova/claude-tokenizer"
            ),
            LLMName.claude_2_0: LLMConfig(
                context=100000, tokenizer_hub="Xenova/claude-tokenizer"
            ),
            LLMName.claude_instant_1_2: LLMConfig(
                context=100000, tokenizer_hub="Xenova/claude-tokenizer"
            ),
        },
        DefaultModelSuppliers.META: {
            LLMName.llama3_2_vision_11b: LLMConfig(
                context=128000, tokenizer_hub="Xenova/Meta-Llama-3.1-Tokenizer", supports_func_calling=False
            ),
            LLMName.llama_3_1_8b: LLMConfig(
                context=128000, tokenizer_hub="Xenova/Meta-Llama-3.1-Tokenizer"
            ),
            LLMName.llama_3_1_70b: LLMConfig(
                context=128000, tokenizer_hub="Xenova/Meta-Llama-3.1-Tokenizer"
            ),
            LLMName.llama_3: LLMConfig(
                context=8192, tokenizer_hub="Xenova/llama3-tokenizer-new"
            ),
            LLMName.llama_2: LLMConfig(context=4096, tokenizer_hub="Xenova/llama2-tokenizer", supports_func_calling=False),
            LLMName.code_llama: LLMConfig(
                context=16384, tokenizer_hub="Xenova/llama-code-tokenizer"
            ),
        },
        DefaultModelSuppliers.MISTRAL: {
            LLMName.mistral_large: LLMConfig(
                context=128000, tokenizer_hub="Xenova/mistral-tokenizer-v3"
            ),
            LLMName.mistral_small: LLMConfig(
                context=128000, tokenizer_hub="Xenova/mistral-tokenizer-v3"
            ),
            LLMName.mistral_7b: LLMConfig(
                context=128000, tokenizer_hub="Xenova/mistral-tokenizer-v3"
            ),
            LLMName.mistral_nemo: LLMConfig(
                context=128000, tokenizer_hub="Xenova/Mistral-Nemo-Instruct-Tokenizer"
            ),
            LLMName.codestral: LLMConfig(
                context=32000, tokenizer_hub="Xenova/mistral-tokenizer-v3"
            ),
        },
        DefaultModelSuppliers.ALIBABA: {
            LLMName.qwq: LLMConfig(
                context=32000, tokenizer_hub=""
            ),
            LLMName.qwen_32b: LLMConfig(
                context=32000, tokenizer_hub=""
            ),
        },
    }

    @classmethod
    def get_supplier_by_model_name(cls, model: str) -> DefaultModelSuppliers | None:
        for supplier, models in cls._model_defaults.items():
            for base_model_name in models:
                if model.startswith(base_model_name):
                    return supplier
        return None

    @classmethod
    def get_llm_model_config(
            cls, supplier: DefaultModelSuppliers, model_name: str
    ) -> Optional[LLMConfig]:
        """指定されたサプライヤーとモデルの LLMConfig（context と tokenizer_hub）を取得します。"""
        supplier_defaults = cls._model_defaults.get(supplier)
        if not supplier_defaults:
            return None

        for key, config in supplier_defaults.items():
            if model_name.startswith(key):
                return config
        return None

class LLMEndpointConfig(AIBaseConfig):
    supplier: DefaultModelSuppliers = DefaultModelSuppliers.MISTRAL
    model: str = DEFAULT_LLM_NAME
    context_length: int | None = None
    tokenizer_hub: str | None = None
    llm_base_url: str | None = None
    env_variable_name: str | None = None
    llm_api_key: str | None = None
    max_context_tokens: int = 8000
    max_output_tokens: int = 8000
    temperature: float = 0.7
    streaming: bool = True
    prompt: CustomPromptsModel | None = None
    supports_func_calling: bool = True

    _FALLBACK_TOKENIZER = "cl100k_base"

    @property
    def fallback_tokenizer(self) -> str:
        return self._FALLBACK_TOKENIZER

    def __init__(self, **data):
        super().__init__(**data)
        self.set_llm_model_config()
        self.set_api_key()

    def set_api_key(self, force_reset: bool = False):
        if not self.supplier:
            return

        if not self.env_variable_name:
            self.env_variable_name = (
                f"{normalize_to_env_variable_name(self.supplier)}_API_KEY"
            )

        if not self.llm_api_key and force_reset:
            self.llm_api_key = os.getenv(self.env_variable_name)
            if not self.llm_api_key:
                logger.warning(f"The API key for supplier '{self.supplier}' is not set. ")

    def set_llm_model_config(self):
        llm_model_config = LLMModelConfig.get_llm_model_config(
            self.supplier, self.model
        )
        if llm_model_config:
            self.context_length = llm_model_config.context
            self.tokenizer_hub = llm_model_config.tokenizer_hub
            self.supports_func_calling = llm_model_config.supports_func_calling

    def set_llm_model(self, model: str, force_reset: bool = False):
        supplier = LLMModelConfig.get_supplier_by_model_name(model)
        if supplier is None:
            raise ValueError(
                f"Cannot find the corresponding supplier for model {model}"
            )
        self.supplier = supplier
        self.model = model

        self.set_llm_model_config()
        self.set_api_key(force_reset=force_reset)