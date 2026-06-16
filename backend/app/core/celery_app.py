"""
Celery application setup.

This is the shared Celery "app" object that BOTH the API and the worker import:
  - The API imports it to ENQUEUE tasks (POST /jobs calls task.delay(...)).
  - The worker process IS this app, running in "worker" mode, CONSUMING tasks.

Two key configuration concepts:
  - broker        = WHERE tasks are sent (the queue). We use your Redis.
  - result_backend = WHERE task results/status are stored. Also Redis here.

You start a worker from the command line with:
    celery -A app.core.celery_app worker --loglevel=info

The `-A app.core.celery_app` tells Celery to look in THIS module for an app
object named `celery_app` (below).
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "modelforge",
    broker=settings.redis_url,          # tasks go onto this Redis
    backend=settings.redis_url,         # results/status stored in this Redis
    # Tell Celery which module(s) to scan for @celery_app.task functions, so the
    # worker knows about them. Without this, the worker wouldn't "see" the tasks.
    include=["app.services.tasks"],
)

# A couple of sensible defaults (optional but conventional).
celery_app.conf.update(
    task_track_started=True,   # report a "STARTED" state while a task runs
    task_time_limit=600,       # hard-kill a task after 10 minutes (safety net)
)
