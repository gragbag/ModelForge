"""
Pydantic schemas for auth: what register/login send and return.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import Role


class UserCreate(BaseModel):
    """Request body for POST /auth/register and /auth/login."""

    email: EmailStr   # EmailStr validates it's a real email format
    password: str


class UserRead(BaseModel):
    """Public view of a user — note: NO password/hash is ever exposed."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: Role
    created_at: datetime


class TokenPair(BaseModel):
    """What login/refresh return: an access token + a refresh token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Body for POST /auth/refresh — trade a refresh token for a new access token."""

    refresh_token: str
