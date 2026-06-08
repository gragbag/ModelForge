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

from fastapi import FastAPI

from app.core.config import settings

# Creating the app object. The title/version show up in the auto-generated docs.
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="A cloud-native MLOps platform for training and serving models.",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """
    Liveness check. Returns 200 with a small JSON body.

    Why it matters: this is the endpoint Kubernetes (later) will ping to know
    your container is alive, and it's the simplest possible proof the API runs.
    """
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


# ---------------------------------------------------------------------------
# TODO(you) — in later steps you'll add the real routers, e.g.:
#
#   from app.api import datasets, jobs
#   app.include_router(datasets.router)
#   app.include_router(jobs.router)
#
# Leave them commented until those modules exist.
# ---------------------------------------------------------------------------
