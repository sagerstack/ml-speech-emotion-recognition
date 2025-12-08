# Implementation Plan: Automated SageMaker Model Deployment

## Metadata
| Field | Value |
|-------|-------|
| ID | US-001-IMPL-PLAN |
| Title | SageMaker Model Deployment |
| User Story ID | US-001 |
| Created | 2025-12-07 |
| Status | Draft |
| Complexity | High |
| Dependencies | Terraform AWS infrastructure, GitHub Actions OIDC, ECR, existing model artifacts |

## Quick Reference
**Tech Stack**: AWS SageMaker, Terraform, GitHub Actions, Docker, Python 3.11, scikit-learn, boto3
**Architectural Pattern**: Infrastructure as Code (Terraform) + CI/CD automation (GitHub Actions)
**Deployment Scope**: Production only (EKS + SageMaker hybrid)

## Requirements Coverage Validation

### Functional Requirements
| Requirement ID | Description | Parent Task | Status |
|----------------|-------------|-------------|--------|
| FR-1 | Auto-detect latest model version from backend/models/ | [5.0][FR-1] (4 subtasks) | [ ] |
| FR-2 | Package model with dependencies for SageMaker inference | [6.0][FR-2] (6 subtasks) | [ ] |
| FR-3 | Deploy model to SageMaker endpoint via CD pipeline | [7.0][FR-3] (5 subtasks) | [ ] |
| FR-4 | Configure backend to use SageMaker endpoint in production | [8.0][FR-4] (4 subtasks) | [ ] |

### Technical Requirements
| Requirement ID | Description | Parent Task | Status |
|----------------|-------------|-------------|--------|
| TR-1 | Terraform provisions SageMaker infrastructure (IAM, ECR, endpoint) | [9.0][TR-1] (7 subtasks) | [ ] |
| TR-2 | Model deployment completes within 15 minutes | [10.0][TR-2] (3 subtasks) | [ ] |
| TR-3 | SageMaker endpoint scales 1-3 instances based on invocations | [11.0][TR-3] (4 subtasks) | [ ] |
| TR-4 | Model versioning tracks deployed model version | [12.0][TR-4] (4 subtasks) | [ ] |

### Acceptance Criteria
| Criteria ID | Description | Parent Task | Unit Tests | Integration Tests | E2E Test | Live Verification |
|-------------|-------------|-------------|------------|-------------------|----------|-------------------|
| AC-1 | CD pipeline auto-deploys latest model to SageMaker on main branch push | [13.0][AC-1] (7 subtasks) | [13.4] | [13.5] | [13.6] | [13.7] |
| AC-2 | Backend routes inference to SageMaker endpoint in prod, local models in dev | [14.0][AC-2] (7 subtasks) | [14.4] | [14.5] | [14.6] | [14.7] |
| AC-3 | SageMaker endpoint returns predictions within 2s p95 latency | [15.0][AC-3] (7 subtasks) | [15.4] | [15.5] | [15.6] | [15.7] |

**Coverage Summary**:
- ✅ Functional Requirements: 4/4 mapped (100%)
- ✅ Technical Requirements: 4/4 mapped (100%)
- ✅ Acceptance Criteria: 3/3 mapped with complete test coverage (100%)

---

## Task-Based Implementation Plan

### Execution Instructions
Complete tasks in order: Manual Prerequisites → Environment & Setup → Functional Requirements → Technical Requirements → Acceptance Criteria → Documentation

---

### 1. Manual Prerequisites

- [ ] **[1.0][MANUAL] AWS Service Limits & Permissions**
  - [ ] [1.1][MANUAL] Verify AWS account has SageMaker service quota for ml.t3.medium instances (minimum 2)
  - [ ] [1.2][MANUAL] Confirm GitHub Actions OIDC IAM role has sagemaker:* permissions
  - [ ] [1.3][MANUAL] Verify ECR repository quota allows additional model image repositories

---

### 2. Environment & Setup

- [ ] **[2.0][SETUP] SageMaker Model Packaging Structure**
  - [ ] [2.1] Create deployment/sagemaker/ directory structure:
    ```
    deployment/sagemaker/
    ├── model_package/
    │   ├── code/
    │   │   ├── inference.py          # SageMaker inference handler
    │   │   ├── feature_extractor.py  # Audio feature extraction
    │   │   └── requirements.txt      # Runtime dependencies
    │   └── Dockerfile                # SageMaker container image
    └── scripts/
        ├── build_model_package.sh    # Package model.tar.gz
        ├── detect_latest_model.sh    # Auto-detect latest version
        └── deploy_to_sagemaker.py    # Deployment orchestration
    ```
  - [ ] [2.2] Copy latest model version detection logic from model_registry.py
  - [ ] [2.3] Create .sagemaker-version file to track deployed model version

- [ ] **[3.0][SETUP] Terraform Module Structure**
  - [ ] [3.1] Create deployment/terraform/modules/sagemaker/ module:
    ```
    modules/sagemaker/
    ├── main.tf           # SageMaker resources
    ├── variables.tf      # Input variables
    ├── outputs.tf        # Endpoint name, model ARN
    ├── iam.tf           # Execution roles
    └── README.md        # Module documentation
    ```
  - [ ] [3.2] Define variables: model_version, instance_type, min_capacity, max_capacity
  - [ ] [3.3] Define outputs: endpoint_name, model_arn, execution_role_arn

- [ ] **[4.0][SETUP] Docker Infrastructure for SageMaker**
  - [ ] [4.1] Create deployment/docker/sagemaker/Dockerfile:
    - Base image: python:3.11-slim
    - Install: scikit-learn, librosa, numpy, pandas, boto3
    - Copy: inference.py, feature_extractor.py, model.pkl
    - Entry point: SageMaker inference server
  - [ ] [4.2] Add multi-stage build for optimized image size
  - [ ] [4.3] Configure health check endpoint for SageMaker

---

### 3. Functional Requirements

- [ ] **[5.0][FR-1] Auto-detect Latest Model Version**
  - [ ] [5.1] Implement detect_latest_model.sh script:
    - Scan backend/models/ for version directories (v1, v2, v3, ...)
    - Extract version numbers and sort descending
    - Return latest version (e.g., "v5")
  - [ ] [5.2] Validate model.pkl exists in detected version directory
  - [ ] [5.3] Write version to .sagemaker-version file for tracking
  - [ ] [5.4] Unit test: verify detection with multiple versions, single version, no versions

- [ ] **[6.0][FR-2] Package Model with Dependencies for SageMaker**
  - [ ] [6.1] Implement build_model_package.sh script:
    - Copy model.pkl from backend/models/v{x}/ to deployment/sagemaker/model_package/
    - Copy feature_extractor.py from backend/app/infrastructure/model/v{x}/
    - Copy metadata.json for model configuration
  - [ ] [6.2] Create model.tar.gz archive with structure:
    ```
    model.tar.gz
    ├── code/
    │   ├── inference.py
    │   ├── feature_extractor.py
    │   └── requirements.txt
    ├── model.pkl
    └── metadata.json
    ```
  - [ ] [6.3] Validate archive integrity and file permissions
  - [ ] [6.4] Upload model.tar.gz to S3: s3://{bucket}/sagemaker/models/v{x}/model.tar.gz
  - [ ] [6.5] Compute SHA256 checksum for version validation
  - [ ] [6.6] Unit test: verify archive structure, S3 upload, checksum calculation

- [ ] **[7.0][FR-3] Deploy Model to SageMaker Endpoint via CD**
  - [ ] [7.1] Implement deploy_to_sagemaker.py orchestration script:
    - Create SageMaker model from S3 model.tar.gz
    - Create endpoint configuration with instance type and scaling
    - Create or update endpoint with new model version
  - [ ] [7.2] Handle endpoint update vs. create logic (idempotent deployment)
  - [ ] [7.3] Wait for endpoint InService status (timeout: 15 minutes)
  - [ ] [7.4] Tag endpoint with model_version, git_commit_sha, deployed_at
  - [ ] [7.5] Unit test: verify boto3 API calls, error handling, timeout logic

- [ ] **[8.0][FR-4] Configure Backend for SageMaker Endpoint**
  - [ ] [8.1] Update backend/app/infrastructure/config.py:
    - Add USE_SAGEMAKER environment variable (default: false)
    - Add SAGEMAKER_ENDPOINT_NAME configuration
    - Add runtime detection: production → SageMaker, local → file system
  - [ ] [8.2] Update model repository to route based on environment:
    - If USE_SAGEMAKER=true → use sagemaker_client.py
    - Else → use file_system_model_repository.py
  - [ ] [8.3] Update deployment/k8s/prod/configmap.yaml with USE_SAGEMAKER=true
  - [ ] [8.4] Unit test: verify routing logic for both environments

---

### 4. Technical Requirements

- [ ] **[9.0][TR-1] Terraform SageMaker Infrastructure Provisioning**
  - [ ] [9.1] Create modules/sagemaker/iam.tf:
    - SageMaker execution role with ECR pull, S3 read, CloudWatch logs permissions
    - Trust relationship: sagemaker.amazonaws.com
  - [ ] [9.2] Create modules/sagemaker/main.tf:
    - aws_sagemaker_model resource referencing S3 model.tar.gz
    - aws_sagemaker_endpoint_configuration with ml.t3.medium instance
    - aws_sagemaker_endpoint with auto-scaling enabled
  - [ ] [9.3] Configure ECR repository for SageMaker model images:
    - Repository: ml-speech-emotion-sagemaker
    - Lifecycle policy: keep last 5 model versions
  - [ ] [9.4] Add S3 bucket for model artifacts:
    - Bucket: {project_name}-sagemaker-models-{region}
    - Versioning enabled, encryption at rest
  - [ ] [9.5] Update deployment/terraform/main.tf to include sagemaker module
  - [ ] [9.6] Update deployment/terraform/outputs.tf with sagemaker_endpoint_name
  - [ ] [9.7] Run terraform plan to validate configuration

- [ ] **[10.0][TR-2] Model Deployment Timeout <15 Minutes**
  - [ ] [10.1] Configure SageMaker endpoint creation timeout: 900 seconds
  - [ ] [10.2] Add exponential backoff for status polling (5s → 10s → 20s intervals)
  - [ ] [10.3] Unit test: verify timeout enforcement and status polling logic

- [ ] **[11.0][TR-3] Auto-Scaling Configuration**
  - [ ] [11.1] Configure Application Auto Scaling target:
    - Min capacity: 1 instance
    - Max capacity: 3 instances
  - [ ] [11.2] Configure scaling policy:
    - Metric: SageMakerVariantInvocationsPerInstance
    - Target value: 100 invocations per instance
  - [ ] [11.3] Add scale-in cooldown: 300 seconds
  - [ ] [11.4] Unit test: verify auto-scaling configuration in Terraform plan

- [ ] **[12.0][TR-4] Model Version Tracking**
  - [ ] [12.1] Tag SageMaker endpoint with:
    - model_version: v{x}
    - git_commit_sha: {commit}
    - deployed_at: {timestamp}
  - [ ] [12.2] Store deployment metadata in S3: deployments/{version}/metadata.json
  - [ ] [12.3] Update backend /health endpoint to return deployed model version
  - [ ] [12.4] Unit test: verify metadata creation and tagging

---

### 5. Acceptance Criteria

- [ ] **[13.0][AC-1] CD Pipeline Auto-Deploys Latest Model on Main Branch Push**
  - [ ] [13.1] Update .github/workflows/cd.yml with new job: deploy-model-to-sagemaker
    - Trigger: push to main branch, paths: backend/models/**
    - Steps: detect latest model → build package → upload S3 → deploy endpoint
  - [ ] [13.2] Add job dependencies: deploy-model-to-sagemaker runs before eks-deployment
  - [ ] [13.3] Configure AWS credentials using OIDC (existing setup)
  - [ ] [13.4] Write unit tests: verify workflow syntax, job dependencies, trigger paths
  - [ ] [13.5] Write integration tests: mock GitHub Actions runner, verify job execution flow
  - [ ] [13.6] **E2E Test**:
    ```bash
    # Commit new model version to main
    git checkout main
    cp -r backend/models/v5 backend/models/v6
    git add backend/models/v6
    git commit -m "test: add v6 model for E2E testing"
    git push origin main

    # Wait for CD pipeline completion
    gh run watch

    # Verify SageMaker endpoint updated
    aws sagemaker describe-endpoint --endpoint-name ml-emotion-prod
    endpoint_model=$(aws sagemaker describe-endpoint --endpoint-name ml-emotion-prod --query 'EndpointConfigName' --output text)
    echo "$endpoint_model" | grep -q "v6" || exit 1

    echo "✅ AC-1 E2E test passed"
    ```
  - [ ] [13.7] **Live Environment Verification**:
    - Deploy to production via GitHub Actions CD pipeline
    - Verify SageMaker endpoint shows InService status
    - Verify endpoint tags include latest model version
    - Document evidence: AWS console screenshot, endpoint describe output

- [ ] **[14.0][AC-2] Backend Routes to SageMaker in Prod, Local Models in Dev**
  - [ ] [14.1] Implement environment-based routing in model repository
  - [ ] [14.2] Update K8s prod configmap: USE_SAGEMAKER=true, SAGEMAKER_ENDPOINT_NAME={from terraform output}
  - [ ] [14.3] Keep local deployment unchanged: USE_SAGEMAKER=false (default)
  - [ ] [14.4] Write unit tests: verify routing returns SageMaker client when USE_SAGEMAKER=true
  - [ ] [14.5] Write integration tests: verify full inference flow with mocked SageMaker endpoint
  - [ ] [14.6] **E2E Test**:
    ```bash
    # Test local deployment
    ./scripts/local-deploy.sh
    response=$(curl -s http://localhost:8000/api/v1/health)
    echo "$response" | grep -q "model_source.*local" || exit 1

    # Test production deployment (assumes deployed via CD)
    kubectl port-forward -n ml-speech-emotion svc/backend 8000:8000 &
    sleep 5
    response=$(curl -s http://localhost:8000/api/v1/health)
    echo "$response" | grep -q "model_source.*sagemaker" || exit 1

    echo "✅ AC-2 E2E test passed"
    ```
  - [ ] [14.7] **Live Environment Verification**:
    - Deploy to production EKS cluster
    - Call /health endpoint and verify model_source=sagemaker
    - Call /predict endpoint and verify inference succeeds
    - Verify CloudWatch logs show SageMaker endpoint invocations

- [ ] **[15.0][AC-3] SageMaker Endpoint p95 Latency <2s**
  - [ ] [15.1] Implement performance instrumentation in sagemaker_client.py:
    - Record invocation latency with histogram metric
    - Export p50, p95, p99 latencies to Prometheus
  - [ ] [15.2] Create load test script: send 1000 inference requests
  - [ ] [15.3] Calculate latency percentiles from recorded metrics
  - [ ] [15.4] Write unit tests: verify latency instrumentation logic
  - [ ] [15.5] Write integration tests: verify metrics export to Prometheus
  - [ ] [15.6] **E2E Test**:
    ```bash
    # Run load test against SageMaker endpoint
    poetry run python scripts/load_test_sagemaker.py --requests 1000 --endpoint ml-emotion-prod

    # Verify p95 latency <2s
    p95_latency=$(poetry run python scripts/load_test_sagemaker.py --requests 1000 --endpoint ml-emotion-prod | grep "p95" | awk '{print $2}')
    test $(echo "$p95_latency < 2.0" | bc) -eq 1 || exit 1

    echo "✅ AC-3 E2E test passed: p95 latency = ${p95_latency}s"
    ```
  - [ ] [15.7] **Live Environment Verification**:
    - Run load test against production SageMaker endpoint
    - Query Prometheus for sagemaker_invocation_latency_seconds metric
    - Verify p95 latency <2s from Grafana dashboard
    - Document evidence: Grafana screenshot, load test results

---

### 6. Documentation & Deployment

- [ ] **[16.0][DOC] Developer Documentation**
  - [ ] [16.1] Create deployment/sagemaker/README.md:
    - SageMaker architecture diagram
    - Model packaging workflow
    - Deployment process documentation
  - [ ] [16.2] Update main README.md with SageMaker deployment section
  - [ ] [16.3] Document troubleshooting: endpoint failures, scaling issues, version rollback
  - [ ] [16.4] Add inline documentation to all SageMaker-related code

- [ ] **[17.0][DOC] Terraform Documentation**
  - [ ] [17.1] Document SageMaker module variables and outputs
  - [ ] [17.2] Add example usage in deployment/terraform/README.md
  - [ ] [17.3] Document required IAM permissions for GitHub Actions
  - [ ] [17.4] Add cost estimation for SageMaker infrastructure

- [ ] **[18.0][DOC] CI/CD Pipeline Updates**
  - [ ] [18.1] Update .github/workflows/cd.yml with clear comments for SageMaker deployment steps
  - [ ] [18.2] Add monitoring for CD pipeline SageMaker deployment stage
  - [ ] [18.3] Document rollback procedure for failed deployments

- [ ] **[19.0][DOC] Code Quality & Version Control**
  - [ ] [19.1] Run code formatter: black on all Python files
  - [ ] [19.2] Run linter: flake8 on all Python files
  - [ ] [19.3] Run terraform fmt on all Terraform files
  - [ ] [19.4] Fix all linting and formatting issues
  - [ ] [19.5] Create feature branch: feature/sagemaker-deployment
  - [ ] [19.6] Commit changes with message: "feat: add automated SageMaker model deployment"
  - [ ] [19.7] Push to GitHub and create pull request

---

## Implementation Summary

### Key Changes Overview

#### 1. **Terraform Changes** (deployment/terraform/)
- **New Module**: `modules/sagemaker/` with IAM roles, SageMaker model, endpoint configuration, endpoint
- **S3 Bucket**: Model artifacts storage with versioning and encryption
- **ECR Repository**: SageMaker model container images
- **Outputs**: Export sagemaker_endpoint_name to K8s configmap

#### 2. **GitHub Actions CD Changes** (.github/workflows/cd.yml)
- **New Job**: `deploy-model-to-sagemaker`
  - Detect latest model version from backend/models/
  - Build model.tar.gz package
  - Upload to S3
  - Deploy to SageMaker endpoint
  - Tag endpoint with version metadata
- **Trigger**: Push to main branch with changes to backend/models/**
- **Dependencies**: Runs before EKS deployment job

#### 3. **SageMaker Model Packaging** (deployment/sagemaker/)
- **Directory Structure**: model_package/, scripts/
- **Dockerfile**: SageMaker-compatible container with inference handler
- **Scripts**:
  - detect_latest_model.sh - Auto-detect latest version
  - build_model_package.sh - Create model.tar.gz
  - deploy_to_sagemaker.py - Orchestrate deployment

#### 4. **Backend Configuration Changes**
- **Config**: Add USE_SAGEMAKER, SAGEMAKER_ENDPOINT_NAME environment variables
- **Model Repository**: Route to SageMaker client if USE_SAGEMAKER=true, else local models
- **K8s Prod Configmap**: Set USE_SAGEMAKER=true
- **Local Deployment**: Keep USE_SAGEMAKER=false (no change to local/k8s dev)

#### 5. **Monitoring & Observability**
- **Metrics**: SageMaker invocation latency (p50, p95, p99)
- **Logs**: SageMaker endpoint CloudWatch logs
- **Health Check**: /health endpoint returns model source (sagemaker vs local)

### Deployment Flow

```
┌──────────────────────────────────────────────────────────────┐
│  Developer pushes model v{x} to main branch                  │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  GitHub Actions CI/CD Pipeline (.github/workflows/cd.yml)    │
├──────────────────────────────────────────────────────────────┤
│  Job 1: deploy-model-to-sagemaker                            │
│    1. Detect latest model: v{x}                              │
│    2. Build model.tar.gz (model.pkl + inference.py + deps)   │
│    3. Upload to S3: sagemaker/models/v{x}/model.tar.gz       │
│    4. Create/Update SageMaker model                          │
│    5. Create/Update endpoint configuration                   │
│    6. Deploy endpoint (wait for InService, timeout 15min)    │
│    7. Tag endpoint: model_version=v{x}, commit_sha, timestamp│
│                                                              │
│  Job 2: deploy-to-eks (depends on Job 1)                     │
│    1. Get sagemaker_endpoint_name from Terraform output      │
│    2. Update K8s configmap: SAGEMAKER_ENDPOINT_NAME=...      │
│    3. Deploy backend/streamlit to EKS                        │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  AWS Infrastructure (Terraform-managed)                       │
├──────────────────────────────────────────────────────────────┤
│  SageMaker:                                                  │
│    - Endpoint: ml-emotion-prod (InService)                   │
│    - Instance: ml.t3.medium (1-3 instances, auto-scaling)    │
│    - Model: v{x} from S3                                     │
│                                                              │
│  EKS Cluster:                                                │
│    - Backend pods: USE_SAGEMAKER=true                        │
│    - Inference routed to SageMaker endpoint                  │
│                                                              │
│  Monitoring:                                                 │
│    - Prometheus: SageMaker invocation metrics                │
│    - CloudWatch: Endpoint logs and performance metrics       │
└──────────────────────────────────────────────────────────────┘
```

### No Impact to Local/Dev Environments
- Local deployment: `./scripts/local-deploy.sh` continues using local models
- K8s dev: No changes, USE_SAGEMAKER remains false
- Only production (EKS via CD pipeline) uses SageMaker

---

## Changelog
| Date | Author | Summary | Sections Affected | Reason |
|------|--------|---------|------------------|--------|
| 2025-12-07 | Solution Architect | Initial implementation plan creation | All sections | SageMaker deployment planning |

---

*Implementation plan provides comprehensive task breakdown for automated SageMaker model deployment integrated with existing Terraform infrastructure and GitHub Actions CD pipeline.*
