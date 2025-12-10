# Machine Learning Speech Emotion Recognition

## Project Structure

```
ml-speech-emotion-recognition/
├── backend/                      # FastAPI backend service (Clean Architecture)
│   ├── app/
│   │   ├── api/                 # API endpoints
│   │   │   ├── v1/              # API version 1 (monitoring endpoints)
│   │   │   └── v2/              # API version 2 (inference endpoints)
│   │   ├── domain/              # Domain models and business logic
│   │   │   ├── entities/        # Domain entities (Emotion, Confidence, etc.)
│   │   │   ├── errors/          # Domain-specific errors
│   │   │   └── value_objects/   # Value objects
│   │   ├── infrastructure/      # Infrastructure implementations
│   │   │   ├── config/          # Configuration management
│   │   │   ├── model/           # Model adapters (SageMaker, local)
│   │   │   ├── monitoring/      # Evidently AI monitoring service
│   │   │   └── observability/   # Logging, metrics, tracing (OpenTelemetry)
│   │   ├── use_cases/           # Application use cases
│   │   │   ├── inference/       # Emotion prediction use cases
│   │   │   └── monitoring/      # Monitoring use cases
│   │   └── main.py              # Application entry point
│   ├── evidently_workspace/     # Evidently AI workspace
│   ├── models/                  # Local ML model versions
│   │   ├── v4/                  # Model version 4
│   │   ├── v5/                  # Model version 5
│   │   └── v6/                  # Model version 6 (current)
│   ├── monitoring_data/         # Reference datasets for monitoring
│   ├── monitoring_reports/      # Generated Evidently reports
│   ├── scripts/                 # Backend utility scripts
│   ├── tests/                   # Test suite
│   │   ├── unit/                # Unit tests
│   │   ├── integration/         # Integration tests
│   │   ├── e2e/                 # End-to-end tests
│   │   └── fixtures/            # Test fixtures
│   ├── pyproject.toml           # Poetry configuration
│   ├── poetry.lock              # Poetry lock file
│   └── Makefile                 # Development tasks
│
├── frontend/                     # Streamlit frontend application
│   └── streamlit_app/
│       ├── src/
│       │   ├── pages/           # Multi-page Streamlit app
│       │   │   ├── 1_History.py        # Prediction history
│       │   │   ├── 2_Metrics.py        # Model metrics
│       │   │   └── 3_Monitoring.py     # Model monitoring
│       │   ├── ml-app.py        # Main app entry point
│       │   ├── api_client.py    # Backend API client
│       │   └── feature_charts.py # Audio feature visualizations
│       └── pyproject.toml
│
├── data/                         # Training datasets (gitignored)
│   ├── AudioWAV/                # CREMA-D dataset (7,442 audio files)
│   └── ravdess-speech-audio/    # RAVDESS dataset
│
├── deployment/                   # Deployment configurations
│   ├── aws/                     # AWS-specific configurations
│   ├── docker/                  # Dockerfiles
│   │   ├── backend/             # Backend Docker configuration
│   │   └── streamlit/           # Frontend Docker configuration
│   ├── iam/                     # IAM policy documents
│   ├── k8s/                     # Kubernetes manifests
│   │   ├── local/               # Local K8s (Minikube/Kind)
│   │   └── prod/                # Production EKS
│   ├── monitoring/              # Monitoring stack (Grafana, Prometheus, Loki, Tempo)
│   ├── sagemaker/               # SageMaker deployment
│   │   └── container/           # Custom SageMaker container
│   ├── scripts/                 # Deployment automation scripts
│   └── terraform/               # Infrastructure as Code (EKS, VPC, ECR)
│
├── notebooks/                    # Jupyter notebooks
│   └── models/                  # Model development and training
│
├── sagemaker/                    # AWS SageMaker integration
│   ├── docs/                    # SageMaker documentation
│   ├── model-deployment/        # Deployment notebooks
│   └── scripts/                 # SageMaker utility scripts
│
├── scripts/                      # Project-wide utility scripts
│   ├── upload_model_to_s3.sh   # S3 model upload
│   ├── local-deploy.sh         # Local K8s deployment
│   ├── tf-deploy.sh            # Terraform deployment
│   └── tf-destroy.sh           # Terraform destroy
│
├── specs/                        # Feature specifications
│   ├── 001-model-deployment-api/
│   ├── 002-streamlit-app/
│   └── us-*/                    # User story specifications
│
├── docs/                         # Documentation
│   ├── architecture-diagrams/   # System architecture diagrams
│   ├── ops/                     # Operations documentation
│   ├── deployment-sagemaker.md  # SageMaker deployment guide
│   └── *.md                     # Various guides
│
├── .github/
│   └── workflows/               # GitHub Actions CI/CD
│       ├── ci.yml              # CI pipeline
│       └── cd.yml              # CD pipeline
│
├── .claude/                      # Claude Code configuration
│   ├── agents/                  # Custom agents
│   ├── commands/                # Slash commands
│   └── skills/                  # Custom skills
│
├── docker-compose.yml            # Local development stack
├── pyproject.toml               # Root Poetry configuration
├── poetry.lock                  # Root lock file
├── CLAUDE.md                    # Claude Code instructions
└── README.md                    # This file
```

## Key Components

### Backend Architecture (Clean Architecture)
- **Domain Layer**: Core business logic, entities, and value objects
- **Use Cases**: Application-specific business rules
- **Infrastructure**: External services (SageMaker, S3, monitoring)
- **API**: RESTful endpoints with versioning (v1 for monitoring, v2 for inference)
- **Observability**: Full stack with OpenTelemetry, Prometheus, Loki, Tempo

### Frontend
- **Streamlit**: Multi-page web application
- **Real-time Inference**: Audio upload and emotion prediction
- **Monitoring Dashboard**: Evidently AI reports and metrics visualization
- **History**: Prediction history and feedback system

### ML Models
- **Local Models**: Scikit-learn models (v4, v5, v6)
- **SageMaker Models**: Production deployment on AWS SageMaker
- **Feature Extraction**: MFCC, spectral, and prosodic features using Librosa

### Deployment Options
1. **Local Development**: Poetry + Uvicorn + Streamlit
2. **Docker Compose**: Full-stack local deployment
3. **Kubernetes (Local)**: Minikube/Kind with monitoring stack
4. **AWS EKS**: Production Kubernetes with Terraform IaC
5. **AWS SageMaker**: Serverless ML inference endpoints

### Observability Stack
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Metrics and logs visualization
- **Loki**: Log aggregation
- **Tempo**: Distributed tracing
- **Evidently AI**: ML model monitoring and drift detection

### Datasets
- **CREMA-D**: 7,442 audio clips, 91 actors, 6 emotions
- **RAVDESS**: Supplementary dataset for training

---

## Clean Architecture & Testing Strategy

### Backend Clean Architecture

The backend follows **Clean Architecture** principles with clear separation of concerns across layers:

```
backend/app/
│
├── domain/                          # 🏛️ Domain Layer (Enterprise Business Rules)
│   ├── model/                       # ML Model domain
│   │   ├── entities/                # Core domain entities
│   │   │   ├── emotion.py          # Emotion enum (angry, happy, sad, etc.)
│   │   │   ├── confidence.py       # Confidence value object (0.0-1.0)
│   │   │   └── model_version.py    # Model version entity (v4, v5, v6)
│   │   ├── value_objects/          # Immutable value objects
│   │   │   └── audio_metadata.py   # Audio file metadata
│   │   ├── exceptions/             # Domain-specific exceptions
│   │   │   ├── prediction_failed_error.py
│   │   │   ├── sagemaker_throttling_error.py
│   │   │   └── invalid_audio_error.py
│   │   ├── repositories/           # Repository interfaces (ports)
│   │   │   └── model_repository.py # Abstract model repository
│   │   └── services/               # Domain services
│   │       └── emotion_model.py    # Model interface contract
│   │
│   ├── monitoring/                 # Monitoring domain
│   │   ├── entities/               # Monitoring entities
│   │   │   └── prediction.py       # Prediction record for monitoring
│   │   ├── repositories/           # Monitoring repository interfaces
│   │   │   └── prediction_repository.py
│   │   └── services/               # Monitoring service interfaces
│   │       └── monitoring_service.py
│   │
│   └── interfaces/                 # Cross-cutting domain interfaces
│       └── audio_processor.py      # Audio processing interface
│
├── use_cases/                      # 💼 Use Case Layer (Application Business Rules)
│   ├── model/                      # ML inference use cases
│   │   ├── run_inference.py        # Execute emotion prediction
│   │   ├── get_model_info.py       # Retrieve model metadata
│   │   └── get_model_versions.py   # List available models
│   │
│   └── monitoring/                 # Monitoring use cases
│       ├── generate_report.py      # Generate Evidently reports
│       ├── log_prediction_for_monitoring.py
│       └── set_actual_emotion.py   # Update with ground truth
│
├── infrastructure/                 # 🔌 Infrastructure Layer (Frameworks & Drivers)
│   ├── model/                      # Model implementations (adapters)
│   │   ├── file_system_model_repository.py  # Local model storage
│   │   ├── sagemaker_emotion_model_adapter.py  # SageMaker integration
│   │   ├── emotion_model_adapter.py  # Local scikit-learn models
│   │   └── v4/, v5/                # Model-specific implementations
│   │
│   ├── audio/                      # Audio processing implementations
│   │   └── librosa_audio_processor.py  # Librosa-based feature extraction
│   │
│   ├── monitoring/                 # Monitoring implementations
│   │   └── evidently_service.py    # Evidently AI integration
│   │
│   ├── observability/              # Observability stack
│   │   ├── logging/                # Structured logging
│   │   ├── metrics/                # Prometheus metrics
│   │   └── tracing/                # OpenTelemetry tracing
│   │
│   ├── config/                     # Configuration management
│   │   ├── settings.py             # Application settings
│   │   └── feature_flags.py        # Feature toggles
│   │
│   ├── di/                         # Dependency Injection
│   │   ├── container.py            # DI container
│   │   └── providers.py            # Dependency providers
│   │
│   └── validation/                 # Input validation
│       └── file_validation.py      # Audio file validation
│
└── api/                            # 🌐 API Layer (Interface Adapters)
    ├── v1/endpoints/               # API v1 (monitoring)
    │   └── monitoring.py           # Monitoring endpoints
    │
    └── v2/endpoints/               # API v2 (inference)
        └── inference.py            # Clean architecture inference endpoints
```

### Clean Architecture Benefits

1. **Independence of Frameworks**: Business logic doesn't depend on FastAPI, SageMaker, or Evidently
2. **Testability**: Each layer can be tested in isolation with mocks
3. **Independence of UI**: API layer can be swapped (REST → GraphQL) without changing business logic
4. **Independence of Database**: Model storage can switch (filesystem → S3 → database)
5. **Maintainability**: Clear boundaries make code easier to understand and modify

### Dependency Rule

Dependencies point **inward** only:
- **Domain** → Has no dependencies (pure business logic)
- **Use Cases** → Depends only on domain
- **Infrastructure** → Implements domain interfaces
- **API** → Orchestrates use cases, converts HTTP ↔ domain models

---

## Testing Strategy

### Test Pyramid

The project implements a comprehensive test pyramid with three levels:

```
backend/tests/
│
├── unit/                           # 🔬 Unit Tests (Fast, Isolated)
│   ├── domain/                     # Domain logic tests
│   │   ├── test_emotion.py         # Emotion enum validation
│   │   ├── test_confidence.py      # Confidence value object
│   │   └── test_model_version.py   # Model version entity
│   │
│   ├── use_cases/                  # Use case tests (mocked dependencies)
│   │   ├── test_run_inference.py   # Inference logic
│   │   └── test_generate_report.py # Monitoring report generation
│   │
│   ├── infrastructure/             # Infrastructure tests (mocked external services)
│   │   ├── model/
│   │   │   ├── test_sagemaker_emotion_model_adapter.py
│   │   │   └── test_file_system_model_repository.py
│   │   └── monitoring/
│   │       └── test_evidently_service.py
│   │
│   └── api/                        # API endpoint tests (mocked use cases)
│       ├── v1/
│       │   └── test_monitoring_endpoint.py
│       └── v2/
│           └── test_inference_endpoint.py
│
├── integration/                    # 🔗 Integration Tests (Multiple Components)
│   └── infrastructure/
│       ├── test_model_loading.py   # Real model loading + feature extraction
│       ├── test_audio_processing.py # Librosa integration with real audio files
│       └── test_prediction_repository.py # Database/storage integration
│
├── e2e/                            # 🎯 End-to-End Tests (Full System)
│   ├── test_inference_flow.py      # Complete inference: upload → predict → monitor
│   ├── test_monitoring_flow.py     # Full monitoring: predictions → drift detection
│   └── test_api_v2_inference.py    # HTTP request → response validation
│
├── fixtures/                       # Test Data & Utilities
│   ├── audio_files.py              # Sample audio file fixtures
│   ├── mock_models.py              # Mock model implementations
│   └── sagemaker_responses.py      # SageMaker response mocks
│
├── test_data/                      # Static Test Data
│   ├── sample_responses/           # Mock API responses
│   └── sample_audio/               # Test audio files
│
└── utils/                          # Test Utilities
    ├── assertions.py               # Custom test assertions
    └── helpers.py                  # Test helper functions
```

### Test Types Explained

#### 1. Unit Tests (70% of tests)
- **Purpose**: Test individual components in isolation
- **Speed**: Very fast (milliseconds)
- **Dependencies**: All external dependencies mocked
- **Coverage**: Domain logic, use cases, individual adapters
- **Example**:
  ```python
  # tests/unit/domain/test_emotion.py
  def test_emotion_from_string():
      assert Emotion.from_string("happy") == Emotion.HAPPY

  # tests/unit/use_cases/test_run_inference.py
  def test_inference_with_mocked_model(mock_model_repository):
      # All dependencies injected as mocks
      use_case = RunInferenceUseCase(mock_model_repository)
      result = use_case.execute(audio_bytes, version="v6")
      assert result.emotion == Emotion.HAPPY
  ```

#### 2. Integration Tests (20% of tests)
- **Purpose**: Test interaction between components
- **Speed**: Moderate (seconds)
- **Dependencies**: Real implementations, no external services
- **Coverage**: Model loading + feature extraction, audio processing, repository operations
- **Example**:
  ```python
  # tests/integration/infrastructure/test_model_loading.py
  def test_load_real_model_and_extract_features():
      # Uses real model files and Librosa
      model_repo = FileSystemModelRepository()
      audio_processor = LibrosaAudioProcessor()

      model = model_repo.get_model("v6")
      features = audio_processor.extract_features(audio_bytes)
      predictions = model.predict(features)

      assert len(predictions) == 6  # All emotion probabilities
  ```

#### 3. End-to-End Tests (10% of tests)
- **Purpose**: Test complete user workflows
- **Speed**: Slow (seconds to minutes)
- **Dependencies**: Full application stack (may use test doubles for external APIs)
- **Coverage**: API endpoints, complete use case flows, monitoring integration
- **Example**:
  ```python
  # tests/e2e/test_inference_flow.py
  def test_complete_inference_workflow(test_client):
      # Upload audio file
      response = test_client.post(
          "/v2/inference/",
          files={"file": ("test.wav", audio_bytes)}
      )

      assert response.status_code == 200
      data = response.json()

      # Verify prediction
      assert "prediction" in data
      assert data["prediction"]["emotion"] in ["happy", "sad", "angry", ...]

      # Verify monitoring recorded prediction
      prediction_id = data["prediction"]["prediction_id"]
      monitoring_response = test_client.get(f"/v1/monitoring/predictions/{prediction_id}")
      assert monitoring_response.status_code == 200
  ```

### Test Execution

```bash
# Run all tests
make test

# Run specific test level
pytest tests/unit/              # Fast unit tests only
pytest tests/integration/       # Integration tests
pytest tests/e2e/              # End-to-end tests

# Run with coverage
make test-coverage

# Run specific module
pytest tests/unit/use_cases/test_run_inference.py -v
```

### Test Coverage Goals

- **Overall**: >85%
- **Domain Layer**: 100% (critical business logic)
- **Use Cases**: >95% (application logic)
- **Infrastructure**: >80% (adapter implementations)
- **API Layer**: >90% (endpoint coverage)

### Continuous Integration

All tests run automatically on:
- **Pull Requests**: Full test suite must pass
- **Main Branch**: Tests + code quality checks + security scans
- **Pre-commit Hooks**: Unit tests for changed files

---

## Model Deployment Pipeline

### End-to-End Deployment Flow

The project implements a production-grade ML model deployment pipeline from local training to SageMaker endpoints:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: Local Model Development & Training                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    [Jupyter Notebook: Model Training]
                                    │
                         Train scikit-learn model
                         (Random Forest, SVM, etc.)
                                    │
                                    ▼
                    ┌──────────────────────────┐
                    │  backend/models/v6/      │
                    │  ├── model.pkl           │  ← Trained model (680+ MB)
                    │  ├── metadata.json       │  ← Model config & metrics
                    │  ├── inference.py        │  ← SageMaker handler
                    │  └── requirements.txt    │  ← Dependencies
                    └──────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Model Packaging & S3 Upload                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ./scripts/upload_model_to_s3.sh v6
                                    │
                    ┌──────────────────────────┐
                    │ Package Structure:       │
                    │ /tmp/sagemaker_package/  │
                    │ ├── model.pkl            │  ← Root level
                    │ ├── metadata.json        │  ← Root level
                    │ └── code/                │
                    │     ├── inference.py     │  ← /opt/ml/model/code/
                    │     └── requirements.txt │  ← SageMaker reads this
                    └──────────────────────────┘
                                    │
                         tar -czf model.tar.gz .
                                    │
                                    ▼
                    ┌──────────────────────────┐
                    │ S3 Upload                │
                    │ s3://ml-speech-emotion-  │
                    │   models-us-east-1/      │
                    │   sagemaker-models/v6/   │
                    │   └── model.tar.gz       │
                    └──────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: Custom SageMaker Container (Pre-built & Pushed to ECR)        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    [One-time container build]
                                    │
        deployment/sagemaker/container/Dockerfile
                    │
                    ├── Base: python:3.10-slim
                    ├── Install: scikit-learn==1.7.2, numpy==2.1.0
                    ├── Add: nginx + gunicorn + Flask
                    └── Copy: serve script (entrypoint)
                                    │
                    docker build -t ml-speech-emotion-sklearn:1.7.2-py310
                                    │
                    docker push → ECR
                                    │
                                    ▼
        303440520181.dkr.ecr.us-east-1.amazonaws.com/
            ml-speech-emotion-sklearn:1.7.2-py310
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: SageMaker Model Deployment                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        deployment/sagemaker/scripts/deploy_to_sagemaker.py
                    │
                    ├─► Step 1: Create SageMaker Model
                    │   ├── Model Name: ml-emotion-v6
                    │   ├── Container Image: ECR URI (sklearn 1.7.2)
                    │   ├── Model Data: s3://.../v6/model.tar.gz
                    │   └── Environment:
                    │       ├── SAGEMAKER_PROGRAM=inference.py
                    │       ├── SAGEMAKER_SUBMIT_DIRECTORY=/opt/ml/model/code
                    │       └── MODEL_VERSION=v6
                    │
                    ├─► Step 2: Create Endpoint Configuration
                    │   ├── Config Name: ml-emotion-v6-config
                    │   ├── Instance Type: ml.t2.medium
                    │   ├── Initial Instance Count: 1
                    │   └── Production Variant: AllTraffic (100% weight)
                    │
                    └─► Step 3: Create/Update Endpoint
                        ├── Endpoint Name: ml-ser-v1 (auto-versioned)
                        ├── Config: ml-emotion-v6-config
                        ├── Wait for InService (up to 15 min)
                        └── Status Polling: Every 10-30s
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: Production Endpoint (Ready for Inference)                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    SageMaker Endpoint: ml-ser-v1
                    ├── Status: InService
                    ├── Instance: ml.t2.medium (1 instance)
                    ├── Model: v6 (680 MB loaded in memory)
                    └── Inference API: invoke_endpoint()
                                    │
                    ┌──────────────────────────┐
                    │ Request Flow:            │
                    │ Client → API Gateway     │
                    │   → Lambda/EKS Backend   │
                    │   → SageMaker Endpoint   │
                    │   → Container            │
                    │   → inference.py         │
                    │   → model.pkl.predict()  │
                    │   → Response             │
                    └──────────────────────────┘
```

### Detailed Step-by-Step Process

#### Step 1: Local Model Training
```bash
# Train model in Jupyter notebook
cd notebooks/models/
jupyter notebook

# Model is saved to backend/models/v6/
# - model.pkl: Trained scikit-learn pipeline
# - metadata.json: Model version, accuracy, classes, etc.
# - inference.py: SageMaker inference handler
# - requirements.txt: Model-specific dependencies
```

**Model Files:**
```
backend/models/v6/
├── model.pkl          # 680 MB - Serialized scikit-learn model
├── metadata.json      # Model configuration and metrics
├── inference.py       # SageMaker handler (model_fn, input_fn, predict_fn, output_fn)
└── requirements.txt   # Additional dependencies (if any)
```

#### Step 2: Package & Upload to S3
```bash
# Package model for SageMaker and upload to S3
./scripts/upload_model_to_s3.sh v6 --profile ml-ser-deploy
```

**What happens:**
1. **Validation**: Checks all required files exist (model.pkl, metadata.json, inference.py, requirements.txt)
2. **Packaging**: Creates SageMaker-compatible structure:
   ```
   model.tar.gz (compressed)
   ├── model.pkl           # Root level (SageMaker loads from /opt/ml/model/)
   ├── metadata.json       # Root level
   └── code/               # SageMaker copies to /opt/ml/model/code/
       ├── inference.py    # Entry point (SAGEMAKER_PROGRAM)
       └── requirements.txt
   ```
3. **S3 Upload**: Uploads to `s3://ml-speech-emotion-models-us-east-1/sagemaker-models/v6/model.tar.gz`
4. **Monitoring Data**: Also uploads Evidently reference dataset for drift detection

**S3 Structure:**
```
s3://ml-speech-emotion-models-us-east-1/
├── sagemaker-models/
│   ├── v4/model.tar.gz
│   ├── v5/model.tar.gz
│   └── v6/model.tar.gz       ← Latest model package
└── monitoring/
    └── reference_dataset.csv  ← Evidently baseline
```

#### Step 3: Custom SageMaker Container (One-Time Setup)

The custom container is built once and reused across model versions:

**Why Custom Container?**
- **Version Control**: Ensures exact scikit-learn (1.7.2) and numpy (2.1.0) versions
- **Compatibility**: Avoids pickle deserialization errors between versions
- **Optimization**: Includes only required dependencies (smaller image)
- **Flexibility**: Can add custom preprocessing, logging, or monitoring

**Container Build Process:**
```bash
# Build custom container (one-time)
cd deployment/sagemaker/container/
docker build -t ml-speech-emotion-sklearn:1.7.2-py310 .

# Tag for ECR
docker tag ml-speech-emotion-sklearn:1.7.2-py310 \
  303440520181.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-sklearn:1.7.2-py310

# Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 303440520181.dkr.ecr.us-east-1.amazonaws.com
docker push 303440520181.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-sklearn:1.7.2-py310
```

**Container Components:**
- **Base**: Python 3.10 slim (minimal size)
- **ML Stack**: scikit-learn 1.7.2, numpy 2.1.0, scipy, joblib
- **Web Server**: nginx + gunicorn + Flask (SageMaker requirements)
- **Entrypoint**: `serve` script (handles model loading and inference)

#### Step 4: Deploy to SageMaker

**Automatic Deployment (CD Pipeline):**
```bash
# Trigger via GitHub Actions workflow
gh workflow run cd.yml -f model_version=v6 -f deploy_sagemaker=true
```

**Manual Deployment:**
```bash
# Deploy using Python script
python deployment/sagemaker/scripts/deploy_to_sagemaker.py \
  --model-version v6 \
  --endpoint-name ml-ser-v1 \
  --instance-type ml.t2.medium \
  --s3-uri s3://ml-speech-emotion-models-us-east-1/sagemaker-models/v6/model.tar.gz \
  --region us-east-1 \
  --execution-role-arn arn:aws:iam::303440520181:role/ml-speech-emotion-prod-sagemaker-execution
```

**Deployment Orchestration:**

1. **Create SageMaker Model**:
   - Links container image (ECR) with model data (S3)
   - Sets environment variables for inference handler
   - Applies tags for version tracking

2. **Create Endpoint Configuration**:
   - Specifies instance type (ml.t2.medium = 2 vCPU, 4GB RAM)
   - Sets scaling parameters (initial count = 1)
   - Configures traffic routing (100% to AllTraffic variant)

3. **Create/Update Endpoint**:
   - Creates new endpoint OR updates existing endpoint (zero-downtime)
   - Provisions EC2 instance(s) with container
   - Downloads model.tar.gz from S3 to /opt/ml/model/
   - Installs code/requirements.txt dependencies
   - Loads model.pkl into memory
   - Starts nginx + gunicorn (port 8080)
   - Health checks until InService status

**Endpoint Auto-Versioning:**
- Script automatically increments endpoint version: ml-ser-v1 → ml-ser-v2 → ml-ser-v3
- Each deployment creates a new endpoint (old endpoint remains for rollback)

#### Step 5: Production Inference

**Backend Integration:**
```python
# backend/app/infrastructure/model/sagemaker_emotion_model_adapter.py
response = sagemaker_client.invoke_endpoint(
    EndpointName="ml-ser-v1",
    ContentType="application/json",
    Body=json.dumps({"features": [210 audio features]})
)
```

**Request Flow:**
1. User uploads audio → Streamlit/API
2. Backend extracts 210 features (MFCCs, spectral, prosodic) → Librosa
3. Backend invokes SageMaker endpoint → boto3
4. SageMaker routes to container instance
5. Container calls inference.py → predict_fn(features, model)
6. Model predicts emotion probabilities → scikit-learn
7. Response returns to backend → JSON
8. Frontend displays prediction → User

### Key Benefits

1. **Reproducibility**: Exact dependency versions eliminate "works on my machine" issues
2. **Scalability**: SageMaker auto-scales instances based on traffic
3. **Monitoring**: CloudWatch metrics (latency, invocations, errors) built-in
4. **Version Control**: Each model version is immutable and traceable
5. **Zero-Downtime Deployment**: Update endpoints without service interruption
6. **Cost Optimization**: Only pay for inference time (ml.t2.medium ≈ $0.065/hour)

### Deployment Commands Reference

```bash
# 1. Upload new model version to S3
./scripts/upload_model_to_s3.sh v7 --profile ml-ser-deploy

# 2. Deploy to SageMaker (via GitHub Actions)
gh workflow run cd.yml -f model_version=v7 -f deploy_sagemaker=true -f deploy_eks=false

# 3. Verify deployment
aws sagemaker describe-endpoint --endpoint-name ml-ser-v1 --profile ml-ser-deploy

# 4. Test inference
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name ml-ser-v1 \
  --content-type application/json \
  --body '{"features": [0.1, 0.2, ..., 0.3]}' \
  response.json

# 5. Monitor endpoint
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name ModelLatency \
  --dimensions Name=EndpointName,Value=ml-ser-v1
```
