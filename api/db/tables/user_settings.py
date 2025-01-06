from sqlalchemy import Boolean, Column, String

from api.db.database import Base


class UserSetting(Base):
    __tablename__ = "user_settings"

    user_id = Column(String(255), primary_key=True, nullable=False)
    dark_mode = Column(Boolean, default=False)
