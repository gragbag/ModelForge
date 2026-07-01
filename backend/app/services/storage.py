"""
S3 storage service (works against LocalStack locally, real AWS in production).

This wraps `boto3` (the AWS SDK) so the rest of the app doesn't deal with S3
details directly — it just calls `upload_fileobj(...)` / `download_file(...)`.

Key idea: the SAME code talks to LocalStack or real AWS. The only difference is
`s3_endpoint_url` in your config — set to LocalStack's URL locally, unset in
production (then boto3 talks to real AWS). That's the whole trick.
"""

import io

import boto3

from app.core.config import settings

# --- The boto3 S3 client (built for you — the config is fiddly) -------------
# `endpoint_url=settings.s3_endpoint_url` is what points boto3 at LocalStack.
# The credentials are the dummy "test"/"test" LocalStack accepts.
_s3_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    region_name=settings.s3_region,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
)


def ensure_buckets() -> None:
    """
    Create the datasets/models buckets if they don't already exist.
    Called once on app startup (see main.py). Safe to call repeatedly.
    """
    existing = {b["Name"] for b in _s3_client.list_buckets().get("Buckets", [])}
    for bucket in (
        settings.s3_bucket_datasets,
        settings.s3_bucket_models,
        settings.s3_bucket_mlflow,  # MLflow stores run artifacts here
    ):
        if bucket not in existing:
            _s3_client.create_bucket(Bucket=bucket)


def upload_fileobj(file_bytes: bytes, bucket: str, key: str) -> None:
    """Upload raw bytes to S3 at s3://<bucket>/<key>.

    Self-healing: if the bucket has gone missing (e.g. LocalStack was reset),
    create it and retry once, instead of failing the request with a 500.
    """
    try:
        _s3_client.put_object(Bucket=bucket, Key=key, Body=file_bytes)
    except _s3_client.exceptions.NoSuchBucket:
        # Bucket vanished — recreate the buckets and retry the upload once.
        ensure_buckets()
        _s3_client.put_object(Bucket=bucket, Key=key, Body=file_bytes)


def delete_fileobj(bucket: str, key: str) -> None:
    """Delete an object from S3 (best-effort). S3 deletes are idempotent, so a
    missing object is not an error; we only swallow bucket-level issues."""
    try:
        _s3_client.delete_object(Bucket=bucket, Key=key)
    except _s3_client.exceptions.ClientError:
        pass


def download_fileobj(bucket: str, key: str) -> bytes:
    """
    Download an object from S3 and return its raw bytes. Used later by the
    worker (Step 6) to fetch the dataset before training. Built for you.
    """
    buffer = io.BytesIO()
    _s3_client.download_fileobj(bucket, key, buffer)
    return buffer.getvalue()
