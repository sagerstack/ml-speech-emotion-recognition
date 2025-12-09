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
