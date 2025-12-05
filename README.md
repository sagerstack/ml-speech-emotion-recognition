# Machine Learning Speech Emotion Recognition

## Project Structure

```
ml-speech-emotion-recognition/
├── backend/                      # FastAPI backend service
│   ├── app/
│   │   ├── api/                 # API endpoints
│   │   │   └── v1/              # API version 1
│   │   ├── interfaces/          # Interface definitions
│   │   ├── middleware/          # FastAPI middleware
│   │   ├── models/              # Pydantic models
│   │   ├── services/            # Business logic services
│   │   └── utils/               # Utility functions
│   ├── evidently_workspace/     # Evidently AI monitoring workspace
│   ├── models/                  # ML model versions
│   │   ├── v1/                  # Model version 1
│   │   ├── v2/                  # Model version 2
│   │   └── v3/                  # Model version 3 (current)
│   ├── monitoring_data/         # Reference datasets for monitoring
│   ├── monitoring_reports/      # Generated monitoring reports
│   ├── scripts/                 # Backend utility scripts
│   ├── tests/                   # Test suite
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── pyproject.toml
│   └── poetry.lock
│
├── frontend/                     # Streamlit frontend application
│   └── streamlit_app/
│       ├── src/
│       │   ├── pages/           # Streamlit pages
│       │   │   ├── 1_History.py
│       │   │   ├── 2_Metrics.py
│       │   │   └── 3_Monitoring.py
│       │   ├── ml-app.py        # Main app entry point
│       │   ├── api_client.py
│       │   ├── feature_charts.py
│       │   ├── mock_inference.py
│       │   └── real_inference.py
│       └── docs/
│
├── data/                         # Training datasets
│   ├── AudioWAV/                # CREMA-D dataset audio files
│   └── ravdess-speech-audio/    # RAVDESS dataset
│
├── deployment/                   # Deployment configurations
│   ├── aws/                     # AWS deployment configs
│   ├── docker/                  # Dockerfiles
│   ├── k8s/                     # Kubernetes manifests
│   ├── monitoring/              # Monitoring setup
│   ├── scripts/                 # Deployment scripts
│   └── terraform/               # Infrastructure as Code
│
├── notebooks/                    # Jupyter notebooks
│   └── models/                  # Model development notebooks
│
├── sagemaker/                    # AWS SageMaker integration
│   ├── docs/
│   ├── model-deployment/
│   └── scripts/
│
├── scripts/                      # Project-wide utility scripts
│
├── specs/                        # Feature specifications
│   ├── 001-model-deployment-api/
│   ├── 002-streamlit-app/
│   └── master/
│
├── docs/                         # Documentation
│   ├── architecture-diagrams/
│   └── ops/
│
├── docker-compose.yml            # Docker Compose configuration
├── pyproject.toml               # Poetry configuration
└── poetry.lock                  # Poetry lock file
```

## Key Components

- **Backend**: FastAPI-based REST API for emotion recognition inference
- **Frontend**: Streamlit web application for user interaction and visualization
- **Models**: Multiple versions of emotion recognition models (v1, v2, v3)
- **Monitoring**: Evidently AI integration for model performance monitoring
- **Deployment**: Multi-environment deployment support (Docker, Kubernetes, AWS)
- **Datasets**: CREMA-D and RAVDESS speech emotion datasets
