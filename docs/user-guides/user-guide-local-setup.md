# Local Setup Guide

This guide walks you through setting up the ML Speech Emotion Recognition application locally. Two deployment options are available:

1. **Poetry Local Development** - Run backend and frontend directly (recommended for development)
2. **Kubernetes with Minikube** - Full containerized deployment (recommended for testing production-like environment)

---

## Prerequisites

### Operating System
- macOS (Intel or Apple Silicon)
- Linux (Ubuntu 20.04+, Debian 11+)
- Windows with WSL2

### Required Tools

#### 1. Install Homebrew (macOS only)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Install Git
```bash
# macOS
brew install git

# Ubuntu/Debian
sudo apt update && sudo apt install git
```

#### 3. Install Python 3.11+
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11 python3.11-venv python3-pip
```

#### 4. Install Poetry (Python Package Manager)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Add Poetry to your PATH (add to `~/.zshrc` or `~/.bashrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Verify installation:
```bash
poetry --version
```

---

## Clone Repository

```bash
git clone <repository-url>
cd ml-speech-emotion-recognition
```

---

## Data Prerequisites (CRITICAL)

The following files are **not included** in the repository (gitignored). Please refer to the project README.md on how to download these files.

### 1. ML Model (Required)
Place the model file at:
```
backend/models/v6/model.pkl
```

### 2. Reference Dataset (Required for Monitoring)
Place the reference dataset at:
```
backend/monitoring_data/reference_dataset.csv
```

Create the directory if it doesn't exist:
```bash
mkdir -p backend/monitoring_data
```

---

## Environment Setup

Run the setup script to create `.env.local` files for both backend and frontend:

```bash
./scripts/setup-local-env.sh
```

This script will:
- Copy `.env.example` to `.env.local` for backend
- Copy `.env.example` to `.env.local` for frontend
- Generate a secure `SECRET_KEY` for the backend
- Check if required data files are present

---

## Option 1: Poetry Local Development

This option runs the backend and frontend directly on your machine without containers.

### Step 1: Start the Backend

Open a terminal and run:

```bash
cd backend

# Install dependencies
poetry install --with dev

# Start the backend server
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify the backend is running:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Step 2: Start the Frontend

Open a **new terminal** and run:

```bash
cd frontend/streamlit_app

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Streamlit
streamlit run src/ml-app.py --server.port=8510
```

Access the application: http://localhost:8510

### Running Tests

```bash
cd backend

# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## Option 2: Kubernetes with Minikube

This option deploys the full application stack in a local Kubernetes cluster.

### Additional Prerequisites

#### 1. Install Docker Desktop
Download from: https://www.docker.com/products/docker-desktop

**Important:** Allocate at least 6GB RAM to Docker Desktop:
- Docker Desktop > Settings > Resources > Memory: 6GB+

#### 2. Install Minikube and kubectl

```bash
# macOS
brew install minikube kubectl

# Ubuntu/Debian
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
```

### Deploy the Stack

Navigate to the project root and run:

```bash
# Standard deployment (uses local images)
./deployment/k8s/local/deploy-local.sh --skip-push

# With monitoring (Prometheus, Grafana, Loki)
./deployment/k8s/local/deploy-local.sh --skip-push --with-monitoring

# Clean deployment (removes everything first)
./deployment/k8s/local/deploy-local.sh --clean --skip-push
```

### Access Services

| Service | URL | Notes |
|---------|-----|-------|
| Streamlit UI | http://localhost:8501/ml-ser/ | Main Application |
| Backend API | http://localhost:8000/ml-ser | FastAPI Backend |
| API Docs | http://localhost:8000/ml-ser/docs | Swagger UI |
| Health Check | http://localhost:8000/ml-ser/health | Backend Health |

**With `--with-monitoring` flag:**

| Service | URL | Notes |
|---------|-----|-------|
| Prometheus | http://localhost:9090 | Metrics Collection |
| App Metrics Dashboard | http://localhost:3000/d/893b67e4-6d93-49db-9047-9df11b9c86dc/ser-app-dashboard | No login required |
| Kubernetes Dashboard | http://localhost:3000/d/fe5807eb-0772-41d0-8d28-03838a5b9671/kubernetes-dashboard | No login required |

### Useful kubectl Commands

```bash
# View running pods
kubectl get pods -n ml-speech-emotion

# Stream backend logs
kubectl logs -f deployment/backend -n ml-speech-emotion

# Stream frontend logs
kubectl logs -f deployment/streamlit -n ml-speech-emotion

# Manual port forwarding (if needed)
kubectl port-forward svc/backend 8000:8000 -n ml-speech-emotion
kubectl port-forward svc/streamlit 8501:8501 -n ml-speech-emotion

# View monitoring pods (if deployed)
kubectl get pods -n monitoring
```

### Stop the Deployment

```bash
# Stop port forwards
pkill -f "kubectl port-forward"

# Stop minikube
minikube stop

# Delete everything (clean slate)
minikube delete
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Port already in use** | Find and kill the process: `lsof -i :8000` then `kill -9 <PID>` |
| **SECRET_KEY not set** | Run `./scripts/setup-local-env.sh` or manually set in `backend/.env.local` |
| **librosa caching errors** | Automatically fixed by environment variables in `main.py` |
| **Minikube out of memory** | Increase RAM: `minikube config set memory 8192` then restart |
| **Docker not running** | Start Docker Desktop application |
| **Model not found** | Ensure `backend/models/v6/model.pkl` exists (see Data Prerequisites) |
| **Reference dataset not found** | Ensure `backend/monitoring_data/reference_dataset.csv` exists |
| **Poetry command not found** | Add Poetry to PATH: `export PATH="$HOME/.local/bin:$PATH"` |

---

## Project Structure Overview (Relevant for Local Deployment)

```
ml-speech-emotion-recognition/
├── backend/                        # FastAPI Backend (Poetry)
│   ├── app/                       # Application code
│   │   ├── api/                   # API endpoints
│   │   ├── domain/                # Domain models
│   │   ├── infrastructure/        # Config, adapters, services
│   │   └── use_cases/             # Business logic
│   ├── models/v6/                 # ML model (gitignored .pkl)
│   ├── monitoring_data/           # Reference dataset (gitignored)
│   ├── tests/                     # Test suite
│   ├── pyproject.toml             # Python dependencies
│   └── .env.example               # Environment template
│
├── frontend/streamlit_app/         # Streamlit Frontend (pip)
│   ├── src/                       # Application code
│   │   ├── ml-app.py             # Main entry point
│   │   ├── api_client.py         # Backend API client
│   │   └── pages/                # Multi-page app pages
│   ├── requirements.txt           # Python dependencies
│   └── .env.example               # Environment template
│
├── deployment/
│   ├── k8s/local/                 # Kubernetes manifests
│   │   ├── deploy-local.sh       # Deployment script
│   │   ├── backend-deployment.yaml
│   │   ├── streamlit-deployment.yaml
│   │   └── monitoring-stack.yaml
│   └── docker/                    # Dockerfiles
│
├── scripts/
│   └── setup-local-env.sh         # Environment setup script
│
└── docker-compose.yml              # Docker Compose (alternative)
```

---

## Next Steps

After successful setup:

1. **Upload an audio file** through the Streamlit UI
2. **Run emotion analysis** and view results
3. **Explore the API** at http://localhost:8000/docs
4. **Check monitoring** (if deployed with `--with-monitoring`)

For questions or issues, please refer to the project documentation or contact the development team.
