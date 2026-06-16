"""
Database connection setup (SQLAlchemy).

Three things live here:
  1. `engine`      — the actual connection pool to Postgres.
  2. `SessionLocal`— a factory that hands out short-lived DB sessions.
  3. `Base`        — the base class all our table models inherit from.
  4. `get_db()`    — a FastAPI dependency that gives each request its own
                     session and closes it afterward.

Mental model: the `engine` is the pipe to the database; a `Session` is one
conversation over that pipe for a single request. You open a session, do your
reads/writes, commit, and close. `get_db()` automates that lifecycle per request.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# The engine manages a pool of connections to Postgres. Created once, reused.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# A configured "session factory". Calling SessionLocal() gives a new Session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """All ORM table models inherit from this. Alembic also uses it to know
    what tables should exist (Base.metadata)."""

    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency. Usage in an endpoint:

        @router.get("/datasets")
        def list_datasets(db: Session = Depends(get_db)):
            ...

    The `yield` hands the session to the endpoint; the `finally` guarantees it's
    closed even if the endpoint raises. This is the standard FastAPI + SQLAlchemy
    pattern — one session per request, always cleaned up.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
