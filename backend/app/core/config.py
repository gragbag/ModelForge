"""
Application configuration.

Why this exists: we never hardcode things like database passwords or service
URLs in the code. Instead they come from ENVIRONMENT VARIABLES, and this file
centralizes reading them. Locally these are set by docker-compose; in production
they'd come from real secrets management. This is the same "secrets aren't in
the code" principle you saw in the CI pipeline.

`pydantic-settings` reads each field from an env var of the same name (case-
insensitive). The defaults below are dev-friendly so things "just work" locally.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Where to load env vars from. A local `.env` file (if present) is read,
    # then real environment variables override it.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---------------------------------------------------------------
    app_name: str = "ModelForge"
    environment: str = "development"

    # --- Database ----------------------------------------------------------
    # Format: postgresql://<user>:<password>@<host>:<port>/<dbname>
    # The host "postgres" matches the service name we'll use in docker-compose.
    database_url: str = "postgresql://modelforge:modelforge@localhost:5432/modelforge"

    # --- Redis (Celery broker) --------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # --- Object storage (S3 / MinIO) --------------------------------------
    # When this endpoint is set, boto3 talks to MinIO locally. Unset it in
    # production so boto3 uses real AWS S3 (same code, no other changes).
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region: str = "us-east-1"
    aws_access_key_id: str = "minioadmin"      # MinIO root creds (local dev)
    aws_secret_access_key: str = "minioadmin"
    s3_bucket_datasets: str = "datasets"
    s3_bucket_models: str = "models"
    s3_bucket_mlflow: str = "mlflow-artifacts"   # where MLflow stores artifacts

    # --- MLflow ------------------------------------------------------------
    # The tracking server the worker logs runs to. localhost for host-dev;
    # docker-compose overrides this to http://mlflow:5000 (service name).
    mlflow_tracking_uri: str = "http://localhost:5000"

    # --- Auth / JWT --------------------------------------------------------
    # The secret used to SIGN tokens. Anyone with this can forge tokens, so in
    # production it MUST come from real secrets management (never this default).
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60      # access tokens expire after 1 hour
    refresh_token_expire_days: int = 7         # refresh tokens last a week


# A single shared settings instance the rest of the app imports.
settings = Settings()
