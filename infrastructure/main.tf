# ============================================================================
# Terraform settings + the AWS provider.
# ----------------------------------------------------------------------------
# `terraform { ... }` declares which version of Terraform and which providers
# we need. A "provider" is the plugin that knows how to talk to a cloud — here,
# the AWS provider.
#
# The provider below is pointed at LOCALSTACK (your local fake-AWS) so you can
# run apply/destroy for FREE, no AWS account needed. The comments show exactly
# what to change to target REAL AWS later.
# ============================================================================

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  # ---- LocalStack settings (delete this whole block for real AWS) --------
  access_key                  = "test" # LocalStack accepts any credentials
  secret_key                  = "test"
  s3_use_path_style           = true # LocalStack needs path-style S3 URLs
  skip_credentials_validation = true # don't check creds against real AWS
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3 = var.localstack_s3_endpoint # send S3 calls to LocalStack
  }
  # ---- For REAL AWS: delete the block above. Just keep `region`, and supply
  #      credentials via env vars (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY).
  # ------------------------------------------------------------------------
}
