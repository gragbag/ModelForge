"""
Pydantic schemas for jobs.

Two schemas, because the data going IN is different from the data coming OUT:

  - JobCreate : what the user SENDS to POST /jobs (the request body).
                Only the few fields the user controls.
  - JobRead   : what the API RETURNS (the full job, including server-set fields
                like id, status, metrics).

This in/out split is standard: never let users set fields like `status` or
`metrics` directly — those are controlled by the server/worker.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.job import JobStatus, TaskType


class JobCreate(BaseModel):
    """Request body for POST /jobs. Pydantic validates these on the way in."""

    # Worked example — the dataset to train on.
    dataset_id: int
    model_type: str
    target_column: str
    # The user declares the problem type. Pydantic will reject anything that
    # isn't "classification" or "regression" automatically (enum validation).
    task_type: TaskType

    # ------------------------------------------------------------------
    # TODO(you): add the other two fields the user must provide:
    #   model_type: str       # e.g. "random_forest"
    #   target_column: str    # the column to predict
    # (Just type annotations — Pydantic handles validation.)
    # ------------------------------------------------------------------


class JobRead(BaseModel):
    """Response shape for a job. Reads straight from the Job DB object."""

    model_config = ConfigDict(from_attributes=True)

    # Worked example — the first two fields.
    id: int
    status: JobStatus
    dataset_id: int
    model_type: str
    target_column: str
    task_type: TaskType
    metrics: dict | None
    model_s3_key: str | None
    error: str | None
    created_at: datetime

    # ------------------------------------------------------------------
    # TODO(you): add the remaining fields you want to expose:
    #   dataset_id: int
    #   model_type: str
    #   target_column: str
    #   metrics: dict | None
    #   model_s3_key: str | None
    #   error: str | None
    #   created_at: datetime
    # ------------------------------------------------------------------
