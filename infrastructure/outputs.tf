# ============================================================================
# Outputs — values Terraform prints after `apply`. Handy for confirming what
# was created, or feeding values to other tools/scripts.
# `value` references a resource attribute: aws_s3_bucket.datasets.bucket
# ============================================================================

output "datasets_bucket" {
  description = "Name of the datasets S3 bucket"
  value       = aws_s3_bucket.datasets.bucket
}

output "models_bucket" {
  description = "Name of the models S3 bucket"
  value       = aws_s3_bucket.models.bucket
}

# ----------------------------------------------------------------------------
# TODO(you): add an output for the models bucket once you've defined it,
# mirroring the example above (value = aws_s3_bucket.models.bucket).
# ----------------------------------------------------------------------------
