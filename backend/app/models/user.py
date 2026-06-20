"""
The `users` table — one row per account.

We store the password as a bcrypt HASH, never the plaintext (see core/security.py).
The `role` enum drives authorization (admin vs regular user) in Wave 2.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Role(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # email is the login identifier — unique + indexed for fast lookup.
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    # The bcrypt hash of the password. NEVER the plaintext.
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.USER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"
