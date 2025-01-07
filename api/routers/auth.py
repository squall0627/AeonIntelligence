from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from pydantic import EmailStr, BaseModel

from api.auth.oauth2 import (
    Token,
    User,
    create_access_token,
    authenticate_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_user,
    get_db,
    get_current_user,
    verify_token,
)
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/login_for_access_token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    authorization: str = Header(None),
):

    # Authenticate user and create new token
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check existing token if provided in header
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        if verify_token(token):
            return {"access_token": token, "token_type": "Bearer"}

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "email": user.email,
        },  # Include username and email in token data
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "Bearer"}


@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


# Define Pydantic model for request body validation
class RegisterUserRequest(BaseModel):
    email: EmailStr
    password: str
    username: str
    full_name: Optional[str] = None


@router.post("/register", response_model=User)
async def register_user(
    user: RegisterUserRequest,
    db: Session = Depends(get_db),
):
    return create_user(
        db, user.username, str(user.email), user.password, user.full_name
    )
