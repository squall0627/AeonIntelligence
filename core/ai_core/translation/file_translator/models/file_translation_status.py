from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Status(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class FileTranslationStatus(BaseModel):
    task_id: str
    task_name: str
    status: Status
    progress: float = 0.0
    input_file_path: str
    output_file_path: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[str] = None
