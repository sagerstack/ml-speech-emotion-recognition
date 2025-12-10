# SageMaker Deployment Guide

Complete guide for deploying ML models to AWS SageMaker, covering data scientist workflows, MLOps setup, and continuous deployment.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Roles & Responsibilities](#roles--responsibilities)
- [Initial Setup (One-Time)](#initial-setup-one-time)
- [Data Scientist Workflow](#data-scientist-workflow)
- [MLOps Workflow](#mlops-workflow)
- [CD Pipeline](#cd-pipeline)
- [Scripts Reference](#scripts-reference)
- [Custom Container Details](#custom-container-details)
- [Troubleshooting](#troubleshooting)

---

## Overview

This project uses **AWS SageMaker** for model serving with the following approach:

- **Custom Docker Container**: Uses sklearn 1.7.2 + numpy 2.1.0 (AWS's latest is only 1.4.2)
- **Offline Packaging**: Models are packaged locally and uploaded to S3
- **GitHub Actions CD**: Automated deployment to SageMaker endpoints
- **Multi-Environment**: Supports development and production endpoints

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| Custom Container | Inference runtime with sklearn 1.7.2 | `deployment/sagemaker/container/` |
| Model Package | Trained model + dependencies | `backend/models/v5/` |
| Deployment Script | Creates/updates SageMaker endpoints | `deployment/sagemaker/scripts/deploy_to_sagemaker.py` |
| Upload Script | Packages and uploads to S3 | `scripts/upload_model_to_s3.sh` |
| CD Workflow | Automated deployment pipeline | `.github/workflows/cd.yml` |

---

## Architecture

```
┌─────────────────┐
│  Data Scientist │
└────────┬────────┘
         │
         │ 1. Train Model
         │ 2. Test Locally
         │
         ▼
┌─────────────────────┐
│ Model Packaging     │
│ - model.pkl         │
│ - inference.py      │
│ - requirements.txt  │
│ - ultra_ensemble.py │
└────────┬────────────┘
         │
         │ 3. Upload to S3
         │    (upload_model_to_s3.sh)
         ▼
┌─────────────────────┐
│ S3 Bucket           │
│ ml-speech-emotion-  │
│ models-us-east-1/   │
│ └─ sagemaker-models/│
│    └─ v5/           │
│       └─ model.tar.gz
└────────┬────────────┘
         │
         │ 4. Trigger CD Workflow
         │    (GitHub Actions)
         ▼
┌─────────────────────┐
│ SageMaker Deployer  │
│ (deploy_to_sagemaker│
│  .py)               │
└────────┬────────────┘
         │
         │ 5. Create/Update Resources
         ├─ Create Model (ml-emotion-v5)
         ├─ Create Endpoint Config
         └─ Create/Update Endpoint
         │
         ▼
┌─────────────────────┐
│ SageMaker Endpoint  │
│ ml-ser-endpoint4    │
│                     │
│ ┌─────────────────┐ │
│ │ Custom Container│ │
│ │ sklearn 1.7.2   │ │
│ │ numpy 2.1.0     │ │
│ │                 │ │
│ │ ┌─────────────┐ │ │
│ │ │ Flask App   │ │ │
│ │ │ /ping       │ │ │
│ │ │ /invocations│ │ │
│ │ └─────────────┘ │ │
│ └─────────────────┘ │
└─────────────────────┘
```

---

## Roles & Responsibilities

### Data Scientist

**Responsibilities:**
- Train and validate ML models
- Package models with inference code
- Test locally before deployment
- Upload model packages to S3

**Required Tools:**
- Poetry (Python dependency management)
- AWS CLI with `ml-ser-deploy` profile
- Docker (optional, for local testing)

### MLOps Engineer

**Responsibilities:**
- Set up AWS infrastructure (IAM, ECR, S3)
- Build and maintain custom Docker containers
- Configure and maintain CD pipelines
- Monitor deployments and troubleshoot issues

**Required Tools:**
- AWS CLI with admin access
- Docker
- GitHub CLI (`gh`)
- Terraform (optional, for infrastructure as code)

---

## Initial Setup (One-Time)

### 1. AWS Infrastructure Setup

#### S3 Bucket for Models

```bash
# Create S3 bucket
aws s3 mb s3://ml-speech-emotion-models-us-east-1 --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ml-speech-emotion-models-us-east-1 \
  --versioning-configuration Status=Enabled
```

#### IAM Role for SageMaker

```bash
# Create SageMaker execution role
aws iam create-role \
  --role-name ml-speech-emotion-prod-sagemaker-execution \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "sagemaker.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach managed policy
aws iam attach-role-policy \
  --role-name ml-speech-emotion-prod-sagemaker-execution \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess

# Add S3 access policy
aws iam put-role-policy \
  --role-name ml-speech-emotion-prod-sagemaker-execution \
  --policy-name s3-model-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::ml-speech-emotion-models-us-east-1",
        "arn:aws:s3:::ml-speech-emotion-models-us-east-1/*"
      ]
    }]
  }'

# Add ECR pull permissions for custom container
aws iam put-role-policy \
  --role-name ml-speech-emotion-prod-sagemaker-execution \
  --policy-name ecr-pull-custom-container \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ],
        "Resource": "arn:aws:ecr:us-east-1:303440520181:repository/ml-speech-emotion-sklearn"
      },
      {
        "Effect": "Allow",
        "Action": "ecr:GetAuthorizationToken",
        "Resource": "*"
      }
    ]
  }'
```

#### IAM User for Deployment

```bash
# Create deployment user
aws iam create-user --user-name ml-ser-deploy

# Attach necessary policies
aws iam attach-user-policy \
  --user-name ml-ser-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-user-policy \
  --user-name ml-ser-deploy \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

# Create access keys
aws iam create-access-key --user-name ml-ser-deploy
```

Configure AWS CLI profile:

```bash
aws configure --profile ml-ser-deploy
# Enter Access Key ID, Secret Access Key, us-east-1, json
```

### 2. Build Custom Docker Container

**Why Custom Container?**
- AWS's latest sklearn container only supports **sklearn 1.4.2**
- Our model was trained with **sklearn 1.7.2** (released 2024)
- Need numpy 2.x support for pickle compatibility

**Build and Push:**

```bash
cd deployment/sagemaker/container

# Build for linux/amd64 (SageMaker runs on x86_64)
./build_and_push.sh --profile ml-ser-deploy
```

This creates:
- **Image**: `303440520181.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-sklearn:1.7.2-py310`
- **Size**: ~426MB
- **Contents**: Python 3.10, sklearn 1.7.2, numpy 2.1.0, Flask, Gunicorn, nginx

### 3. GitHub Secrets

Add these secrets to GitHub repository (`Settings → Secrets → Actions`):

```
AWS_ACCOUNT_ID=303440520181
AWS_REGION=us-east-1
```

GitHub Actions uses OIDC for authentication (no access keys needed).

---

## Data Scientist Workflow

### Step 1: Train Model

```bash
cd backend

# Activate poetry environment
poetry shell

# Train model (example)
poetry run python -m src.train --version v5
```

### Step 2: Package Model

Model package structure:

```
backend/models/v5/
├── model.pkl              # Pickled model (1.2GB)
├── inference.py           # Custom inference logic
├── ultra_ensemble.py      # Custom model class
├── requirements.txt       # Python dependencies
└── metadata.json          # Model metadata
```

**requirements.txt:**

```txt
# Compatible with sagemaker-scikit-learn:1.4-2-cpu-py3 container
# which has sklearn 1.4.2 + numpy 2.x support
numpy>=2.0.0
scikit-learn>=1.4.0
```

**Important Considerations:**

1. **Pickle Compatibility**: Model must be pickled with `UltraEnsembleModel` injected into `__main__`:

```python
# When saving model
import __main__
from ultra_ensemble import UltraEnsembleModel
__main__.UltraEnsembleModel = UltraEnsembleModel

with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)
```

2. **File Size**: Model.pkl is 1.2GB - ensure fast upload to S3

3. **Custom Classes**: Include all custom classes (`ultra_ensemble.py`)

### Step 3: Test Locally (Optional)

```bash
# Load and test model
poetry run python -c "
import pickle
with open('backend/models/v5/model.pkl', 'rb') as f:
    model = pickle.load(f)
print(model)
"
```

### Step 4: Upload to S3

```bash
# From project root
./scripts/upload_model_to_s3.sh v5 --profile ml-ser-deploy
```

**What this does:**

1. Creates temporary directory
2. Copies model files from `backend/models/v5/`
3. Creates `code/` subdirectory for inference code
4. Packages as `model.tar.gz`
5. Uploads to S3: `s3://ml-speech-emotion-models-us-east-1/sagemaker-models/v5/model.tar.gz`

**Output:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Packaging model v5 for SageMaker
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Model package created (359.3 MB)
✓ Uploaded to S3

S3 URI: s3://ml-speech-emotion-models-us-east-1/sagemaker-models/v5/model.tar.gz
```

### Step 5: Trigger Deployment

**Option A: Via GitHub Actions UI**

1. Go to `Actions → Deploy to Production`
2. Click `Run workflow`
3. Enter:
   - `model_version`: `v5`
   - `endpoint_name`: `ml-ser-endpoint4` (or custom name)

**Option B: Via GitHub CLI**

```bash
gh workflow run cd.yml \
  -f model_version=v5 \
  -f endpoint_name=ml-ser-endpoint4 \
  --ref feature/clean-architecture-refactor
```

---

## MLOps Workflow

### Container Management

#### Rebuild Container (when dependencies change)

```bash
cd deployment/sagemaker/container

# Edit Dockerfile to update dependencies
# Then rebuild and push
./build_and_push.sh --profile ml-ser-deploy
```

#### Update Container in Deployment Script

Edit `deployment/sagemaker/scripts/deploy_to_sagemaker.py`:

```python
SKLEARN_CONTAINER_IMAGES = {
    'us-east-1': '303440520181.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-sklearn:1.7.2-py310',
    # ... other regions
}
```

### Endpoint Management

#### List Endpoints

```bash
aws sagemaker list-endpoints --region us-east-1
```

#### Describe Endpoint

```bash
aws sagemaker describe-endpoint \
  --endpoint-name ml-ser-endpoint4 \
  --region us-east-1
```

#### Delete Endpoint

```bash
# Delete endpoint
aws sagemaker delete-endpoint \
  --endpoint-name ml-ser-endpoint4 \
  --region us-east-1

# Delete endpoint config
aws sagemaker delete-endpoint-config \
  --endpoint-config-name ml-emotion-v5-config \
  --region us-east-1

# Delete model
aws sagemaker delete-model \
  --model-name ml-emotion-v5 \
  --region us-east-1
```

#### View Logs

```bash
# List log streams
aws logs describe-log-streams \
  --log-group-name /aws/sagemaker/Endpoints/ml-ser-endpoint4 \
  --region us-east-1 \
  --order-by LastEventTime \
  --descending

# Get logs
aws logs get-log-events \
  --log-group-name "/aws/sagemaker/Endpoints/ml-ser-endpoint4" \
  --log-stream-name "AllTraffic/i-09364fce76c352b41" \
  --region us-east-1 \
  --start-from-head
```

### Monitoring

Check CloudWatch for:
- **Request Count**: Number of `/invocations` calls
- **Latency**: Model inference time
- **Error Rate**: 4xx/5xx responses
- **Instance Metrics**: CPU, memory usage

---

## CD Pipeline

### Workflow File

**Location**: `.github/workflows/cd.yml`

### Trigger Events

```yaml
workflow_dispatch:
  inputs:
    model_version:
      description: 'Model version to deploy (e.g., v5)'
      required: true
    endpoint_name:
      description: 'SageMaker endpoint name (e.g., ml-ser-endpoint4)'
      required: false
      default: 'ml-speech-emotion'
```

### Pipeline Steps

#### Job 1: Deploy Model to SageMaker

```yaml
- name: Deploy to SageMaker
  run: |
    python deployment/sagemaker/scripts/deploy_to_sagemaker.py \
      --model-version "$MODEL_VERSION" \
      --endpoint-name "ml-ser-endpoint4" \
      --instance-type ml.t2.medium \
      --s3-uri "$S3_MODEL_URI" \
      --region "us-east-1" \
      --execution-role-arn "arn:aws:iam::303440520181:role/ml-speech-emotion-prod-sagemaker-execution" \
      --timeout 900
```

**What it does:**

1. Validates S3 model package exists
2. Creates SageMaker Model resource
3. Creates Endpoint Configuration
4. Creates or Updates Endpoint
5. Waits for endpoint to reach `InService` (max 900s)

**Timeline:**
- Model creation: ~1s
- Endpoint config creation: ~1s
- Endpoint creation: ~4 min (includes container pull, health checks)

#### Job 2: Deploy to EKS

Updates backend/frontend services to use new SageMaker endpoint.

### Deployment Flow

```
┌─────────────────────┐
│ Trigger Workflow    │
│ (manual/automated)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Checkout Code       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Configure AWS Creds │
│ (via OIDC)          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Validate S3 Package │
│ Exists              │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Run deploy_to_      │
│ sagemaker.py        │
└──────────┬──────────┘
           │
           ├─ Create Model
           ├─ Create Config
           ├─ Create/Update Endpoint
           └─ Wait for InService
           │
           ▼
┌─────────────────────┐
│ Verify Endpoint     │
│ Health              │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Deploy to EKS       │
│ (update backend)    │
└─────────────────────┘
```

---

## Scripts Reference

### 1. `upload_model_to_s3.sh`

**Purpose**: Package and upload model to S3

**Location**: `scripts/upload_model_to_s3.sh`

**Usage**:
```bash
./scripts/upload_model_to_s3.sh <model_version> [--profile <aws-profile>]
```

**Example**:
```bash
./scripts/upload_model_to_s3.sh v5 --profile ml-ser-deploy
```

**What it does**:
1. Creates temp directory
2. Copies files from `backend/models/{version}/`:
   - `model.pkl`
   - `requirements.txt`
   - `metadata.json`
3. Creates `code/` directory with:
   - `inference.py`
   - `ultra_ensemble.py`
4. Creates `model.tar.gz` archive
5. Uploads to S3: `s3://ml-speech-emotion-models-us-east-1/sagemaker-models/{version}/model.tar.gz`
6. Cleans up temp directory

**Key Features**:
- Validates model files exist
- Shows upload progress
- Reports final S3 URI

### 2. `deploy_to_sagemaker.py`

**Purpose**: Deploy model to SageMaker endpoint

**Location**: `deployment/sagemaker/scripts/deploy_to_sagemaker.py`

**Usage**:
```bash
python deploy_to_sagemaker.py \
  --model-version v5 \
  --endpoint-name ml-ser-endpoint4 \
  --instance-type ml.t2.medium \
  --s3-uri s3://ml-speech-emotion-models-us-east-1/sagemaker-models/v5/model.tar.gz \
  --region us-east-1 \
  --execution-role-arn arn:aws:iam::303440520181:role/ml-speech-emotion-prod-sagemaker-execution \
  --timeout 900
```

**Arguments**:
- `--model-version`: Model version (e.g., v5)
- `--endpoint-name`: SageMaker endpoint name
- `--instance-type`: EC2 instance type (ml.t2.medium, ml.m5.large, etc.)
- `--s3-uri`: S3 location of model.tar.gz
- `--region`: AWS region
- `--execution-role-arn`: IAM role for SageMaker
- `--timeout`: Max wait time for endpoint creation (seconds)

**What it does**:

1. **Create Model**:
```python
sagemaker.create_model(
    ModelName='ml-emotion-v5',
    PrimaryContainer={
        'Image': '303440520181.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-sklearn:1.7.2-py310',
        'ModelDataUrl': 's3://ml-speech-emotion-models-us-east-1/sagemaker-models/v5/model.tar.gz'
    },
    ExecutionRoleArn='arn:aws:iam::303440520181:role/ml-speech-emotion-prod-sagemaker-execution'
)
```

2. **Create Endpoint Config**:
```python
sagemaker.create_endpoint_config(
    EndpointConfigName='ml-emotion-v5-config',
    ProductionVariants=[{
        'VariantName': 'AllTraffic',
        'ModelName': 'ml-emotion-v5',
        'InstanceType': 'ml.t2.medium',
        'InitialInstanceCount': 1
    }]
)
```

3. **Create/Update Endpoint**:
```python
# If endpoint doesn't exist
sagemaker.create_endpoint(
    EndpointName='ml-ser-endpoint4',
    EndpointConfigName='ml-emotion-v5-config'
)

# If endpoint exists
sagemaker.update_endpoint(
    EndpointName='ml-ser-endpoint4',
    EndpointConfigName='ml-emotion-v5-config'
)
```

4. **Wait for InService**:
```python
while status == 'Creating':
    time.sleep(30)
    status = describe_endpoint()['EndpointStatus']
```

**Error Handling**:
- Handles "already exists" errors gracefully
- Cannot update in-progress endpoints (waits or fails)
- Provides detailed error messages with CloudWatch log hints

### 3. `build_and_push.sh`

**Purpose**: Build and push custom Docker container to ECR

**Location**: `deployment/sagemaker/container/build_and_push.sh`

**Usage**:
```bash
./build_and_push.sh [--profile <aws-profile>] [--region <region>]
```

**Example**:
```bash
cd deployment/sagemaker/container
./build_and_push.sh --profile ml-ser-deploy
```

**What it does**:
1. Gets AWS account ID
2. Creates ECR repository if needed
3. Logs into ECR
4. Builds Docker image with `--platform linux/amd64`
5. Tags image for ECR
6. Pushes to ECR

**Output**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Building Custom SageMaker Container
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Image Name:  ml-speech-emotion-sklearn
  Image Tag:   1.7.2-py310
  ECR URI:     303440520181.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-sklearn:1.7.2-py310
  Region:      us-east-1
  Account:     303440520181

✓ ECR repository ready
✓ ECR login successful
✓ Docker image built
✓ Image tagged
✓ Image pushed to ECR
```

---

## Custom Container Details

### Dockerfile

**Location**: `deployment/sagemaker/container/Dockerfile`

```dockerfile
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/program:${PATH}"
ENV MODEL_DIR=/opt/ml/model

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    ca-certificates \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    numpy==2.1.0 \
    scikit-learn==1.7.2 \
    scipy>=1.11.0 \
    joblib>=1.3.0 \
    flask>=2.0.0 \
    gunicorn>=21.0.0 \
    gevent>=23.0.0

# Set up the program directory
COPY serve /opt/program/serve
COPY nginx.conf /opt/program/nginx.conf
COPY wsgi.py /opt/program/wsgi.py

RUN chmod +x /opt/program/serve

WORKDIR /opt/program

EXPOSE 8080

ENTRYPOINT ["serve"]
```

### Container Structure

```
/opt/program/
├── serve              # Entry point (starts nginx + gunicorn)
├── nginx.conf         # Nginx config (port 8080)
└── wsgi.py            # Flask app (/ping, /invocations)

/opt/ml/model/         # Mounted by SageMaker
├── model.pkl
├── requirements.txt
├── metadata.json
└── code/
    ├── inference.py
    └── ultra_ensemble.py
```

### Flask Application (wsgi.py)

**Location**: `deployment/sagemaker/container/wsgi.py`

**Key Features**:

1. **UltraEnsembleModel Injection**:
```python
from ultra_ensemble import UltraEnsembleModel
import __main__
__main__.UltraEnsembleModel = UltraEnsembleModel
```
This fixes pickle compatibility when model was saved with class in `__main__`.

2. **Endpoints**:
   - `GET /ping`: Health check (returns 200 if model loaded)
   - `POST /invocations`: Inference endpoint

3. **Request Format**:
```json
{
  "features": [[0.1, 0.2, ..., 0.5]]  // 180 features
}
```

4. **Response Format**:
```json
{
  "predictions": ["happy"],
  "probabilities": [[0.1, 0.2, 0.7, ...]],
  "classes": ["angry", "disgust", "fearful", "happy", "neutral", "sad"]
}
```

### nginx Configuration

**Location**: `deployment/sagemaker/container/nginx.conf`

```nginx
server {
    listen 8080 deferred;
    client_max_body_size 0;
    keepalive_timeout 3;

    location ~ ^/(ping|invocations) {
        proxy_pass http://gunicorn;
        proxy_read_timeout 60s;
    }
}
```

### Entry Point (serve)

**Location**: `deployment/sagemaker/container/serve`

Starts:
1. nginx (port 8080)
2. gunicorn (unix socket)
   - 2 workers (gevent)
   - 60s timeout

---

## Troubleshooting

### Common Issues

#### 1. "exec format error"

**Problem**: Container built on macOS (ARM64) but SageMaker runs x86_64

**Solution**:
```bash
docker build --platform linux/amd64 -t ml-speech-emotion-sklearn:1.7.2-py310 .
```

#### 2. "Can't get attribute 'UltraEnsembleModel' on <module '__main__'>"

**Problem**: Model pickled with custom class in `__main__`

**Solution**: Already fixed in `wsgi.py`:
```python
import __main__
__main__.UltraEnsembleModel = UltraEnsembleModel
```

#### 3. "ModuleNotFoundError: No module named '_loss'"

**Problem**: sklearn version mismatch (model trained with 1.7.2, container has 1.4.2)

**Solution**: Use custom container with sklearn 1.7.2

#### 4. "Cannot update in-progress endpoint"

**Problem**: Previous endpoint still creating/updating

**Solutions**:
- Wait for current operation to complete
- Use a different endpoint name
- Delete endpoint (only works if not in-progress)

#### 5. ECR Permission Denied

**Problem**: SageMaker can't pull custom container from ECR

**Solution**: Add ECR pull policy to SageMaker execution role (see Initial Setup)

#### 6. Endpoint Timeout

**Problem**: Endpoint stuck in "Creating" for 900+ seconds

**Check**:
```bash
# View CloudWatch logs
aws logs get-log-events \
  --log-group-name "/aws/sagemaker/Endpoints/ml-ser-endpoint4" \
  --log-stream-name "AllTraffic/i-xxx" \
  --region us-east-1
```

**Common Causes**:
- Container failing to start (check logs)
- Health check failing (/ping returns non-200)
- Out of memory (worker killed)

#### 7. Model Loading Takes Too Long

**Problem**: Worker timeout during model load

**Solution**: Increase gunicorn timeout in `serve`:
```python
MODEL_SERVER_TIMEOUT = int(os.environ.get('MODEL_SERVER_TIMEOUT', 120))  # Increase from 60
```

### Debugging

#### Test Container Locally

```bash
# Build container
docker build --platform linux/amd64 -t ml-speech-emotion-sklearn:1.7.2-py310 .

# Download model from S3
aws s3 cp s3://ml-speech-emotion-models-us-east-1/sagemaker-models/v5/model.tar.gz .
mkdir -p /tmp/model && tar -xzf model.tar.gz -C /tmp/model

# Run container
docker run -p 8080:8080 \
  -v /tmp/model:/opt/ml/model \
  ml-speech-emotion-sklearn:1.7.2-py310

# Test health check
curl http://localhost:8080/ping

# Test inference
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"features": [[0.1, 0.2, ..., 0.5]]}'
```

#### Check SageMaker Logs

```bash
# Real-time tail
aws logs tail /aws/sagemaker/Endpoints/ml-ser-endpoint4 --follow
```

#### Describe Endpoint

```bash
aws sagemaker describe-endpoint \
  --endpoint-name ml-ser-endpoint4 \
  --region us-east-1 | jq '.'
```

---

## Best Practices

### Data Scientists

1. **Version Control**: Keep model versions in S3 (versioning enabled)
2. **Testing**: Always test locally before uploading
3. **Documentation**: Update metadata.json with training details
4. **Dependencies**: Pin exact versions in requirements.txt
5. **Communication**: Notify MLOps before major deployments

### MLOps Engineers

1. **Container Updates**: Test container changes locally first
2. **Gradual Rollout**: Test on dev endpoint before prod
3. **Monitoring**: Set up CloudWatch alarms for errors/latency
4. **Cost Optimization**: Use smaller instance types for dev
5. **Cleanup**: Delete old endpoints to avoid charges

### Security

1. **IAM Least Privilege**: Only grant necessary permissions
2. **S3 Encryption**: Enable encryption at rest
3. **VPC**: Deploy SageMaker in private VPC (production)
4. **Secret Management**: Use AWS Secrets Manager for sensitive data
5. **Audit Logging**: Enable CloudTrail for SageMaker API calls

---

## Cost Optimization

### Instance Types

| Instance Type | vCPUs | Memory | Price/Hour | Use Case |
|---------------|-------|--------|------------|----------|
| ml.t2.medium | 2 | 4 GB | $0.065 | Dev/Test |
| ml.t3.medium | 2 | 4 GB | $0.062 | Low-traffic prod |
| ml.m5.large | 2 | 8 GB | $0.134 | Production |
| ml.m5.xlarge | 4 | 16 GB | $0.269 | High-traffic |

### Tips

1. **Auto-scaling**: Use auto-scaling for variable traffic
2. **Delete Dev Endpoints**: Stop when not in use
3. **Spot Instances**: Not available for SageMaker, but consider batch transform
4. **Multi-Model Endpoints**: Host multiple models on one endpoint (advanced)

---

## References

- [AWS SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [SageMaker Python SDK](https://sagemaker.readthedocs.io/)
- [Custom Container Guide](https://docs.aws.amazon.com/sagemaker/latest/dg/adapt-inference-container.html)
- [SageMaker Pricing](https://aws.amazon.com/sagemaker/pricing/)
