"""
The `jobs` table — one row per training job.

A job ties together: which dataset to train on, what kind of model, which column
to predict, the current status, and (once finished) the resulting metrics and
where the trained model artifact was saved.

This is the second model for you to complete. Same column syntax as dataset.py.
Two new ideas appear here:

  1. A FOREIGN KEY — a job points at the dataset it trains on:
         dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))

  2. STORING JSON — the metrics (accuracy, rmse, etc.) vary per model, so we
     store them as a JSON blob rather than fixed columns:
         metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

The status uses a Python Enum so the allowed values are explicit and typo-proof.
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class JobStatus(str, enum.Enum):
    """The lifecycle of a training job (matches the spec's Phase 3 statuses)."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, enum.Enum):
    """What kind of ML problem this job is. The user specifies this; it decides
    which model and which metrics the worker uses."""

    CLASSIFICATION = "classification"  # predict a category  -> accuracy, f1, ...
    REGRESSION = "regression"          # predict a number    -> rmse, mae, r2


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Worked example — the status column with a default of QUEUED.
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.QUEUED, nullable=False
    )

    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    # The user who submitted this job (Wave 2 ownership).
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # User-given name for the model this job produces — used as the registered
    # model name in MLflow, so deployments can pick models by a meaningful name.
    name: Mapped[str | None] = mapped_column(nullable=True)
    model_type: Mapped[str] = mapped_column(nullable=False)
    # The column to predict — tabular only; image jobs label by folder, so null.
    target_column: Mapped[str | None] = mapped_column(nullable=True)
    # Whether to standardize features (StandardScaler) before training.
    scale_features: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    # User-set model hyperparameters (e.g. {"n_neighbors": 7}); empty = defaults.
    hyperparameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # NEW (Step 6): the user-specified problem type — classification or regression.
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType), nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # results, once trained
    model_s3_key: Mapped[str | None] = mapped_column(nullable=True)  # where the artifact is saved
    error: Mapped[str | None] = mapped_column(nullable=True)  # failure reason, if any
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} status={self.status.value}>"
