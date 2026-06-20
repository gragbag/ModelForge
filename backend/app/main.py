"""
ModelForge API entry point.

This is the file uvicorn runs. For now it's intentionally minimal: just a
`/health` endpoint so you can confirm the whole toolchain works end to end
(install -> run server -> get a response -> see the auto-generated docs).

As you build later steps, you'll register more routers here (datasets, jobs).
Run it locally with:

    cd backend
    uvicorn app.main:app --reload

Then open:
    http://localhost:8000/health    -> the health check
    http://localhost:8000/docs      -> interactive OpenAPI docs (free with FastAPI)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import auth, datasets, jobs
from app.core.config import settings
from app.services import storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once on startup (before `yield`) and once on shutdown (after).
    On startup we make sure the S3 buckets exist, so uploads have somewhere to
    go. This is the "auto-create buckets on startup" choice you picked.
    """
    storage.ensure_buckets()
    yield
    # (nothing to clean up on shutdown for now)


# Creating the app object. The title/version show up in the auto-generated docs.
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="A cloud-native MLOps platform for training and serving models.",
    lifespan=lifespan,
)

# Register the auth endpoints (register, login, refresh, me).
app.include_router(auth.router)

# Register the datasets endpoints (POST /datasets, GET /datasets).
app.include_router(datasets.router)

# Register the jobs endpoints (POST /jobs, GET /jobs/{id}).
app.include_router(jobs.router)

# --- Observability --------------------------------------------------------
# Auto-instrument the app for Prometheus. This ONE call wires up a /metrics
# endpoint that reports request counts, latency histograms, and status codes —
# which Prometheus scrapes and Grafana graphs.
#
# TODO(you): activate the instrumentator. It's a single fluent call:
#     Instrumentator().instrument(app).expose(app)
#   - .instrument(app) -> measures every request
#   - .expose(app)     -> publishes the numbers at GET /metrics
# Write that one line below.
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health_check() -> dict[str, str]:
    """
    Liveness check. Returns 200 with a small JSON body.

    Why it matters: this is the endpoint Kubernetes (later) will ping to know
    your container is alive, and it's the simplest possible proof the API runs.
    """
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}
