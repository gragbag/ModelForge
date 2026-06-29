"""
Celery tasks — run inside the WORKER process.

Step 12 adds RELIABILITY around the training work:
  - retries with exponential backoff on transient failures
  - idempotency (safe to run a job more than once)
  - permanent failures recorded as FAILED ("dead-letter" visibility)
  - acks_late (configured in celery_app.py) so a dying worker's job is redelivered

The core idea: tell TRANSIENT failures (retry) apart from PERMANENT ones (fail fast).
"""

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.exc import OperationalError

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.dataset import (
    STATUS_FAILED,
    STATUS_READY,
    STATUS_VALIDATING,
    Dataset,
)
from app.models.job import Job, JobStatus
from app.services import image_data, storage
from app.services.trainers import get_trainer

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


def _fail_dataset(db, dataset: Dataset | None, message: str) -> None:
    """Mark a dataset's validation as failed (shown in the UI)."""
    if dataset is not None:
        dataset.status = STATUS_FAILED
        dataset.error = message
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

        if job.status == JobStatus.COMPLETED:
            return

        job.status = JobStatus.RUNNING
        db.commit()

        dataset = db.get(Dataset, job.dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset {job.dataset_id} not found")

        # Dispatch to the trainer for this dataset's modality (tabular today;
        # image/text trainers plug in here). The trainer owns the whole
        # modality-specific pipeline: load data, train, log, and persist.
        trainer = get_trainer(dataset.modality)
        outcome = trainer.run(job, dataset)

        job.model_s3_key = outcome.model_s3_key
        job.metrics = outcome.metrics
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

        # Retry with exponential backoff (waits grow 1s, 2s, 4s as retries climb).
        # self.retry raises a special exception Celery catches to reschedule, so
        # it doesn't fall through to the handler below.
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    except Exception as exc:
        # ---- Permanent failure (e.g. bad data / missing column) -----------
        # Not in TRANSIENT_ERRORS, so retrying wouldn't help. Record + re-raise.
        _mark_failed(db, job, str(exc))
        raise

    finally:
        db.close()


@celery_app.task(bind=True, name="validate_dataset", max_retries=3)
def validate_dataset_task(self, dataset_id: int) -> None:
    """Content-validate an uploaded image dataset in the background.

    Downloads the zip, opens every image (work too heavy for the upload request),
    and moves the dataset validating -> ready (with final metadata) or failed
    (with a reason). Same transient-vs-permanent error handling as training.
    """
    db = SessionLocal()
    dataset = None
    try:
        dataset = db.get(Dataset, dataset_id)
        # Gone, or already finalized by an earlier run -> nothing to do (idempotent).
        if dataset is None or dataset.status != STATUS_VALIDATING:
            return

        raw = storage.download_fileobj(settings.s3_bucket_datasets, dataset.s3_key)

        try:
            meta = image_data.validate_contents(raw)
        except ValueError as exc:
            # The data itself is bad (not images / too few classes) — permanent.
            _fail_dataset(db, dataset, str(exc))
            return

        dataset.meta = meta
        dataset.status = STATUS_READY
        dataset.error = None
        db.commit()

    except ClientError as exc:
        if _is_transient_client_error(exc) and self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        _fail_dataset(db, dataset, str(exc))
        raise

    except TRANSIENT_ERRORS as exc:
        if self.request.retries >= self.max_retries:
            _fail_dataset(db, dataset, f"Failed after {self.request.retries} retries: {exc}")
            raise
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    except Exception as exc:
        _fail_dataset(db, dataset, str(exc))
        raise

    finally:
        db.close()
