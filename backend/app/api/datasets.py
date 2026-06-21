"""
Dataset endpoints: upload a CSV and list datasets.

Flow for POST /datasets:
    1. Receive the uploaded file
    2. Parse it with pandas -> row_count, column_count
    3. Upload the raw bytes to S3 (LocalStack)
    4. Insert a row into the `datasets` table
    5. Return the created dataset (as a DatasetRead schema)

This is the first endpoint that touches all three layers: API + S3 + database.
"""

import io
import json

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.dataset import Dataset
from app.models.user import Role, User
from app.schemas.dataset import DatasetRead
from app.services import storage

# A router groups related endpoints. We include it into the app in main.py.
# `prefix="/datasets"` means every route here starts with /datasets.
router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetRead, status_code=201)
def upload_dataset(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <-- requires a valid token
) -> Dataset:
    """
    Upload a CSV. `file: UploadFile` is how FastAPI receives an uploaded file.
    `db: Session = Depends(get_db)` injects a database session for this request.
    """
    # Basic validation — only accept CSVs for now.
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    # Read the whole file into memory as bytes. (Fine for the modest CSVs we
    # expect; a production system would stream large files.)
    raw_bytes = file.file.read()

    try:
        df = pd.read_csv(io.BytesIO(raw_bytes))
        row_count = df.shape[0]
        column_count = df.shape[1]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    s3_key = f"uploads/{file.filename}"
    storage.upload_fileobj(raw_bytes, settings.s3_bucket_datasets, s3_key)

    dataset = Dataset(
        filename=file.filename,
        s3_key=s3_key,
        size_bytes=len(raw_bytes),
        row_count=row_count,
        column_count=column_count,
        owner_id=current_user.id,
    )
    db.add(dataset)       # stage the insert
    db.commit()           # actually write to Postgres
    db.refresh(dataset)   # reload so dataset.id / created_at are populated

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
    """Return the column names + first 5 rows of a dataset's CSV (for the UI
    preview). Downloads only the first few rows from S3."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or (
        dataset.owner_id != current_user.id and current_user.role != Role.ADMIN
    ):
        raise HTTPException(status_code=404, detail="Dataset not found")

    raw = storage.download_fileobj(settings.s3_bucket_datasets, dataset.s3_key)
    df = pd.read_csv(io.BytesIO(raw), nrows=5)
    # df.to_json handles NaN -> null and numpy types -> native, so the result is
    # always valid JSON; json.loads turns it back into Python objects to return.
    return {
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
