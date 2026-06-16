"""
Celery tasks — the functions that run inside the WORKER process (not the API).

Step 6: this now does REAL training. The task is the "orchestrator" — it does
the plumbing (load job, download data, save model, update DB) and delegates the
actual ML to the pure functions in services/training.py.

Flow:
    QUEUED -> RUNNING -> [download CSV -> train -> upload model] -> COMPLETED
                                                                 \-> FAILED (on error)
"""

import io

import joblib
import pandas as pd

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.dataset import Dataset
from app.models.job import Job, JobStatus
from app.services import storage, training


@celery_app.task(name="train_model")
def train_model_task(job_id: int) -> None:
    """Train a model for the given job id, in the background worker."""
    db = SessionLocal()
    job = None
    try:
        job = db.get(Job, job_id)
        if job is None:
            return  # job was deleted before the worker got to it

        # Mark RUNNING so GET /jobs/{id} reflects progress.
        job.status = JobStatus.RUNNING
        db.commit()

        # Look up the dataset this job trains on (we need its S3 key).
        dataset = db.get(Dataset, job.dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset {job.dataset_id} not found")
        
        raw = storage.download_fileobj(settings.s3_bucket_datasets, dataset.s3_key)
        df = pd.read_csv(io.BytesIO(raw))

        # ------------------------------------------------------------------
        # TODO(you): download the CSV from S3 and load it into a DataFrame.
        #
        # 1) Download the raw bytes from the datasets bucket:
        #        raw = storage.download_fileobj(settings.s3_bucket_datasets, dataset.s3_key)
        #
        # 2) Load into pandas (same trick as the upload endpoint):
        #        df = pd.read_csv(io.BytesIO(raw))
        # ------------------------------------------------------------------

        # --- Train (delegates to the pure ML service) ---------------------
        model, metrics = training.train_and_evaluate(
            df=df,
            target_column=job.target_column,
            task_type=job.task_type,
            model_type=job.model_type,
        )

        # ------------------------------------------------------------------
        # TODO(you): serialize the trained model and upload it to S3.
        #
        # 1) joblib serializes a model to bytes via a buffer:
        #        buffer = io.BytesIO()
        #        joblib.dump(model, buffer)
        #
        # 2) Pick a key and upload to the MODELS bucket:
        #        model_key = f"models/{job.id}/model.joblib"
        #        storage.upload_fileobj(buffer.getvalue(), settings.s3_bucket_models, model_key)
        #
        # 3) Record where it was saved on the job:
        #        job.model_s3_key = model_key
        # ------------------------------------------------------------------
        buffer = io.BytesIO()
        joblib.dump(model, buffer)

        model_key = f"models/{job.id}/model.joblib"
        storage.upload_fileobj(buffer.getvalue(), settings.s3_bucket_models, model_key)
        job.model_s3_key = model_key

        # --- Save results + mark COMPLETED --------------------------------
        job.metrics = metrics
        job.status = JobStatus.COMPLETED
        db.commit()

    except Exception as exc:
        # Record the failure so it's visible via GET /jobs/{id} instead of silent.
        if job is not None:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            db.commit()
        raise
    finally:
        db.close()
