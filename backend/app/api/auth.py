"""
Auth endpoints: register, login, refresh, and "who am I".

The flow:
  register -> creates a user (password stored as a bcrypt hash)
  login    -> verifies email+password, returns an access + refresh token pair
  refresh  -> trades a valid refresh token for a fresh access token
  /me      -> returns the current user (proves the token works)
"""

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenPair, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Create a new account. Stores a bcrypt HASH of the password, never plaintext."""
    # Reject duplicate emails.
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ------------------------------------------------------------------
    # TODO(you): create the user with a HASHED password, save, return it.
    #   user = User(
    #       email=payload.email,
    #       hashed_password=hash_password(payload.password),  # <-- never store plaintext
    #   )
    #   db.add(user); db.commit(); db.refresh(user)
    #   return user
    # ------------------------------------------------------------------
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: UserCreate, db: Session = Depends(get_db)) -> TokenPair:
    """Verify credentials and issue an access + refresh token pair."""
    auth_error = HTTPException(status_code=401, detail="Incorrect email or password")

    # ------------------------------------------------------------------
    # TODO(you): authenticate and mint tokens. Steps:
    #
    # 1) Look up the user by email:
    #        user = db.execute(
    #            select(User).where(User.email == payload.email)
    #        ).scalar_one_or_none()
    #
    # 2) Reject if no user OR the password doesn't match the stored hash.
    #    (Use one generic error for both — don't reveal which was wrong.)
    #        if user is None or not verify_password(payload.password, user.hashed_password):
    #            raise auth_error
    #
    # 3) Return a token pair:
    #        return TokenPair(
    #            access_token=create_access_token(user.id),
    #            refresh_token=create_refresh_token(user.id),
    #        )
    # ------------------------------------------------------------------
    user = db.execute(
        select(User).where(User.email == payload.email)
    ).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise auth_error

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    """Trade a valid REFRESH token for a new access token (and a new refresh token).
    This is built for you as a reference — it mirrors the login token-minting but
    validates a refresh token instead of a password."""
    invalid = HTTPException(status_code=401, detail="Invalid refresh token")
    try:
        decoded = decode_token(payload.refresh_token)
    except jwt.PyJWTError:
        raise invalid

    # Must be a REFRESH token (not an access token reused here).
    if decoded.get("type") != "refresh":
        raise invalid

    user_id = decoded.get("sub")
    user = db.get(User, int(user_id)) if user_id is not None else None
    if user is None:
        raise invalid

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently-authenticated user. Requires a valid access token —
    a quick way to test that auth works end to end."""
    return current_user
