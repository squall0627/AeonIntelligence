import mimetypes
import warnings
import os
import aiofiles
import hashlib

from uuid import UUID, uuid4
from pathlib import Path
from enum import Enum
from typing import Any, Self
from anthropic import BaseModel


class FileExtension(str, Enum):
    txt = ".txt"
    pdf = ".pdf"
    csv = ".csv"
    doc = ".doc"
    docx = ".docx"
    pptx = ".pptx"
    xls = ".xls"
    xlsx = ".xlsx"
    md = ".md"
    mdx = ".mdx"
    markdown = ".markdown"
    bib = ".bib"
    epub = ".epub"
    html = ".html"
    odt = ".odt"
    py = ".py"
    ipynb = ".ipynb"
    m4a = ".m4a"
    mp3 = ".mp3"
    webm = ".webm"
    mp4 = ".mp4"
    mpga = ".mpga"
    wav = ".wav"
    mpeg = ".mpeg"

class AIFileSerialized(BaseModel):
    file_id: UUID
    original_filename: str
    path: Path
    file_sha1: str
    file_extension: FileExtension | str
    kw_id: UUID | None = None
    file_size: int | None = None
    additional_metadata: dict[str, Any] | None = None

def get_file_extension(file_path: Path) -> FileExtension | str:
    try:
        mime_type, _ = mimetypes.guess_type(file_path.name)
        if mime_type:
            mime_ext = mimetypes.guess_extension(mime_type)
            if mime_ext:
                return FileExtension(mime_ext)
        return FileExtension(file_path.suffix)
    except ValueError:
        warnings.warn(
            f"File {file_path.name} extension isn't recognized. Make sure you have registered a parser for {file_path.suffix}",
            stacklevel=2,
        )
        return file_path.suffix

async def load_aifile(kw_id: UUID, path: str | Path):
    if not isinstance(path, Path):
        path = Path(path)

    if not path.exists():
        raise FileExistsError(f"file {path} doesn't exist")

    file_size = os.stat(path).st_size

    async with aiofiles.open(path, mode="rb") as f:
        file_sha1 = hashlib.sha1(await f.read()).hexdigest()

    try:
        file_id = UUID(path.name)
    except ValueError:
        file_id = uuid4()

    return AIFile(
        file_id=file_id,
        kw_id=kw_id,
        path=path,
        original_filename=path.name,
        file_extension=get_file_extension(path),
        file_size=file_size,
        file_sha1=file_sha1,
    )

class AIFile:
    __slots__ = [
        "file_id",
        "kw_id",
        "path",
        "original_filename",
        "file_size",
        "file_extension",
        "file_sha1",
        "additional_metadata",
    ]

    def __init__(
            self,
            file_id: UUID,
            original_filename: str,
            path: Path,
            file_sha1: str,
            file_extension: FileExtension | str,
            kw_id: UUID | None = None,
            file_size: int | None = None,
            metadata: dict[str, Any] | None = None,
    ) -> None:
        self.file_id = file_id
        self.kw_id = kw_id
        self.path = path
        self.original_filename = original_filename
        self.file_size = file_size
        self.file_extension = file_extension
        self.file_sha1 = file_sha1
        self.additional_metadata = metadata if metadata else {}

    def __repr__(self) -> str:
        return f"AIFile-{self.file_id} original_filename:{self.original_filename}"

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "aifile_id": self.file_id,
            "aifile_path": self.path,
            "original_file_name": self.original_filename,
            "file_sha1": self.file_sha1,
            "file_size": self.file_size,
            **self.additional_metadata,
        }

    def serialize(self) -> AIFileSerialized:
        return AIFileSerialized(
            file_id=self.file_id,
            kw_id=self.kw_id,
            path=self.path.absolute(),
            original_filename=self.original_filename,
            file_size=self.file_size,
            file_extension=self.file_extension,
            file_sha1=self.file_sha1,
            additional_metadata=self.additional_metadata,
        )

    @classmethod
    def deserialize(cls, serialized: AIFileSerialized) -> Self:
        return cls(
            file_id=serialized.file_id,
            kw_id=serialized.kw_id,
            path=serialized.path,
            original_filename=serialized.original_filename,
            file_size=serialized.file_size,
            file_extension=serialized.file_extension,
            file_sha1=serialized.file_sha1,
            metadata=serialized.additional_metadata,
        )