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

    # --- Object storage (S3 / LocalStack) ---------------------------------
    # When this endpoint is set, boto3 talks to LocalStack instead of real AWS.
    s3_endpoint_url: str | None = "http://localhost:4566"
    s3_region: str = "us-east-1"
    aws_access_key_id: str = "test"        # LocalStack accepts any credentials
    aws_secret_access_key: str = "test"
    s3_bucket_datasets: str = "datasets"
    s3_bucket_models: str = "models"

    # --- Auth / JWT --------------------------------------------------------
    # The secret used to SIGN tokens. Anyone with this can forge tokens, so in
    # production it MUST come from real secrets management (never this default).
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60      # access tokens expire after 1 hour
    refresh_token_expire_days: int = 7         # refresh tokens last a week


# A single shared settings instance the rest of the app imports.
settings = Settings()
