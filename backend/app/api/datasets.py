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
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetRead
from app.services import storage

# A router groups related endpoints. We include it into the app in main.py.
# `prefix="/datasets"` means every route here starts with /datasets.
router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetRead, status_code=201)
def upload_dataset(file: UploadFile, db: Session = Depends(get_db)) -> Dataset:
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
            )
    db.add(dataset)       # stage the insert
    db.commit()           # actually write to Postgres
    db.refresh(dataset)   # reload so dataset.id / created_at are populated

    return dataset

    # ------------------------------------------------------------------
    # TODO(you): implement the upload flow. Steps, with hints:
    #
    # 1) Parse the CSV to count rows/columns.
    #    Hint: pandas can read bytes via an in-memory buffer:
    #        import io
    #        df = pd.read_csv(io.BytesIO(raw_bytes))
    #        row_count = df.shape[0]
    #        column_count = df.shape[1]
    #    Wrap this in try/except and raise HTTPException(400, ...) on a parse
    #    error, so a bad file returns a clean 400 instead of a 500.
    #
    # 2) Decide the S3 key (where the file lives in the bucket). A common
    #    pattern is to namespace by something unique. Since we don't have the
    #    dataset id yet (the DB assigns it on insert), a simple approach:
    #        s3_key = f"uploads/{file.filename}"
    #    (We can make this nicer later; uniqueness isn't critical for now.)
    #
    # 3) Upload the bytes to S3:
    #        storage.upload_fileobj(raw_bytes, settings.s3_bucket_datasets, s3_key)
    #
    # 4) Create the DB row and save it:
    #        dataset = Dataset(
    #            filename=file.filename,
    #            s3_key=s3_key,
    #            size_bytes=len(raw_bytes),
    #            row_count=row_count,
    #            column_count=column_count,
    #        )
    #        db.add(dataset)       # stage the insert
    #        db.commit()           # actually write to Postgres
    #        db.refresh(dataset)   # reload so dataset.id / created_at are populated
    #
    # 5) `return dataset` — FastAPI converts the SQLAlchemy object to a
    #    DatasetRead automatically (because of from_attributes=True).
    # ------------------------------------------------------------------
    raise HTTPException(status_code=501, detail="TODO(you): implement upload_dataset")


@router.get("", response_model=list[DatasetRead])
def list_datasets(db: Session = Depends(get_db)) -> list[Dataset]:
    """
    List all datasets. Built for you as a reference for how a DB read looks in
    SQLAlchemy 2.0: build a select() statement, execute it, get the objects.
    """
    result = db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    return list(result.scalars().all())
