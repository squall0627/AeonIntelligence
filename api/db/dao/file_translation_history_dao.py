from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from api.db.tables.file_translation_history import FileTranslationHistory
from core.utils.log_handler import rotating_file_logger

logger = rotating_file_logger("FileTranslationHistoryDao")


class FileTranslationHistoryDao:
    def __init__(self, db: Session):
        self.db = db

    async def insert(
        self,
        user_id: str,
        task_id: str,
        task_name: str,
        source_file_name: str,
        source_file_path: str,
        translated_file_name: Optional[str] = None,
        translated_file_path: Optional[str] = None,
        status: str = "PROCESSING",
        duration: float = 0.0,
        error: Optional[str] = None,
    ) -> FileTranslationHistory:
        """
        Insert a new file translation history record
        """
        try:
            history = FileTranslationHistory(
                user_id=user_id,
                task_id=task_id,
                task_name=task_name,
                source_file_name=source_file_name,
                source_file_path=source_file_path,
                translated_file_name=translated_file_name,
                translated_file_path=translated_file_path,
                status=status,
                duration=duration,
                error=error,
            )
            self.db.add(history)
            self.db.commit()
            self.db.refresh(history)
            return history
        except Exception as e:
            logger.error(f"Error inserting file translation history: {str(e)}")
            self.db.rollback()
            raise

    async def get_by_task_id(self, task_id: str) -> Optional[FileTranslationHistory]:
        """
        Get file translation history by task_id
        """
        try:
            query = select(FileTranslationHistory).where(
                FileTranslationHistory.task_id == task_id
            )
            result = self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting file translation history by task_id: {str(e)}")
            raise

    async def get_by_user_id(self, user_id: str) -> List[FileTranslationHistory]:
        """
        Get all file translation history for a user
        """
        try:
            query = (
                select(FileTranslationHistory)
                .where(FileTranslationHistory.user_id == user_id)
                .order_by(FileTranslationHistory.date_time.desc())
            )
            result = self.db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting file translation history by user_id: {str(e)}")
            raise

    async def update_status(
        self,
        task_id: str,
        status: str,
        translated_file_name: Optional[str] = None,
        translated_file_path: Optional[str] = None,
        duration: Optional[float] = None,
        error: Optional[str] = None,
    ) -> Optional[FileTranslationHistory]:
        """
        Update the status of a file translation history record
        """
        try:
            history = await self.get_by_task_id(task_id)
            if history:
                history.status = status
                if translated_file_name:
                    history.translated_file_name = translated_file_name
                if translated_file_path:
                    history.translated_file_path = translated_file_path
                if duration is not None:
                    history.duration = duration
                if error:
                    history.error = error
                self.db.commit()
                self.db.refresh(history)
            return history
        except Exception as e:
            logger.error(f"Error updating file translation history status: {str(e)}")
            self.db.rollback()
            raise
