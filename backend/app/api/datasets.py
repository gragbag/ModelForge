"""
Dataset endpoints: upload a dataset and list datasets.

A dataset is either:
  - tabular: a .csv  -> parsed with pandas (row_count / column_count)
  - image:   a .zip  -> images in a folder-per-class layout (cats/…, dogs/…),
             where the folder name is the label (the torchvision ImageFolder
             convention). We record the classes + image count.

Flow for POST /datasets: receive the file -> inspect it -> upload to S3 ->
insert a row -> return it. Touches all three layers: API + S3 + database.
"""

import io
import json

import pandas as pd
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.dataset import (
    MODALITY_IMAGE,
    MODALITY_TABULAR,
    STATUS_READY,
    STATUS_VALIDATING,
    Dataset,
)
from app.models.user import Role, User
from app.schemas.dataset import DatasetRead
from app.services import image_data, storage
from app.services.tasks import validate_dataset_task

# A router groups related endpoints. We include it into the app in main.py.
# `prefix="/datasets"` means every route here starts with /datasets.
router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetRead, status_code=201)
def upload_dataset(
    file: UploadFile,
    name: str = Form(...),
    modality: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <-- requires a valid token
) -> Dataset:
    """Upload a dataset. The user picks a unique `name`, the `modality`
    (tabular/image), an optional `description`, and the matching file — a `.csv`
    for tabular or a folder-per-class `.zip` for image."""
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="A dataset name is required")
    if modality not in (MODALITY_TABULAR, MODALITY_IMAGE):
        raise HTTPException(status_code=400, detail="modality must be tabular or image")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Names are unique per user (fail early with a clear message; the DB
    # constraint is the backstop).
    exists = (
        db.execute(
            select(Dataset).where(
                Dataset.owner_id == current_user.id, Dataset.name == name
            )
        )
        .scalars()
        .first()
    )
    if exists is not None:
        raise HTTPException(
            status_code=409, detail=f"You already have a dataset named {name!r}"
        )

    # Read the whole file into memory. (Fine for the modest files we expect; a
    # production system would stream large uploads straight to S3.)
    raw_bytes = file.file.read()
    fname = file.filename.lower()

    # Validate the file matches the chosen modality, and derive metadata. Tabular
    # is parsed synchronously (immediately "ready"); image zips get a cheap
    # structural check now, with full per-image validation in a background task.
    row_count: int | None = None
    column_count: int | None = None
    meta: dict | None = None
    if modality == MODALITY_TABULAR:
        if not fname.endswith(".csv"):
            raise HTTPException(
                status_code=400, detail="A tabular dataset must be a .csv file"
            )
        status = STATUS_READY
        try:
            df = pd.read_csv(io.BytesIO(raw_bytes))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")
        row_count, column_count = df.shape[0], df.shape[1]
    else:  # image
        if not fname.endswith(".zip"):
            raise HTTPException(
                status_code=400,
                detail="An image dataset must be a .zip of folder-per-class images",
            )
        status = STATUS_VALIDATING
        try:
            meta = image_data.inspect_structure(raw_bytes)  # cheap, no decoding
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Insert the row first so Postgres assigns the auto-increment id, then key
    # the S3 object by that id — unique per dataset, and consistent with the
    # models/{job.id}/... convention. flush() gets the id without committing; if
    # the upload then fails, the transaction rolls back (no orphan row).
    dataset = Dataset(
        name=name,
        description=description.strip() or None,
        filename=file.filename,
        s3_key="",  # set below, once we have the id
        size_bytes=len(raw_bytes),
        row_count=row_count,
        column_count=column_count,
        modality=modality,
        meta=meta,
        status=status,
        owner_id=current_user.id,
    )
    db.add(dataset)
    try:
        db.flush()  # assigns dataset.id (and enforces the unique-name constraint)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail=f"You already have a dataset named {name!r}"
        )

    dataset.s3_key = f"uploads/{dataset.id}/{file.filename}"
    storage.upload_fileobj(raw_bytes, settings.s3_bucket_datasets, dataset.s3_key)

    db.commit()
    db.refresh(dataset)   # reload so created_at is populated

    # Kick off async content validation for image datasets (validating -> ready/failed).
    if dataset.modality == MODALITY_IMAGE:
        validate_dataset_task.delay(dataset.id)

    return dataset


@router.get("", response_model=list[DatasetRead])
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <-- requires a valid token
) -> list[Dataset]:
    """List datasets. Regular users see only their own; admins see all."""
    stmt = select(Dataset).order_by(Dataset.created_at.desc())
    if current_user.role != Role.ADMIN:
        stmt = stmt.where(Dataset.owner_id == current_user.id)

    result = db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{dataset_id}/preview")
def preview_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Preview a dataset. Tabular -> column names + first 5 rows; image -> its
    classes + image count (from stored metadata, no download needed)."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or (
        dataset.owner_id != current_user.id and current_user.role != Role.ADMIN
    ):
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Image datasets: serve the metadata we recorded at upload time.
    if dataset.modality == MODALITY_IMAGE:
        return {"modality": MODALITY_IMAGE, **(dataset.meta or {})}

    try:
        raw = storage.download_fileobj(settings.s3_bucket_datasets, dataset.s3_key)
    except ClientError as exc:
        # The metadata row exists but the file is gone from object storage
        # (e.g. LocalStack was reset). Return a clear 410 instead of a 500.
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NoSuchBucket"):
            raise HTTPException(
                status_code=410,
                detail="Dataset file is no longer available (object storage was "
                "reset). Please re-upload this dataset.",
            )
        raise
    df = pd.read_csv(io.BytesIO(raw), nrows=5)
    # df.to_json handles NaN -> null and numpy types -> native, so the result is
    # always valid JSON; json.loads turns it back into Python objects to return.
    return {
        "modality": MODALITY_TABULAR,
        "columns": list(df.columns),
        "rows": json.loads(df.to_json(orient="records")),
    }


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a dataset you own (admins can delete any)."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or (
        dataset.owner_id != current_user.id and current_user.role != Role.ADMIN
    ):
        raise HTTPException(status_code=404, detail="Dataset not found")

    db.delete(dataset)
    try:
        db.commit()
    except IntegrityError:
        # A job still references this dataset (foreign key) — block the delete.
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: this dataset has training jobs. Delete those first.",
        )
