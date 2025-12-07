# SageMaker Terraform Module

This module provisions AWS infrastructure for SageMaker model deployment including S3 storage, IAM roles, and permissions.

## Resources Created

### S3 Storage
- **S3 Bucket**: `{project_name}-models-{region}` for storing model artifacts
  - `raw-models/v{x}/`: Trained models uploaded by data scientists
  - `sagemaker-models/v{x}/`: Packaged models for SageMaker deployment
- **Versioning**: Enabled to track all model uploads
- **Encryption**: AES256 encryption at rest
- **Lifecycle Policies**:
  - SageMaker packages archived to Glacier after 90 days
  - Raw models kept indefinitely for audit/rollback

### IAM Roles
- **SageMaker Execution Role**: Allows SageMaker endpoints to:
  - Read model artifacts from S3
  - Pull container images from ECR
  - Write logs to CloudWatch
  - Access SageMaker services

## Usage

```hcl
module "sagemaker" {
  source = "./modules/sagemaker"

  project_name = "ml-speech-emotion"
  environment  = "prod"
  aws_region   = "us-east-1"

  # Optional: Initial model deployment
  model_version = "v5"

  # Instance configuration
  instance_type = "ml.t3.medium"
  min_capacity  = 1
  max_capacity  = 3

  # Auto-scaling
  autoscaling_target_invocations = 100

  common_tags = {
    Project     = "ML Speech Emotion Recognition"
    Environment = "prod"
    ManagedBy   = "Terraform"
  }
}
```

## Outputs

- `model_storage_bucket_name`: S3 bucket name for model storage
- `model_storage_bucket_arn`: S3 bucket ARN
- `sagemaker_execution_role_arn`: IAM role ARN for SageMaker
- `sagemaker_execution_role_name`: IAM role name

## Model Deployment Workflow

1. **Data Scientist**: Upload model to S3
   ```bash
   ./scripts/upload_model_to_s3.sh v5
   ```

2. **GitHub Actions**: Package and deploy to SageMaker
   ```bash
   gh workflow run cd.yml -f model_version=v5
   ```

3. **SageMaker**: Endpoint serves predictions from deployed model

## Notes

- SageMaker model/endpoint resources are **NOT** managed by this module
- They are created dynamically by GitHub Actions CD pipeline
- This module only provisions infrastructure (S3, IAM) needed for deployment
- Actual model deployment happens via `deployment/sagemaker/scripts/deploy_to_sagemaker.py`
