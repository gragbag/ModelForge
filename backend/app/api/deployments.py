"""
Deployment + prediction endpoints.

  POST /deployments                 -> "deploy" a registered model version
  GET  /deployments                 -> list your deployments
  POST /deployments/{id}/predict    -> get a prediction from that deployment

A deployment records which MLflow model version to serve; /predict loads that
model from the registry and runs inference on the feature values you send.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.deployment import Deployment
from app.models.user import Role, User
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentRead,
    PredictRequest,
    PredictResponse,
)
from app.services import serving

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post("", response_model=DeploymentRead, status_code=201)
def create_deployment(
    payload: DeploymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Deployment:
    """Deploy a registered model version (records it; serves it at /predict)."""
    deployment = Deployment(
        model_name=payload.model_name,
        model_version=payload.model_version,
        owner_id=current_user.id,
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    return deployment


@router.get("", response_model=list[DeploymentRead])
def list_deployments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Deployment]:
    """List deployments — your own, or all if you're an admin."""
    stmt = select(Deployment).order_by(Deployment.created_at.desc())
    if current_user.role != Role.ADMIN:
        stmt = stmt.where(Deployment.owner_id == current_user.id)
    return list(db.execute(stmt).scalars().all())


@router.post("/{deployment_id}/predict", response_model=PredictResponse)
def predict(
    deployment_id: int,
    payload: PredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PredictResponse:
    """Run inference: load the deployment's model and predict on the input row."""
    deployment = db.get(Deployment, deployment_id)
    if deployment is None or (
        deployment.owner_id != current_user.id and current_user.role != Role.ADMIN
    ):
        raise HTTPException(status_code=404, detail="Deployment not found")

    try:
        model = serving.load_model(deployment.model_name, deployment.model_version)
        print(model)

        prediction = serving.predict_one(model, payload.features)
    except Exception:
        logger.exception("Prediction failed for deployment %s", deployment_id)  # full detail in logs
        raise HTTPException(status_code=400, detail="Prediction failed — check your feature values")

    return PredictResponse(prediction=prediction)
