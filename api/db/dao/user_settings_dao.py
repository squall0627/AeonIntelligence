from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from api.db.tables.user_settings import UserSetting
from core.utils.log_handler import rotating_file_logger

logger = rotating_file_logger("UserSettingsDao")


class UserSettingsDao:
    def __init__(self, db: Session):
        self.db = db

    async def update_user_settings(self, user_id: str, **kwargs):
        """
        Update or create user settings using SQL Server MERGE statement.
        """
        try:
            # Convert kwargs to a list of column assignments
            set_clauses = ", ".join([f"{k} = :{k}" for k in kwargs])

            # Create MERGE statement
            merge_stmt = text(
                f"""
                MERGE INTO user_settings AS target
                USING (SELECT :user_id AS user_id) AS source
                ON target.user_id = source.user_id
                WHEN MATCHED THEN
                    UPDATE SET {set_clauses}
                WHEN NOT MATCHED THEN
                    INSERT (user_id, {', '.join(kwargs.keys())})
                    VALUES (:user_id, {', '.join([f':{k}' for k in kwargs])});
            """
            )

            # Execute the statement with parameters
            params = {"user_id": user_id, **kwargs}
            self.db.execute(merge_stmt, params)
            self.db.commit()

            # Return the updated settings
            return await self.get_user_settings(user_id)
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            self.db.rollback()
            raise e

    async def get_user_settings(self, user_id: str) -> Optional[dict[str, any]]:
        """
        Get all settings for a user.
        Returns None if no settings exist.
        """
        try:
            # Create select statement
            stmt = select(UserSetting).where(UserSetting.user_id == user_id)
            logger.debug(f">>> Select statement: {stmt}")

            # Execute query
            result = self.db.execute(stmt)
            settings = result.scalar_one_or_none()

            # If no settings exist, return None
            if settings is None:
                return None

            # Convert to dictionary
            return {"user_id": settings.user_id, "dark_mode": settings.dark_mode}
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            raise e
