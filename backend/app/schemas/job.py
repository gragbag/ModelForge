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

    # A human-friendly name for the resulting model (used as the registered
    # model name in MLflow). Retraining with the same name adds a new version.
    name: str
    dataset_id: int
    model_type: str
    # Tabular jobs require this; image jobs label by folder, so it's optional.
    target_column: str | None = None
    # The user declares the problem type. Pydantic will reject anything that
    # isn't "classification" or "regression" automatically (enum validation).
    task_type: TaskType
    # Optionally standardize features before training (StandardScaler).
    scale_features: bool = False
    # Model hyperparameters (e.g. {"n_neighbors": 7}); empty = model defaults.
    hyperparameters: dict = {}


class JobRead(BaseModel):
    """Response shape for a job. Reads straight from the Job DB object."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    status: JobStatus
    dataset_id: int
    model_type: str
    target_column: str | None
    task_type: TaskType
    scale_features: bool
    metrics: dict | None
    progress: dict | None
    model_s3_key: str | None
    error: str | None
    created_at: datetime
