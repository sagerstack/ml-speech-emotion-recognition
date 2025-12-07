output "model_storage_bucket_name" {
  description = "Name of the S3 bucket for model storage"
  value       = aws_s3_bucket.model_storage.id
}

output "model_storage_bucket_arn" {
  description = "ARN of the S3 bucket for model storage"
  value       = aws_s3_bucket.model_storage.arn
}

output "sagemaker_execution_role_arn" {
  description = "ARN of the SageMaker execution role"
  value       = aws_iam_role.sagemaker_execution.arn
}

output "sagemaker_execution_role_name" {
  description = "Name of the SageMaker execution role"
  value       = aws_iam_role.sagemaker_execution.name
}
