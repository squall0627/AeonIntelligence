import logging
import types
import importlib

from typing import Type, TypeAlias
from core.ai_core.files.file import FileExtension
from core.ai_core.processor.processor_base import ProcessorBase

logger = logging.getLogger("ai_core")

_registry: dict[str, Type[ProcessorBase]] = {}

# 外部・読み取り専用。インポート済みで使用可能な実際のプロセッサを含みます。
registry = types.MappingProxyType(_registry)

ProcMapping: TypeAlias = dict[FileExtension | str, str]

known_processors: ProcMapping = {
    FileExtension.txt: "core.ai_core.processor.impl.default_processor.TikTokenTxtProcessor",
    FileExtension.pdf: "core.ai_core.processor.impl.default_processor.UnstructuredPDFProcessor",
    FileExtension.csv: "core.ai_core.processor.impl.default_processor.CSVProcessor",
    FileExtension.docx: "core.ai_core.processor.impl.default_processor.DOCXProcessor",
    FileExtension.doc: "core.ai_core.processor.impl.default_processor.DOCXProcessor",
    FileExtension.xlsx: "core.ai_core.processor.impl.default_processor.XLSXProcessor",
    FileExtension.xls: "core.ai_core.processor.impl.default_processor.XLSXProcessor",
    FileExtension.pptx: "core.ai_core.processor.impl.default_processor.PPTProcessor",
    FileExtension.markdown: "core.ai_core.processor.impl.default_processor.MarkdownProcessor",
    FileExtension.md: "core.ai_core.processor.impl.default_processor.MarkdownProcessor",
    FileExtension.mdx: "core.ai_core.processor.impl.default_processor.MarkdownProcessor",
    FileExtension.epub: "core.ai_core.processor.impl.default_processor.EpubProcessor",
    FileExtension.bib: "core.ai_core.processor.impl.default_processor.BibTexProcessor",
    FileExtension.odt: "core.ai_core.processor.impl.default_processor.ODTProcessor",
    FileExtension.html: "core.ai_core.processor.impl.default_processor.HTMLProcessor",
    FileExtension.py: "core.ai_core.processor.impl.default_processor.PythonProcessor",
    FileExtension.ipynb: "core.ai_core.processor.impl.default_processor.NotebookProcessor",
}

def get_processor_class(file_extension: FileExtension | str) -> Type[ProcessorBase]:
    if file_extension not in registry:
        if file_extension not in known_processors:
            raise ValueError(f"Extension not known: {file_extension}")
        cls_mod = known_processors[file_extension]
        if cls_mod is not None:
            try:
                _registry[file_extension] = _import_class(cls_mod)
            except ImportError:
                logger.warn(
                    f"Falling to import processor for {file_extension} : {cls_mod}"
                )
        else:
            raise ImportError(f"Can't find any processor for {file_extension}")

    cls = registry[file_extension]
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

    if not issubclass(mod, ProcessorBase):
        raise TypeError(f"{full_mod_path} is not a subclass of ProcessorBase ")

    return mod