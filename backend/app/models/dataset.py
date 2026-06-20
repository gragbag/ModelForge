"""
The `datasets` table — one row per uploaded CSV/Parquet file.

This is where you LEARN SQLAlchemy by writing the columns yourself. I've given
you the class, the first column as a worked example, and a TODO list of the rest
with the exact types to use. Fill in the TODO(you) section.

How a SQLAlchemy 2.0 column is declared:

    name: Mapped[<python type>] = mapped_column(<SQL options>)

  - `Mapped[str]`        -> a required text column
  - `Mapped[str | None]` -> a nullable text column
  - `Mapped[int]`        -> an integer column
  - mapped_column(primary_key=True)   -> primary key
  - mapped_column(index=True)         -> add an index (faster lookups)
  - mapped_column(nullable=False)     -> required (NOT NULL)

Reference docs: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    # Worked example — the primary key. Every table needs one.
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(nullable=False)
    s3_key: Mapped[str] = mapped_column(nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    row_count: Mapped[int | None] = mapped_column(nullable=False)
    column_count: Mapped[int | None] = mapped_column(nullable=False)
    # The user who uploaded this dataset (Wave 2 ownership).
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # ------------------------------------------------------------------
    # TODO(you): add the rest of the columns this dataset needs.
    # The spec (Phase 2) says we store this metadata about each upload:
    #
    #   filename       -> the original file name        (Mapped[str])
    #   s3_key         -> where the file lives in S3     (Mapped[str])
    #                     e.g. "datasets/3/data.csv"
    #   size_bytes     -> file size in bytes             (Mapped[int])
    #   row_count      -> number of rows                 (Mapped[int | None])
    #   column_count   -> number of columns              (Mapped[int | None])
    #
    # (row_count/column_count are nullable because we compute them after upload;
    #  they may be unknown for a moment.)
    #
    # Write them below, following the `id` example above.
    # ------------------------------------------------------------------

    # Worked example #2 — an auto-set timestamp. `server_default=func.now()`
    # tells Postgres to fill it in automatically when the row is created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} filename={getattr(self, 'filename', '?')!r}>"
