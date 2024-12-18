import importlib
import types
from typing import Type, TypeAlias

from core.ai_core.translation.file_translator.file_translator_base import (
    FileTranslatorBase,
)
from core.ai_core.translation.file_translator.file_translator_type import (
    FileTranslatorType,
)
from core.utils.log_handler import rotating_file_logger

logger = rotating_file_logger("ai_core")

_registry: dict[str, Type[FileTranslatorBase]] = {}

registry = types.MappingProxyType(_registry)

FileTranslatorMapping: TypeAlias = dict[FileTranslatorType | str, str]

known_file_translators: FileTranslatorMapping = {
    FileTranslatorType.PPTX: "core.ai_core.translation.file_translator.impl.pptx_translator.PPTXTranslator",
}


def get_translator_class(
    file_translator_type: FileTranslatorType | str,
) -> type(FileTranslatorBase):
    if file_translator_type not in registry:
        if file_translator_type not in known_file_translators:
            raise ValueError(f"File translator type not known: {file_translator_type}")
        cls_mod = known_file_translators[file_translator_type]
        if cls_mod is not None:
            try:
                _registry[file_translator_type] = _import_class(cls_mod)
            except ImportError:
                logger.warn(
                    f"Falling to import File translator for {file_translator_type} : {cls_mod}"
                )
        else:
            raise ImportError(
                f"Can't find any File translator for {file_translator_type}"
            )

    cls = registry[file_translator_type]
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

    if not issubclass(mod, FileTranslatorBase):
        raise TypeError(f"{full_mod_path} is not a subclass of FileTranslatorBase ")

    return mod
