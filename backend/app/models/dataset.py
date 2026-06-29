"""
The `datasets` table — one row per uploaded CSV/Parquet file.

Stores metadata about each upload; the file itself lives in S3 (see `s3_key`).
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Dataset modalities — what kind of data the file holds. This decides which
# training + serving pipeline runs downstream (tabular = scikit-learn,
# image/text = the deep-learning trainers).
MODALITY_TABULAR = "tabular"
MODALITY_IMAGE = "image"
MODALITY_TEXT = "text"

# Validation lifecycle. Tabular uploads are validated synchronously and go
# straight to "ready"; image uploads are content-validated by a background job,
# moving validating -> ready (usable) or failed (with an error).
STATUS_VALIDATING = "validating"
STATUS_READY = "ready"
STATUS_FAILED = "failed"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(nullable=False)
    s3_key: Mapped[str] = mapped_column(nullable=False)  # where the file lives in S3
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    # Tabular-only shape; null for image/text datasets.
    row_count: Mapped[int | None] = mapped_column(nullable=True)
    column_count: Mapped[int | None] = mapped_column(nullable=True)
    # What kind of data this is — picks the training/serving pipeline. Existing
    # rows default to tabular (the only modality before deep-learning support).
    modality: Mapped[str] = mapped_column(
        String, nullable=False, server_default=MODALITY_TABULAR, default=MODALITY_TABULAR
    )
    # Modality-specific metadata — e.g. image: {"classes": [...], "num_images": N};
    # null for tabular (row/column counts already describe it).
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Validation lifecycle (see statuses above). Existing rows default to ready.
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=STATUS_READY, default=STATUS_READY
    )
    # Why validation failed, if it did (shown in the UI).
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    # The user who uploaded this dataset.
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Auto-set on insert by Postgres.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} filename={getattr(self, 'filename', '?')!r}>"
