import logging
import importlib
import types

from typing import Type, TypeAlias

from core.ai_core.embedder.embedder_base import EmbedderBase
from core.ai_core.embedder.embedder_config import EmbedderType

logger = logging.getLogger("ai_core")

_registry: dict[str, Type[EmbedderBase]] = {}

registry = types.MappingProxyType(_registry)

EmbedderMapping: TypeAlias = dict[EmbedderType | str, str]

known_embedders: EmbedderMapping = {
    EmbedderType.OllamaEmbeddings: "core.ai_core.embedder.impl.ollama_embeddings.OllamaEmbedder",
}

def get_embedder_class(embedder_type: EmbedderType | str) -> Type[EmbedderBase]:
    if embedder_type not in registry:
        if embedder_type not in known_embedders:
            raise ValueError(f"Embedder type not known: {embedder_type}")
        cls_mod = known_embedders[embedder_type]
        if cls_mod is not None:
            try:
                _registry[embedder_type] = _import_class(cls_mod)
            except ImportError:
                logger.warn(
                    f"Falling to import embedder for {embedder_type} : {cls_mod}"
                )
        else:
            raise ImportError(f"Can't find any embedder for {embedder_type}")

    cls = registry[embedder_type]
    return cls

def _import_class(full_mod_path: str):
    if ":" in full_mod_path:
        mod_name, name = full_mod_path.rsplit(":", 1)
    else:
        mod_name, name = full_mod_path.rsplit(".", 1)

    mod = importlib.import_module(mod_name)

    for cls in name.split("."):
        mod = getattr(mod, cls)

    if not isinstance(mod, type):
        raise TypeError(f"{full_mod_path} is not a class")

    if not issubclass(mod, EmbedderBase):
        raise TypeError(f"{full_mod_path} is not a subclass of EmbedderBase ")

    return mod