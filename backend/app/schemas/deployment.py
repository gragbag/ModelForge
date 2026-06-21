"""
Pydantic schemas for deployments and prediction.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DeploymentCreate(BaseModel):
    """Request body for POST /deployments — deploy a registered model version."""

    model_name: str = "modelforge-model"   # the name models are registered under
    model_version: str                     # which version to serve, e.g. "1"


class DeploymentRead(BaseModel):
    """Response shape for a deployment."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    model_name: str
    model_version: str
    created_at: datetime


class PredictRequest(BaseModel):
    """Input for prediction: one or more rows of feature values, e.g.
    {"rows": [{"hours_studied": 6, "prev_score": 72, "attendance": 85}, ...]}"""

    rows: list[dict[str, Any]]


class PredictResponse(BaseModel):
    """The input rows paired with their predictions (same order)."""

    rows: list[dict[str, Any]]
    predictions: list[Any]
