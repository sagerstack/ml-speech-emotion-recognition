# S3 bucket for ML model storage (raw models and SageMaker packages)
resource "aws_s3_bucket" "model_storage" {
  bucket        = "${var.project_name}-models-${var.aws_region}"
  force_destroy = true # Allow deletion even with objects/versions

  tags = merge(
    var.common_tags,
    {
      Name    = "ML Model Storage"
      Purpose = "raw-models-and-sagemaker-packages"
    }
  )
}

# Enable versioning to track model versions
resource "aws_s3_bucket_versioning" "model_storage" {
  bucket = aws_s3_bucket.model_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "model_storage" {
  bucket = aws_s3_bucket.model_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "model_storage" {
  bucket = aws_s3_bucket.model_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy to manage old model versions
resource "aws_s3_bucket_lifecycle_configuration" "model_storage" {
  bucket = aws_s3_bucket.model_storage.id

  # Archive old SageMaker packages to Glacier after 90 days
  rule {
    id     = "archive-old-sagemaker-packages"
    status = "Enabled"

    filter {
      prefix = "sagemaker-models/"
    }

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}
