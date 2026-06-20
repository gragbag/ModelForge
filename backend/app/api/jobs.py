"""
Job endpoints: submit a training job and check its status.

POST /jobs flow:
    1. Validate the request (Pydantic + check the dataset exists)
    2. Create a Job row with status=QUEUED
    3. Enqueue the Celery task (drops it onto Redis for the worker)
    4. Return the job immediately (status QUEUED) — we DON'T wait for training

GET /jobs/{id}:
    Look up the job and return its current status/metrics (the user polls this).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.dataset import Dataset
from app.models.job import Job
from app.models.user import Role, User
from app.schemas.job import JobCreate, JobRead
from app.services.tasks import train_model_task

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=201)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <-- requires a valid token
) -> Job:
    """
    Submit a training job. `payload: JobCreate` is the validated request body —
    by the time this runs, Pydantic has guaranteed the fields are present and
    the right types.
    """
    # Make sure the referenced dataset exists AND belongs to this user (you
    # shouldn't be able to train on someone else's data). 404 either way so we
    # don't reveal that a dataset exists but belongs to someone else.
    dataset = db.get(Dataset, payload.dataset_id)
    if dataset is None or (
        dataset.owner_id != current_user.id and current_user.role != Role.ADMIN
    ):
        raise HTTPException(status_code=404, detail="Dataset not found")

    job = Job(
        dataset_id=payload.dataset_id,
        model_type=payload.model_type,
        target_column=payload.target_column,
        task_type=payload.task_type,
        owner_id=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue the training task (the Redis hand-off). Returns immediately;
    # the actual work happens in the worker.
    train_model_task.delay(job.id)

    return job


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # <-- requires a valid token
) -> Job:
    """Fetch a job by id — but only if it's YOURS (admins can see any)."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.owner_id != current_user.id and current_user.role != Role.ADMIN:
        raise HTTPException(status_code=404, detail="Job not found")

    return job
