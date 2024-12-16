from enum import Enum


class EmbedderType(str, Enum):
    OllamaEmbeddings = "OllamaEmbeddings"


def default_embedder_type() -> EmbedderType:
    return EmbedderType.OllamaEmbeddings
