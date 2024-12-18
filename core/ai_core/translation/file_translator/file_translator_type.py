from enum import Enum


class FileTranslatorType(str, Enum):
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    PDF = "pdf"
    CSV = "csv"
    XML = "xml"
    HTML = "html"
    ZIP = "zip"
    JPG = "jpg"
