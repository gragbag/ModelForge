# ============================================================================
# ModelForge backend/worker image (multi-stage build)
# ----------------------------------------------------------------------------
# This SAME image runs two ways (see docker-compose.yml):
#   - backend: the default CMD (uvicorn)
#   - worker:  command overridden to run celery
#
# Multi-stage build = two stages:
#   1. "builder" installs the Python dependencies into a virtualenv.
#   2. "final" copies just that venv + the app code, leaving the build tools
#      behind. Result: a smaller, cleaner production image.
# ============================================================================

# ---- Stage 1: builder -- install dependencies ------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Create an isolated virtualenv we can copy wholesale into the final stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy ONLY requirements first. Docker caches each layer; as long as
# requirements.txt is unchanged, this expensive install layer is reused even
# when your app code changes. (That's why we copy it before the code.)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---- Stage 2: final -- the actual runtime image ----------------------------
FROM python:3.12-slim AS final

WORKDIR /app

# Bring over the ready-made virtualenv from the builder (no pip/build tools).
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Don't buffer stdout/stderr — so logs show up immediately in `docker logs`.
ENV PYTHONUNBUFFERED=1

# Copy the application code (app/, alembic/, alembic.ini, entrypoint.sh, ...).
COPY . .

# The entrypoint optionally runs DB migrations, then execs whatever command
# the container was given (uvicorn for backend, celery for worker).
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command = run the API. The worker service overrides this in compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
