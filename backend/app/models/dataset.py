"""
The `datasets` table — one row per uploaded CSV/Parquet file.

Stores metadata about each upload; the file itself lives in S3 (see `s3_key`).
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(nullable=False)
    s3_key: Mapped[str] = mapped_column(nullable=False)  # where the file lives in S3
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    row_count: Mapped[int | None] = mapped_column(nullable=False)
    column_count: Mapped[int | None] = mapped_column(nullable=False)
    # The user who uploaded this dataset.
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Auto-set on insert by Postgres.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} filename={getattr(self, 'filename', '?')!r}>"
