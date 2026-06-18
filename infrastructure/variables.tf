# ============================================================================
# Input variables — the "parameters" of your infrastructure.
# Each has a default, so `terraform plan` works without passing anything.
# Variables are referenced elsewhere as `var.<name>` (e.g. var.aws_region).
# ============================================================================

variable "aws_region" {
  description = "AWS region to create resources in"
  type        = string
  default     = "us-east-1"
}

variable "localstack_s3_endpoint" {
  description = "LocalStack S3 endpoint, for free local testing"
  type        = string
  default     = "http://localhost:4566"
}
