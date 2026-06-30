"""
Deployment + prediction endpoints.

  POST /deployments                 -> "deploy" a registered model version
  GET  /deployments                 -> list your deployments
  POST /deployments/{id}/predict    -> get a prediction from that deployment

A deployment records which MLflow model version to serve; /predict loads that
model from the registry and runs inference on the feature values you send.
"""

import io
import json
import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

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
    # Detect the model's modality once, so the UI knows whether to offer the
    # tabular (rows/CSV) or image (upload) prediction interface.
    modality = (
        "image"
        if serving.is_image_model(payload.model_name, payload.model_version)
        else "tabular"
    )
    deployment = Deployment(
        model_name=payload.model_name,
        model_version=payload.model_version,
        modality=modality,
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


@router.get("/available-models")
def available_models(
    current_user: User = Depends(get_current_user),
) -> list[dict[str, str]]:
    """List all registered model versions available to deploy (from MLflow), so
    the UI can show meaningful names instead of asking the user to type one."""
    return serving.list_model_versions()


@router.delete("/registered-models", status_code=204)
def delete_registered_model(
    name: str,
    version: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a registered model version from the MLflow registry (clears stale
    models from the deploy list). Blocked if a deployment is still serving it."""
    in_use = (
        db.execute(
            select(Deployment).where(
                Deployment.model_name == name, Deployment.model_version == version
            )
        )
        .scalars()
        .first()
    )
    if in_use is not None:
        raise HTTPException(
            status_code=409,
            detail="This model is deployed — delete the deployment first.",
        )
    try:
        serving.delete_model_version(name, version)
    except Exception:
        logger.exception("Failed to delete model %s v%s", name, version)
        raise HTTPException(status_code=400, detail="Could not delete model")


@router.delete("/{deployment_id}", status_code=204)
def delete_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a deployment you own (admins can delete any)."""
    deployment = db.get(Deployment, deployment_id)
    if deployment is None or (
        deployment.owner_id != current_user.id and current_user.role != Role.ADMIN
    ):
        raise HTTPException(status_code=404, detail="Deployment not found")
    db.delete(deployment)
    db.commit()


def _owned_deployment(deployment_id, db, current_user) -> Deployment:
    """Fetch a deployment the user is allowed to use, or 404."""
    deployment = db.get(Deployment, deployment_id)
    if deployment is None or (
        deployment.owner_id != current_user.id and current_user.role != Role.ADMIN
    ):
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


def _predict_rows(deployment: Deployment, rows: list[dict]) -> list:
    """Load the deployment's model and predict on the given rows (shared by the
    JSON and CSV endpoints). Turns any failure into a clean 400."""
    try:
        model = serving.load_model(deployment.model_name, deployment.model_version)
        return serving.predict_batch(model, rows)
    except Exception:
        logger.exception("Prediction failed for deployment %s", deployment.id)
        raise HTTPException(
            status_code=400,
            detail="Prediction failed — check that your columns match the model's features.",
        )


@router.post("/{deployment_id}/predict", response_model=PredictResponse)
def predict(
    deployment_id: int,
    payload: PredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PredictResponse:
    """Batch inference from JSON rows. `rows` is a list of feature dicts."""
    deployment = _owned_deployment(deployment_id, db, current_user)
    if not payload.rows:
        raise HTTPException(status_code=400, detail="No rows provided")
    predictions = _predict_rows(deployment, payload.rows)
    return PredictResponse(rows=payload.rows, predictions=predictions)


@router.post("/{deployment_id}/predict-csv", response_model=PredictResponse)
def predict_csv(
    deployment_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PredictResponse:
    """Batch inference from an uploaded CSV. Each row is one prediction."""
    deployment = _owned_deployment(deployment_id, db, current_user)
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    try:
        df = pd.read_csv(io.BytesIO(file.file.read()))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    # to_json handles NaN/numpy types cleanly; round-trip to plain Python rows.
    rows = json.loads(df.to_json(orient="records"))
    predictions = _predict_rows(deployment, rows)
    return PredictResponse(rows=rows, predictions=predictions)


@router.post("/{deployment_id}/predict-image")
def predict_image(
    deployment_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Classify a single uploaded image with an image (CNN) deployment.
    Returns the predicted class + confidence."""
    deployment = _owned_deployment(deployment_id, db, current_user)

    if not serving.is_image_model(deployment.model_name, deployment.model_version):
        raise HTTPException(
            status_code=400, detail="This deployment does not serve an image model"
        )
    if not file.filename or not file.filename.lower().endswith(
        (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp")
    ):
        raise HTTPException(status_code=400, detail="Please upload an image file")

    data = file.file.read()
    try:
        return serving.predict_images(
            deployment.model_name, deployment.model_version, [data]
        )[0]
    except Exception:
        logger.exception("Image prediction failed for deployment %s", deployment.id)
        raise HTTPException(status_code=400, detail="Prediction failed on this image")
