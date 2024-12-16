import logging
import os
import tiktoken

from transformers import AutoTokenizer
from dataclasses import dataclass
from typing import Union
from urllib.parse import parse_qs, urlparse
from pydantic.v1 import SecretStr
from rich.tree import Tree

from langchain_core.language_models import BaseChatModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

from core.ai_core.llm.llm_callbacks import AgentCallbackHandler
from core.ai_core.llm.llm_config import (
    LLMEndpointConfig,
    DefaultModelSuppliers,
    DEFAULT_LLM_NAME,
)

logger = logging.getLogger("ai_core")


@dataclass
class LLMInfo:
    model: str
    llm_base_url: str | None
    temperature: float
    max_tokens: int
    supports_function_calling: int

    def add_to_tree(self, llm_tree: Tree):
        llm_tree.add(f"Model: [italic]{self.model}[/italic]")
        llm_tree.add(f"Base URL: [underline]{self.llm_base_url}[/underline]")
        llm_tree.add(f"Temperature: [bold]{self.temperature}[/bold]")
        llm_tree.add(f"Max Tokens: [bold]{self.max_tokens}[/bold]")
        func_call_color = "green" if self.supports_function_calling else "red"
        llm_tree.add(
            f"Supports Function Calling: [bold {func_call_color}]{self.supports_function_calling}[/bold {func_call_color}]"
        )


class LLMEndpoint:
    def __init__(self, llm_config: LLMEndpointConfig, llm: BaseChatModel):
        self._config = llm_config
        self._llm = llm
        self._supports_func_calling = llm_config.supports_func_calling

        if llm_config.tokenizer_hub:
            # huggingface/tokenizers: 現在のプロセスがフォークされましたが、既に並列処理が使用されています。デッドロックを回避するために並列処理を無効にしています...
            os.environ["TOKENIZERS_PARALLELISM"] = (
                "false"
                if not os.environ.get("TOKENIZERS_PARALLELISM")
                else os.environ["TOKENIZERS_PARALLELISM"]
            )
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(llm_config.tokenizer_hub)
            except (
                OSError
            ):  # Hugging Face に接続できない場合、またはキャッシュされたモデルが存在しない場合
                logger.warning(
                    f"Cannot access the configured tokenizer from {llm_config.tokenizer_hub}, using the default tokenizer {llm_config.fallback_tokenizer}"
                )
                self.tokenizer = tiktoken.get_encoding(llm_config.fallback_tokenizer)
        else:
            self.tokenizer = tiktoken.get_encoding(llm_config.fallback_tokenizer)

    @classmethod
    def from_config(cls, config: LLMEndpointConfig = LLMEndpointConfig()):
        _llm: Union[AzureChatOpenAI, ChatOpenAI, ChatAnthropic, ChatOllama]
        try:
            if config.supplier == DefaultModelSuppliers.AZURE:
                # Parse the URL
                parsed_url = urlparse(config.llm_base_url)
                deployment = parsed_url.path.split("/")[3]
                api_version = parse_qs(parsed_url.query).get("api-version", [None])[0]
                azure_endpoint = f"https://{parsed_url.netloc}"
                _llm = AzureChatOpenAI(
                    azure_deployment=deployment,
                    api_version=api_version,
                    api_key=(
                        SecretStr(config.llm_api_key) if config.llm_api_key else None
                    ),
                    azure_endpoint=azure_endpoint,
                    max_tokens=config.max_output_tokens,
                    temperature=config.temperature,
                    callbacks=[AgentCallbackHandler()],
                )
            elif config.supplier == DefaultModelSuppliers.ANTHROPIC:
                _llm = ChatAnthropic(
                    model_name=config.model,
                    api_key=(
                        SecretStr(config.llm_api_key) if config.llm_api_key else None
                    ),
                    base_url=config.llm_base_url,
                    max_tokens=config.max_output_tokens,
                    temperature=config.temperature,
                    callbacks=[AgentCallbackHandler()],
                )
            elif config.supplier == DefaultModelSuppliers.OPENAI:
                _llm = ChatOpenAI(
                    model=config.model,
                    api_key=(
                        SecretStr(config.llm_api_key) if config.llm_api_key else None
                    ),
                    base_url=config.llm_base_url,
                    max_tokens=config.max_output_tokens,
                    temperature=config.temperature,
                    callbacks=[AgentCallbackHandler()],
                )
            else:
                _llm = ChatOllama(
                    model=config.model,
                    num_ctx=config.context_length,
                    temperature=config.temperature,
                    callbacks=[AgentCallbackHandler()],
                )
            return cls(llm=_llm, llm_config=config)
        except ImportError as e:
            raise ImportError("Please provide a valid BaseLLM") from e

    def count_tokens(self, text: str) -> int:
        # 入力テキストをトークン化し、トークンの数を返します。
        encoding = self.tokenizer.encode(text)
        return len(encoding)

    def get_config(self):
        return self._config

    def supports_func_calling(self) -> bool:
        return self._supports_func_calling

    def info(self) -> LLMInfo:
        return LLMInfo(
            model=self._config.model,
            llm_base_url=self._config.llm_base_url,
            temperature=self._config.temperature,
            max_tokens=self._config.max_output_tokens,
            supports_function_calling=self.supports_func_calling(),
        )

    @property
    def llm(self):
        return self._llm


def default_rag_llm() -> LLMEndpoint:
    try:
        logger.debug(
            f"Loaded {DEFAULT_LLM_NAME} as default LLM for knowledge warehouse"
        )
        llm = LLMEndpoint.from_config(
            LLMEndpointConfig(
                supplier=DefaultModelSuppliers.MISTRAL, model=DEFAULT_LLM_NAME
            )
        )
        return llm
    except ImportError as e:
        raise ImportError("Please provide a valid BaseLLM") from e
