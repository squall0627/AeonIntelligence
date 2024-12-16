import logging
import importlib
import types
from typing import Type, TypeAlias

from core.ai_core.vectordb.vectordb_base import VectordbBase
from core.ai_core.vectordb.vectordb_config import VectordbType

logger = logging.getLogger("ai_core")

_registry: dict[str, Type[VectordbBase]] = {}

registry = types.MappingProxyType(_registry)

VectordbMapping: TypeAlias = dict[VectordbType | str, str]

known_vectordbs: VectordbMapping = {
    VectordbType.FaissCPU: "core.ai_core.vectordb.impl.faiss_cpu.FaissCpu",
    VectordbType.FaissGPU: "core.ai_core.vectordb.impl.faiss_gpu.FaissGpu",
}


def get_vectordb_class(vectordb_type: VectordbType | str) -> Type[VectordbBase]:
    if vectordb_type not in registry:
        if vectordb_type not in known_vectordbs:
            raise ValueError(f"Vectordb type not known: {vectordb_type}")
        cls_mod = known_vectordbs[vectordb_type]
        if cls_mod is not None:
            try:
                _registry[vectordb_type] = _import_class(cls_mod)
            except ImportError:
                logger.warn(
                    f"Falling to import vectordb for {vectordb_type} : {cls_mod}"
                )
        else:
            raise ImportError(f"Can't find any vectordb for {vectordb_type}")

    cls = registry[vectordb_type]
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

    if not issubclass(mod, VectordbBase):
        raise TypeError(f"{full_mod_path} is not a subclass of VectordbBase ")

    return mod
