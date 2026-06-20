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
    """Input for a prediction: one row of feature values, e.g.
    {"features": {"hours_studied": 6, "prev_score": 72, "attendance": 85}}"""

    features: dict[str, Any]


class PredictResponse(BaseModel):
    prediction: Any
