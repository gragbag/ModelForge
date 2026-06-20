"""
Auth dependencies — the gatekeepers you attach to protected endpoints.

`get_current_user` reads the JWT from the request, verifies it, and loads the
user. Any endpoint with `Depends(get_current_user)` becomes login-only.
`require_admin` builds on it to enforce the admin role (Wave 2).
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import Role, User

# Tells FastAPI to look for a "Authorization: Bearer <token>" header, and powers
# the "Authorize" button in the /docs UI. tokenUrl points at the login endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Verify the access token and return the logged-in User. Raises 401 if the
    token is missing/invalid/expired, or the user no longer exists."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise credentials_error

    if payload.get("type") != "access":
        raise credentials_error
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error
    
    user = db.get(User, int(user_id))
    if user is None:
        raise credentials_error

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency that only allows admins through (used in Wave 2). It depends on
    get_current_user, so it both authenticates AND checks the role."""
    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user
