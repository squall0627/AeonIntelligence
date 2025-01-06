import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from api.db.database import get_db
from api.db.tables.user import User as UserModel

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class User(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    disabled: Optional[bool] = False


class UserInDB(User):
    hashed_password: str


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create access token using email as unique identifier instead of username
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    # Use email as the unique identifier in the token
    to_encode.update(
        {
            "exp": expire,
            "email": data.get("email"),  # Add email to token data
            "sub": data.get("sub"),  # Keep username for compatibility
        }
    )

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> bool:
    """
    Verify the JWT token's validity
    Returns True if token is valid, False otherwise
    """
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check if token has expired
        exp = payload.get("exp")
        if exp is None:
            return False

        # Convert exp to datetime
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        if datetime.now(timezone.utc) >= exp_datetime:
            return False

        # Check if both username and email exist in token
        username: str = payload.get("sub")
        email: str = payload.get("email")
        if username is None or email is None:
            return False

        return True

    except JWTError:
        return False


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """
    Get current user from token using email as primary identifier
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify and decode the token
        if not verify_token(token):
            raise credentials_exception

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception

        # Get user by email instead of username
        user = get_user_by_email(email=email, db=db)
        if user is None:
            raise credentials_exception

        return user

    except JWTError:
        raise credentials_exception


def authenticate_user(email: str, password: str, db: Session = Depends(get_db)):
    """
    Authenticate a user by email and password
    """
    # Try to find user by email
    user = get_user_by_email(email=email, db=db)

    if not user:
        return False

    if not verify_password(password, user.hashed_password):
        return False

    return user


def create_user(
    db: Session, username: str, email: str, password: str, full_name: str = None
):
    """
    Create a new user in the database
    Only email needs to be unique
    """
    # Check if email already exists
    existing_user = db.query(UserModel).filter(UserModel.email == email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(password)
    db_user = UserModel(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        is_active=True,
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating user")


def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """
    Retrieve user from database by email (unique identifier)
    """
    user = (
        db.query(UserModel)
        .filter(
            UserModel.email == email,
            UserModel.is_active == True,
        )
        .first()
    )

    if user:
        return UserInDB(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=not user.is_active,
            hashed_password=user.hashed_password,
        )
    return None
