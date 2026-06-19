"""
Celery tasks — run inside the WORKER process.

Step 12 adds RELIABILITY around the training work:
  - retries with exponential backoff on transient failures
  - idempotency (safe to run a job more than once)
  - permanent failures recorded as FAILED ("dead-letter" visibility)
  - acks_late (configured in celery_app.py) so a dying worker's job is redelivered

The core idea: tell TRANSIENT failures (retry) apart from PERMANENT ones (fail fast).
"""

import io

import joblib
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import OperationalError

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.dataset import Dataset
from app.models.job import Job, JobStatus
from app.services import storage, training

# Connection-level errors worth RETRYING — momentary network/endpoint/DB
# glitches. NOTE: ClientError is deliberately NOT here anymore. A boto3
# ClientError wraps an HTTP error from S3, and those split into two kinds —
# 5xx (transient) and 4xx like 404 (permanent) — so we classify it separately
# in `_is_transient_client_error` below rather than blindly retrying all of them.
TRANSIENT_ERRORS = (BotoCoreError, OperationalError, ConnectionError)


def _is_transient_client_error(exc: ClientError) -> bool:
    """A boto3 ClientError wraps an HTTP error response from S3.
      - 5xx  -> the SERVER had a problem  -> transient, worth retrying
      - 4xx  -> OUR request was bad (e.g. 404 file-not-found, 403 forbidden)
                -> permanent, retrying can't help

    TODO(you): return True only for 5xx status codes. The HTTP status lives at:
        exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
    Return whether that status is >= 500.
    """
    status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
    return status >= 500


def _mark_failed(db, job: Job | None, message: str) -> None:
    """Record a permanent failure so it's visible via GET /jobs/{id} — our
    'dead-letter' handling: failed jobs are captured, never silently lost."""
    if job is not None:
        job.status = JobStatus.FAILED
        job.error = message
        db.commit()


@celery_app.task(
    bind=True,        # `bind=True` gives us `self` -> self.retry(), self.request.retries
    name="train_model",
    max_retries=3,    # retry a transient failure up to 3 times
)
def train_model_task(self, job_id: int) -> None:
    db = SessionLocal()
    job = None
    try:
        job = db.get(Job, job_id)
        if job is None:
            return  # job was deleted before the worker got to it

        # ---- IDEMPOTENCY guard ------------------------------------------
        # A job can be delivered MORE THAN ONCE: a retry, or acks_late
        # redelivering after a worker died right after finishing. Re-running a
        # finished job wastes work and overwrites good results.
        #
        # TODO(you): return early if the job is already done. One line:
        #     if job.status == JobStatus.COMPLETED:
        #         return

        if job.status == JobStatus.COMPLETED:
            return

        job.status = JobStatus.RUNNING
        db.commit()

        dataset = db.get(Dataset, job.dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset {job.dataset_id} not found")

        raw = storage.download_fileobj(settings.s3_bucket_datasets, dataset.s3_key)
        df = pd.read_csv(io.BytesIO(raw))

        model, metrics = training.train_and_evaluate(
            df=df,
            target_column=job.target_column,
            task_type=job.task_type,
            model_type=job.model_type,
        )

        # Deterministic key: a re-run overwrites the SAME S3 object rather than
        # creating duplicates — another piece of idempotency.
        buffer = io.BytesIO()
        joblib.dump(model, buffer)
        model_key = f"models/{job.id}/model.joblib"
        storage.upload_fileobj(buffer.getvalue(), settings.s3_bucket_models, model_key)

        job.model_s3_key = model_key
        job.metrics = metrics
        job.status = JobStatus.COMPLETED
        db.commit()

    except ClientError as exc:
        # ---- S3 returned an HTTP error -> classify before retrying --------
        # 5xx = transient (retry); 4xx like 404 = permanent (fail fast). This is
        # the precise classification that stops us pointlessly retrying a 404.
        if _is_transient_client_error(exc) and self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        _mark_failed(db, job, str(exc))
        raise

    except TRANSIENT_ERRORS as exc:
        # ---- Transient failure -> RETRY with exponential backoff ----------
        if self.request.retries >= self.max_retries:
            # Out of retries -> give up and record a permanent failure.
            _mark_failed(db, job, f"Failed after {self.request.retries} retries: {exc}")
            raise

        # TODO(you): trigger the retry. Celery re-queues the job and re-runs it
        # after `countdown` seconds. Exponential backoff = 2 ** attempt, so the
        # waits grow 2s, 4s, 8s as retries climb:
        #     raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        #
        # (self.retry raises a special exception Celery catches to reschedule —
        #  so it doesn't fall through to the handler below.)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    except Exception as exc:
        # ---- Permanent failure (e.g. bad data / missing column) -----------
        # Not in TRANSIENT_ERRORS, so retrying wouldn't help. Record + re-raise.
        _mark_failed(db, job, str(exc))
        raise

    finally:
        db.close()
