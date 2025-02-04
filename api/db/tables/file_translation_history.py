from sqlalchemy import Column, String, func, Float, Integer, NVARCHAR

from api.db.database import Base
from sqlalchemy import DateTime


class FileTranslationHistory(Base):
    __tablename__ = "file_translation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), index=True, nullable=False)
    task_id = Column(NVARCHAR(255), unique=True, index=True, nullable=False)
    task_name = Column(NVARCHAR(255), nullable=False)
    date_time = Column(
        DateTime(timezone=True), nullable=False, default=func.current_timestamp()
    )
    source_file_name = Column(NVARCHAR(255), nullable=False)
    source_file_path = Column(NVARCHAR(255), nullable=False)
    translated_file_name = Column(NVARCHAR(255), nullable=True)
    translated_file_path = Column(NVARCHAR(255), nullable=True)
    status = Column(NVARCHAR(255), nullable=False)
    duration = Column(Float, nullable=False, default=0.0)
    error = Column(NVARCHAR(1000), nullable=True)
