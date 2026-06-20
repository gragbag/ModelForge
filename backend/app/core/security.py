"""
Security primitives: password hashing (bcrypt) and JWT tokens (pyjwt).

These are the crypto building blocks. They're provided complete because security
bugs here are dangerous — your learning TODOs are in how the ENDPOINTS use them
(api/auth.py) and the get_current_user gatekeeper (core/deps.py).
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


# --- Password hashing -------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt (includes a random salt)."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


# --- JWT tokens -------------------------------------------------------------
def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    """Build a signed JWT. `subject` is who the token is for (the user id);
    `token_type` distinguishes access vs refresh tokens."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,            # "subject" — standard JWT claim for the user id
        "type": token_type,        # "access" or "refresh"
        "iat": now,                # issued-at
        "exp": now + expires_delta,  # expiry — pyjwt rejects the token after this
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int) -> str:
    """Short-lived token sent on every request (expires in ~1 hour)."""
    return _create_token(
        str(user_id), "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: int) -> str:
    """Long-lived token used ONLY to get a new access token (expires in ~7 days)."""
    return _create_token(
        str(user_id), "refresh",
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Verify a token's signature + expiry and return its payload.
    Raises jwt.PyJWTError (e.g. ExpiredSignatureError, InvalidTokenError) if the
    token is invalid/expired — callers turn that into a 401."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
