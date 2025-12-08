# SageMaker Model Deployment Guide

This guide explains how to deploy ML models to AWS SageMaker for the Speech Emotion Recognition project.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Deployment Workflow](#deployment-workflow)
- [Manual Operations](#manual-operations)
- [Troubleshooting](#troubleshooting)

---

## Overview

This project uses AWS SageMaker for production ML model serving, with models stored in S3 and deployed via GitHub Actions CD pipeline.

### Key Components

- **S3 Storage**: Primary storage for trained models
- **SageMaker Endpoint**: Production inference endpoint
- **GitHub Actions**: Automated deployment pipeline
- **Terraform**: Infrastructure provisioning

### Model Storage Structure

```
s3://ml-speech-emotion-models-us-east-1/
├── raw-models/                    # Trained models (uploaded by data scientists)
│   ├── v4/
│   │   ├── model.pkl              # 926 MB scikit-learn model
│   │   ├── metadata.json          # Model metadata
│   │   ├── feature_extractor.py   # Feature extraction logic
│   │   └── manifest.json          # Upload manifest
│   └── v5/
│       ├── model.pkl              # 1.2 GB scikit-learn model
│       ├── metadata.json
│       ├── feature_extractor.py
│       └── manifest.json
└── sagemaker-models/              # Packaged for SageMaker (created by CD pipeline)
    ├── v4/
    │   └── model.tar.gz           # SageMaker package (model + inference code)
    └── v5/
        └── model.tar.gz
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Data Scientist Workflow                                     │
├─────────────────────────────────────────────────────────────┤
│  1. Train model → backend/models/v{x}/model.pkl             │
│  2. Run: ./scripts/upload_model_to_s3.sh v5                 │
│     → Uploads to S3: raw-models/v5/                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  S3: Primary Model Storage (Source of Truth)                 │
├─────────────────────────────────────────────────────────────┤
│  • raw-models/v{x}/: Trained models (versioned, persistent) │
│  • sagemaker-models/v{x}/: Packaged for deployment          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions CD Pipeline                                  │
├─────────────────────────────────────────────────────────────┤
│  Trigger: gh workflow run cd.yml -f model_version=v5        │
│                                                              │
│  Job 1: Deploy Model to SageMaker                           │
│    1. Download from S3: raw-models/v5/model.pkl             │
│    2. Package: model.tar.gz (model + inference.py)          │
│    3. Upload to S3: sagemaker-models/v5/model.tar.gz        │
│    4. Deploy to SageMaker endpoint (15min timeout)          │
│                                                              │
│  Job 2: Deploy to EKS (always runs)                         │
│    1. Deploy backend/streamlit to EKS cluster               │
│    2. Display deployment summary                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS SageMaker Production Endpoint                           │
├─────────────────────────────────────────────────────────────┤
│  Endpoint: ml-emotion-prod                                  │
│  Instance: ml.t3.medium (1-3 instances, auto-scaling)       │
│  Model: v{x} from S3                                        │
│  Container: AWS pre-built scikit-learn:1.2-1-cpu-py3        │
│  Handler: inference.py (model_fn, input_fn, predict_fn)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### 1. Infrastructure Setup

Ensure Terraform infrastructure is deployed:

```bash
cd deployment/terraform
terraform init
terraform apply
```

This creates:
- S3 bucket: `ml-speech-emotion-models-us-east-1`
- SageMaker execution IAM role
- GitHub Actions deployment role with SageMaker permissions

### 2. AWS Credentials

Data scientists need AWS credentials with S3 write access:

```bash
# Configure AWS CLI profile
aws configure --profile ml-ser-deploy

# Test access
aws s3 ls --profile ml-ser-deploy
```

### 3. GitHub Secrets

Ensure GitHub repository has secret:
- `AWS_DEPLOY_ROLE_ARN`: ARN of GitHub Actions deployment role

---

## Deployment Workflow

### Option 1: Automated Deployment (Recommended)

**Step 1: Upload Model to S3**

After training a new model:

```bash
# Upload model v5 to S3
./scripts/upload_model_to_s3.sh v5 --profile ml-ser-deploy
```

This uploads:
- `model.pkl` (large file, may take a few minutes)
- `metadata.json`
- `feature_extractor.py`
- `manifest.json` (auto-generated)

**Step 2: Trigger Deployment via GitHub Actions**

```bash
# Deploy model v5 to SageMaker
gh workflow run cd.yml -f model_version=v5

# Or via GitHub UI:
# Actions → Deploy to Production → Run workflow
# Enter: model_version = v5
```

**Step 3: Monitor Deployment**

```bash
# Watch workflow progress
gh run watch

# Or view logs in GitHub UI
```

Deployment takes approximately **15-20 minutes**:
- Download from S3: ~2 min
- Package model: ~1 min
- Upload to S3: ~2 min
- SageMaker deployment: ~10-15 min

**Step 4: Verify Deployment**

```bash
# Check SageMaker endpoint status
aws sagemaker describe-endpoint \
  --endpoint-name ml-emotion-prod \
  --region us-east-1 \
  --query '{Name:EndpointName, Status:EndpointStatus, Model:ProductionVariants[0].VariantName, Instance:ProductionVariants[0].InstanceType}' \
  --output table

# Expected output:
# --------------------------------------------------------
# |                  DescribeEndpoint                     |
# +----------+--------------------------------------------+
# | Instance |  ml.t3.medium                              |
# | Model    |  AllTraffic                                |
# | Name     |  ml-emotion-prod                           |
# | Status   |  InService                                 |
# +----------+--------------------------------------------+
```

### Option 2: Skip SageMaker Deployment

Deploy only EKS application without updating SageMaker:

```bash
gh workflow run cd.yml -f skip_sagemaker=true
```

---

## Manual Operations

### Download Model from S3 (For Local Development)

```bash
# Download model v5 from S3 for local testing
./scripts/download_model_from_s3.sh v5 --profile ml-ser-deploy
```

Downloads to:
- `backend/models/v5/model.pkl`
- `backend/app/infrastructure/model/v5/metadata.json`
- `backend/app/infrastructure/model/v5/feature_extractor.py`

### List Available Models in S3

```bash
# List all model versions in S3
aws s3 ls s3://ml-speech-emotion-models-us-east-1/raw-models/ --profile ml-ser-deploy

# Expected output:
#                            PRE v4/
#                            PRE v5/
```

### Manual SageMaker Deployment (For Testing)

```bash
# Package model manually
cd deployment/sagemaker
mkdir -p model_package/code

# Download from S3
aws s3 cp s3://ml-speech-emotion-models-us-east-1/raw-models/v5/model.pkl \
  model_package/model.pkl --profile ml-ser-deploy

aws s3 cp s3://ml-speech-emotion-models-us-east-1/raw-models/v5/metadata.json \
  model_package/metadata.json --profile ml-ser-deploy

aws s3 cp s3://ml-speech-emotion-models-us-east-1/raw-models/v5/feature_extractor.py \
  model_package/code/feature_extractor.py --profile ml-ser-deploy

# Copy inference handler
cp inference.py model_package/code/

# Create requirements.txt
cat > model_package/code/requirements.txt <<EOF
librosa==0.10.1
numpy==1.24.3
scikit-learn==1.3.0
soundfile==0.12.1
pandas==2.0.3
EOF

# Package
cd model_package
tar -czf ../model.tar.gz *
cd ..

# Upload to S3
aws s3 cp model.tar.gz \
  s3://ml-speech-emotion-models-us-east-1/sagemaker-models/v5/model.tar.gz \
  --profile ml-ser-deploy

# Deploy to SageMaker
python scripts/deploy_to_sagemaker.py \
  --model-version v5 \
  --endpoint-name ml-emotion-prod \
  --instance-type ml.t3.medium \
  --s3-uri s3://ml-speech-emotion-models-us-east-1/sagemaker-models/v5/model.tar.gz \
  --region us-east-1
```

### Delete SageMaker Endpoint (Cost Savings)

```bash
# Delete endpoint (stops incurring costs)
aws sagemaker delete-endpoint \
  --endpoint-name ml-emotion-prod \
  --region us-east-1

# Delete endpoint configuration
aws sagemaker delete-endpoint-config \
  --endpoint-config-name ml-emotion-v5-config \
  --region us-east-1

# Delete model
aws sagemaker delete-model \
  --model-name ml-emotion-v5 \
  --region us-east-1
```

---

## Troubleshooting

### Issue: "Model not found in S3"

**Symptoms:**
```
❌ Error: Model not found in S3: s3://bucket/raw-models/v5/model.pkl
```

**Solution:**
```bash
# Upload model first
./scripts/upload_model_to_s3.sh v5 --profile ml-ser-deploy

# Verify upload
aws s3 ls s3://ml-speech-emotion-models-us-east-1/raw-models/v5/ --profile ml-ser-deploy
```

---

### Issue: SageMaker Deployment Timeout

**Symptoms:**
```
TimeoutError: Endpoint did not reach InService status within 900s
```

**Causes:**
- Large model size (>1GB takes longer)
- First deployment (cold start)
- Instance type provisioning

**Solution:**
```bash
# Check endpoint status
aws sagemaker describe-endpoint \
  --endpoint-name ml-emotion-prod \
  --region us-east-1

# If status is "Creating" or "Updating", wait longer
# SageMaker deployments can take 15-20 minutes

# Increase timeout in CD workflow if needed (default: 900s)
```

---

### Issue: Terraform Outputs Not Available

**Symptoms:**
```
❌ Error: Could not get S3 bucket name from Terraform outputs
```

**Solution:**
```bash
# Apply Terraform first
cd deployment/terraform
terraform apply

# Verify outputs
terraform output model_storage_bucket_name

# Expected output:
# "ml-speech-emotion-models-us-east-1"
```

---

### Issue: GitHub Actions Role Permission Denied

**Symptoms:**
```
AccessDenied: User is not authorized to perform: sagemaker:CreateModel
```

**Solution:**

Ensure GitHub Actions IAM role has SageMaker permissions:

```bash
# Check role policy in deployment/terraform/main.tf
# Should include:
# - sagemaker:CreateModel
# - sagemaker:CreateEndpointConfig
# - sagemaker:CreateEndpoint
# - sagemaker:UpdateEndpoint
# - sagemaker:DescribeModel
# - sagemaker:DescribeEndpointConfig
# - sagemaker:DescribeEndpoint
# - s3:GetObject
# - s3:PutObject
# - iam:PassRole (for SageMaker execution role)

# Re-apply Terraform to update permissions
cd deployment/terraform
terraform apply
```

---

### Issue: Model Inference Errors

**Symptoms:**
SageMaker endpoint returns 500 errors during inference

**Debug Steps:**

```bash
# 1. Check CloudWatch logs
aws logs tail /aws/sagemaker/Endpoints/ml-emotion-prod --follow --region us-east-1

# 2. Check endpoint logs for errors
aws sagemaker describe-endpoint \
  --endpoint-name ml-emotion-prod \
  --region us-east-1 \
  --query 'FailureReason' \
  --output text

# 3. Test locally with same inference handler
cd backend
poetry run python -c "
from deployment.sagemaker.inference import model_fn, input_fn, predict_fn
model = model_fn('models/v5')
# Test with sample audio...
"
```

---

## Cost Optimization

### SageMaker Costs

- **ml.t3.medium**: ~$0.056/hour = ~$40/month per instance
- **Auto-scaling**: 1-3 instances based on load
- **Storage**: S3 storage ~$0.023/GB/month

### Recommendations

1. **Use auto-scaling**: Only run instances when needed
2. **Delete endpoint when not in use**: Stop costs during non-production periods
3. **Use Spot instances**: (Future optimization) ~70% cost savings
4. **Monitor invocations**: Scale down during low-traffic periods

---

## Additional Resources

- [AWS SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [Scikit-learn Container Documentation](https://sagemaker.readthedocs.io/en/stable/frameworks/sklearn/using_sklearn.html)
- [Project Implementation Plan](../../.claude/artifacts/US-001-SAGEMAKER-DEPLOYMENT-IMPL-PLAN.md)
