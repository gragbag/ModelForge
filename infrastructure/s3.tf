# ============================================================================
# The S3 buckets, defined as code.
#
# A `resource` block declares one piece of infrastructure:
#     resource "<type>" "<local_name>" { ...settings... }
#   - <type>       : what AWS thing it is (aws_s3_bucket)
#   - <local_name> : a name YOU pick to refer to it within Terraform
#                    (e.g. aws_s3_bucket.datasets.bucket elsewhere)
#
# Note: these use "-tf" names so they don't collide with the buckets your app
# auto-creates in the same LocalStack. In a real deployment, Terraform would own
# bucket creation and you'd drop the app's ensure_buckets().
# ============================================================================

# Worked example — the datasets bucket.
resource "aws_s3_bucket" "datasets" {
  bucket = "modelforge-datasets-tf"

  tags = {
    Project = "ModelForge"
    Purpose = "Uploaded datasets"
  }
}

resource "aws_s3_bucket" "models" {
  bucket = "modelforge-models-tf"

  tags = {
    Project = "ModelForge"
    Purpose = "Trained model artifacts"
  }
}

# ----------------------------------------------------------------------------
# TODO(you): define a second bucket for trained models, mirroring the example
# above:
#   - resource "aws_s3_bucket" "models"
#   - bucket = "modelforge-models-tf"
#   - tags: Project = "ModelForge", Purpose = "Trained model artifacts"
# ----------------------------------------------------------------------------
