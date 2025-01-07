import uuid

from sqlalchemy import Boolean, Column, String, NVARCHAR
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER

from api.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(NVARCHAR(255), nullable=False)
    full_name = Column(NVARCHAR(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
