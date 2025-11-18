# 🚀 ML Speech Emotion Recognition - Complete Deployment Guide

This comprehensive guide covers all deployment strategies for the ML Speech Emotion Recognition application, from local development to production deployment.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Strategies](#deployment-strategies)
4. [Strategy 1: Local Development](#strategy-1-local-development)
5. [Strategy 2: Docker Deployment](#strategy-2-docker-deployment)
6. [Strategy 3: Kubernetes Deployment](#strategy-3-kubernetes-deployment)
7. [Environment Configuration](#environment-configuration)
8. [Troubleshooting](#troubleshooting)
9. [Migration Paths](#migration-paths)
10. [Success Criteria](#success-criteria)

---

## 🎯 Overview

This guide provides three progressive deployment strategies for the ML Speech Emotion Recognition application:

| Strategy | Use Case | Complexity | Isolation | Best For |
|----------|----------|------------|-----------|----------|
| **Local Development** | Development, debugging | ⭐ Beginner | ❌ None | Quick iteration, learning |
| **Docker Deployment** | Team collaboration, testing | ⭐⭐ Intermediate | ✅ Full | Consistent environments |
| **Kubernetes Deployment** | Production, scaling | ⭐⭐⭐ Advanced | ✅ Full + Orchestration | Production readiness |

---

## 📋 Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 8GB | 16GB |
| **CPU** | 4 cores | 8 cores |
| **Disk Space** | 20GB | 50GB |

### Required Software

#### 1. Python 3.11+
```bash
# macOS
brew install python@3.11

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Verify installation
python3.11 --version
```

#### 2. Poetry (Python Dependency Manager)
```bash
# macOS/Linux/WSL
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH (restart terminal after)
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
poetry --version
```

#### 3. Node.js 18+ & npm
```bash
# macOS
brew install node

# Linux (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

#### 4. Audio Processing Libraries
```bash
# macOS
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install ffmpeg libsndfile1
```

#### 5. Docker Desktop (for Strategies 2 & 3)
```bash
# macOS
brew install --cask docker

# Download from: https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker compose version
```

#### 6. Kubernetes Tools (for Strategy 3)
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Minikube (or use Docker Desktop K8s)
brew install minikube

# Verify installation
kubectl version --client
minikube version
```

---

## 🎯 Deployment Strategies

### Choosing the Right Strategy

| Scenario | Recommended Strategy |
|----------|---------------------|
| **New developer onboarding** | Strategy 1 (Local) |
| **Feature development** | Strategy 1 (Local) |
| **Team collaboration** | Strategy 2 (Docker) |
| **Demo to stakeholders** | Strategy 2 (Docker) |
| **Production readiness testing** | Strategy 3 (Kubernetes) |
| **DevOps workflow validation** | Strategy 3 (Kubernetes) |

### Quick Decision Matrix

- **Learning Phase**: Strategy 1 → Strategy 2 → Strategy 3
- **Development Focus**: Strategy 1 or 2
- **Production Focus**: Strategy 2 or 3
- **Team Size**: 1-2 devs (Strategy 1), 3-10 devs (Strategy 2), 10+ devs (Strategy 3)

---

# 🎯 Strategy 1: Local Development (Native Execution)

## 💡 When to Use This Strategy

- ✅ **Quick development** and debugging
- ✅ **Learning** the codebase
- ✅ **Testing** new features
- ✅ **No Docker/Kubernetes knowledge required**

## 🗂️ Project Setup

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd ml-speech-emotion-recognition
```

### 2. Backend Setup
```bash
cd backend

# Install dependencies with Poetry
poetry install

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Activate virtual environment
poetry shell
```

### 3. Frontend Setup
```bash
# React Dashboard
cd ../frontend/react_dashboard
npm install

# Streamlit App
cd ../streamlit_app
pip install -r requirements.txt
```

## 🚀 Running Services Locally

### Option 1: Individual Terminals (Recommended for Development)

#### Terminal 1: Backend API
```bash
cd backend
poetry shell
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 2: Streamlit ML Interface
```bash
cd frontend/streamlit_app
streamlit run app.py --server.headless=true --server.port=8501
```

#### Terminal 3: React Dashboard
```bash
cd frontend/react_dashboard
npm start
```

### Option 2: Automated Script
```bash
# Use the provided start script
./scripts/start-local.sh
```

## 🌐 Accessing Services

| Service | URL | Description |
|---------|-----|-------------|
| **Backend API** | http://localhost:8000 | FastAPI application |
| **Health Check** | http://localhost:8000/health | API health status |
| **API Documentation** | http://localhost:8000/docs | Interactive API docs |
| **React Dashboard** | http://localhost:3000 | Main web interface |
| **Streamlit Interface** | http://localhost:8501 | ML interface |

## 🔧 Configuration

### Backend Configuration (.env)
```env
# Basic Configuration
DEBUG=true
HOST=0.0.0.0
PORT=8000
SECRET_KEY=your-secret-key-here

# AWS Configuration
AWS_REGION=us-east-1
SAGEMAKER_ENDPOINT_NAME=your-endpoint-name

# File Upload Configuration
MAX_UPLOAD_SIZE_MB=30
MAX_AUDIO_DURATION_SECONDS=30

# CORS Configuration (for local development)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8501"]
```

### Frontend Configuration

#### React (.env.local)
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_ENVIRONMENT=development
```

#### Streamlit (.streamlit/config.toml)
```toml
[server]
port = 8501
headless = true
address = "0.0.0.0"

[browser]
gatherUsageStats = false
```

---

# 🐳 Strategy 2: Docker Deployment (Containerized Development)

## 💡 When to Use This Strategy

- ✅ **Team collaboration** with consistent environments
- ✅ **Testing production-like setup**
- ✅ **Deployment testing**
- ✅ **Isolating dependencies**

## 🏗️ Building Docker Images

### 1. Navigate to Docker Configuration
```bash
cd deployment/docker
```

### 2. Build All Images
```bash
# Build all services
./build.sh all latest

# Verify images are built
docker images | grep sagerstack/ml-emotion
```

## 🚀 Starting Services with Docker Compose

### Core Services
```bash
# Start main application
docker compose up -d

# View logs
docker compose logs -f

# Check status
docker compose ps
```

### With Monitoring Stack
```bash
# Start with monitoring (Redis, Prometheus, Grafana)
docker compose --profile monitoring up -d

# View all services
docker compose ps
```

### Development Mode with Volumes
```bash
# Start with live code mounting
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## 🌐 Accessing Services (Docker)

| Service | URL | Description |
|---------|-----|-------------|
| **React Dashboard** | http://localhost:3000 | Main web interface |
| **Streamlit Interface** | http://localhost:8501 | ML interface |
| **Backend API** | http://localhost:8000 | FastAPI application |
| **API Documentation** | http://localhost:8000/docs | Interactive API docs |

## 📝 Environment Variables in Docker

The `docker-compose.yml` automatically sets environment variables:

```yaml
services:
  streamlit:
    environment:
      - BACKEND_API_URL=http://backend:8000  # Docker internal networking
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

For custom configuration, create a `.env` file in the project root:
```env
BACKEND_API_URL=http://custom-backend:9000
API_TIMEOUT=60
DEBUG_MODE=false
```

---

# ☸️ Strategy 3: Kubernetes Deployment (Production-like Environment)

## 💡 When to Use This Strategy

- ✅ **Production simulation** and testing
- ✅ **Kubernetes learning** and practice
- ✅ **DevOps workflow** validation
- ✅ **Scaling and orchestration** testing

## 🏗️ Environment Setup

### Option 1: Using Docker Desktop Kubernetes
```bash
# Enable Kubernetes in Docker Desktop settings
# Set resources: 4+ CPUs, 8+ GB RAM

# Verify cluster
kubectl cluster-info
kubectl get nodes
```

### Option 2: Using Minikube
```bash
# Start Minikube with sufficient resources
minikube start --cpus=4 --memory=8000 --disk-size=30g

# Enable required addons
minikube addons enable ingress
minikube addons enable metrics-server

# Verify status
minikube status
```

## 🚀 Deployment Process

### 1. Build and Push Docker Images to Docker Hub

```bash
cd deployment/docker

# Build all images
./build.sh all latest

# Push images to Docker Hub (requires Docker Hub login)
docker push sagerstack/ml-emotion-backend:latest
docker push sagerstack/ml-emotion-streamlit:latest
docker push sagerstack/ml-emotion-frontend:latest

# Verify images are available
docker images | grep sagerstack/ml-emotion
```

### 2. Deploy Application

#### Automated Deployment (Recommended):
```bash
cd deployment/k8s

# Deploy all services using local configs (images pulled from Docker Hub)
./deploy.sh local deploy

# Monitor deployment progress
./deploy.sh local status
```

#### Manual Deployment:
```bash
cd deployment/k8s

# Create namespace and configurations
kubectl apply -f local/namespace.yaml
kubectl apply -f local/configmap.yaml

# Check configmaps 
kubectl describe configmap app-config -n ml-emotion

# Deploy backend first (includes dependencies)
kubectl apply -f local/backend-deployment.yaml

# Wait for backend
kubectl wait --for=condition=available deployment/backend -n ml-emotion --timeout=300s

# Deploy Streamlit
kubectl apply -f local/streamlit-deployment.yaml

# Deploy Frontend
kubectl apply -f local/frontend-deployment.yaml

# Configure ingress
kubectl apply -f local/ingress.yaml
```

### 3. Configure Local DNS
```bash
# Edit hosts file
sudo nano /etc/hosts

# Add entries (use minikube IP or localhost)
minikube ip  # Get Minikube IP
# Or use 127.0.0.1 for Docker Desktop

# Add these lines:
127.0.0.1 ml-emotion.local
127.0.0.1 dashboard.ml-emotion.local
127.0.0.1 streamlit.ml-emotion.local
127.0.0.1 api.ml-emotion.local
```

## 🌐 Accessing Services (Kubernetes)

| Service | URL | Description |
|---------|-----|-------------|
| **Main Application** | http://ml-emotion.local | React dashboard with audio upload |
| **Streamlit Interface** | http://streamlit.ml-emotion.local | Streamlit ML interface |
| **API Documentation** | http://api.ml-emotion.local/docs | FastAPI auto-generated docs |
| **Monitoring** | http://ml-emotion.local/grafana | Grafana dashboard (if enabled) |

## 📊 Resource Usage Comparison

| Strategy | Resource Overhead | Monitoring | Debugging | Pros | Cons |
|----------|------------------|-----------|----------|------|------|
| **Local Development** | Native processes | System tools | IDE integration | Fastest iteration | No isolation |
| **Docker Deployment** | ~2-5% | `docker stats` | `docker exec`, logs | Consistent envs | Docker overhead |
| **Kubernetes** | ~10-15% | `kubectl top`, Prometheus | `kubectl describe`, logs | Production features | Complex setup |

---

# 🔧 Environment Configuration

## 📁 Environment Variables Structure

```
frontend/
├── .env.example              # Template with all available variables
├── .env.local                # Local development variables (git-ignored)
├── requirements.txt            # Python dependencies
└── streamlit_app/
    ├── .env.example           # Streamlit environment template
    └── app.py                # Main application using env vars
```

## 🌐 Environment Variables Available

### Required Variables

| Variable | Description | Default | Local | Docker | Kubernetes |
|----------|-------------|---------|--------|--------|------------|
| `BACKEND_API_URL` | Backend API URL | `http://localhost:8000` | `http://localhost:8000` | `http://backend:8000` | `http://backend-service:8000` |

### Optional Variables

| Variable | Description | Default | Purpose |
|----------|-------------|---------|---------|
| `STREAMLIT_SERVER_PORT` | Streamlit server port | `8501` | Port configuration |
| `STREAMLIT_SERVER_ADDRESS` | Streamlit address | `0.0.0.0` | Network binding |
| `API_TIMEOUT` | API request timeout | `30` | Request timeout |
| `LOG_LEVEL` | Logging level | `INFO` | Verbosity control |
| `DEBUG_MODE` | Debug mode | `false` | Feature flags |
| `AWS_REGION` | AWS region | `us-east-1` | Cloud configuration |
| `MAX_UPLOAD_SIZE_MB` | Max file size | `30` | Upload limits |
| `MAX_AUDIO_DURATION_SECONDS` | Audio duration limit | `30` | Processing limits |

## 📁 Setup Instructions

### 1. Local Development
```bash
# Copy environment template
cp .env.example .env.local

# Edit for local development
# BACKEND_API_URL=http://localhost:8000
# API_TIMEOUT=30
# DEBUG_MODE=true
```

### 2. Docker Development
```bash
# Environment variables set in docker-compose.yml
# Or create .env file in project root
docker compose up -d
```

### 3. Kubernetes Production
```bash
# Create ConfigMap with environment variables
kubectl apply -f deployment/k8s/local/configmap.yaml

# Or use environment-specific manifests
kubectl apply -f deployment/k8s/prod/configmap.yaml
```

## 🔧 Environment Variable Implementation

### API Client Usage
```python
from utils.api_client import APIClient

# Uses environment variable with fallback
def __init__(self, base_url: str = None):
    if base_url is None:
        base_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
    self.base_url = base_url.rstrip('/')
    self.timeout = int(os.getenv('API_TIMEOUT', '30'))
```

### Streamlit App Usage
```python
# Default URL from environment variable
default_api_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
api_url = st.text_input(
    "Backend API URL",
    value=default_api_url,
    help="URL of the FastAPI backend"
)
```

---

# 🔄 Migration Paths

## From Strategy 1 → Strategy 2
1. **Stop local services**: Kill all Python/Node processes
2. **Install Docker**: Install Docker Desktop
3. **Build images**: Use `./build.sh all latest`
4. **Start containers**: `docker compose up -d`
5. **Verify functionality**: Test all endpoints

## From Strategy 2 → Strategy 3
1. **Stop Docker Compose**: `docker compose down`
2. **Setup Kubernetes**: Install Minikube or enable Docker K8s
3. **Build and push images**: Build Docker images and push to Docker Hub
4. **Deploy local manifests**: Apply Kubernetes local configurations (pull from Docker Hub)
5. **Configure DNS**: Set up local domain resolution

## From Strategy 3 → Production
1. **Configure cloud provider**: AWS EKS, Google GKE, Azure AKS
2. **Set up infrastructure**: VPC, security groups, IAM roles
3. **Configure DNS**: Route53, Cloudflare, or custom DNS
4. **Deploy manifests**: Use production configurations
5. **Set up monitoring**: Prometheus, Grafana, logging aggregation
6. **Configure auto-scaling**: HPA, VPA, cluster autoscaler
7. **Implement CI/CD**: GitHub Actions, GitLab CI, Jenkins
8. **Set up observability**: Distributed tracing, centralized logging

---

# 🧹 Troubleshooting

## Common Issues and Solutions

### Local Development Issues

#### Port Conflicts
```bash
# Check what's using the port
lsof -i :8000  # Backend
lsof -i :3000  # React
lsof -i :8501  # Streamlit

# Kill the process
kill -9 <PID>
```

#### Python Dependencies
```bash
# Reset Poetry environment
cd backend
poetry env remove python
poetry install
```

#### Node.js Dependencies
```bash
# Clean and reinstall
cd frontend/react_dashboard
rm -rf node_modules package-lock.json
npm install
```

#### Audio Library Errors
```bash
# Reinstall audio dependencies
# macOS
brew reinstall ffmpeg

# Linux
sudo apt reinstall ffmpeg libsndfile1
```

### Docker Issues

#### Containers won't start
```bash
# Check Docker daemon
docker info

# Check for port conflicts
docker-compose ps
lsof -i :8000 -i :3000 -i :8501

# Reset Docker
docker system prune -a
docker-compose down -v
docker compose up -d
```

#### Build failures
```bash
# Clean build
docker-compose build --no-cache backend

# Check build logs
docker-compose build backend 2>&1 | tee build.log

# Fix ARM64 compatibility (Apple Silicon)
export DOCKER_DEFAULT_PLATFORM=linux/amd64
docker compose build
```

#### Permission errors
```bash
# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo
sudo docker-compose up -d
```

### Kubernetes Issues

#### Pods stuck in Pending
```bash
# Check node resources
kubectl describe nodes
kubectl top nodes

# Check resource requests
kubectl describe pod <pod-name> -n ml-emotion

# Scale down resources if needed
kubectl edit deployment backend -n ml-emotion
```

#### Images not found
```bash
# Check if images exist on Docker Hub
docker pull sagerstack/ml-emotion-backend:latest
docker pull sagerstack/ml-emotion-streamlit:latest
docker pull sagerstack/ml-emotion-frontend:latest

# Check pod image pull status
kubectl describe pod <pod-name> -n ml-emotion | grep -A 10 "Events"

# If images are missing, rebuild and push:
cd deployment/docker
./build.sh all latest
docker push sagerstack/ml-emotion-backend:latest
docker push sagerstack/ml-emotion-streamlit:latest
docker push sagerstack/ml-emotion-frontend:latest
```

#### Ingress not working
```bash
# Check ingress controller
kubectl get pods -n ingress-nginx

# Check ingress configuration
kubectl describe ingress ml-emotion-ingress -n ml-emotion

# Restart ingress
minikube addons disable ingress
minikube addons enable ingress
```

#### DNS resolution problems
```bash
# Check hosts file
cat /etc/hosts | grep ml-emotion.local

# Test DNS
ping ml-emotion.local

# Use Minikube tunnel (alternative to hosts file)
minikube tunnel
```

### Environment Variable Issues

#### Variables not loading
```bash
# Check if .env file exists
ls -la .env*

# Check python-dotenv installation
pip install python-dotenv

# Verify file format
cat .env
```

#### Backend connection failed
```bash
# Check API URL configuration
echo $BACKEND_API_URL

# Test connection manually
curl $BACKEND_API_URL/health

# Check backend logs
kubectl logs -n ml-emotion deployment/backend -f
```

---

# 📊 Performance & Monitoring

## Strategy 1 Performance
- **Resource usage**: Native Python/Node processes
- **Monitoring**: Use Activity Monitor/Task Manager
- **Logging**: Console output
- **Debugging**: Direct IDE integration

## Strategy 2 Performance
- **Resource usage**: Docker container overhead (~2-5%)
- **Monitoring**: `docker stats`, container logs
- **Logging**: `docker-compose logs`
- **Debugging**: `docker exec`, container inspection

## Strategy 3 Performance
- **Resource usage**: Kubernetes overhead (~10-15%)
- **Monitoring**: `kubectl top`, Prometheus/Grafana
- **Logging**: `kubectl logs`, centralized logging
- **Debugging**: `kubectl describe`, `kubectl exec`

---

# 🎉 Success Criteria

## Strategy 1 Success ✅
- [ ] All services start without errors
- [ ] React dashboard loads at http://localhost:3000
- [ ] Streamlit interface loads at http://localhost:8501
- [ ] Backend API responds at http://localhost:8000/health
- [ ] Audio upload and emotion prediction works
- [ ] Hot reloading works for development

## Strategy 2 Success ✅
- [ ] All Docker containers build successfully
- [ ] Docker Compose starts all services
- [ ] All health endpoints respond correctly
- [ ] Application works through browser URLs
- [ ] Container logs show no significant errors
- [ ] Resource usage is reasonable

## Strategy 3 Success ✅
- [ ] Kubernetes cluster is healthy
- [ ] All pods are running and ready
- [ ] Ingress routes work correctly
- [ ] Local DNS resolution functions
- [ ] Application accessible through custom domains
- [ ] Autoscaling works (if configured)
- [ ] Monitoring endpoints are accessible

---

# 📚 References and Scripts

## 📁 Key Files and Scripts

| File/Script | Purpose | Strategy |
|-------------|---------|----------|
| `scripts/start-local.sh` | Start all services locally | 1 |
| `scripts/docker-compose-manage.sh` | Manage Docker deployment | 2 |
| `deployment/k8s/deploy.sh` | Kubernetes deployment | 3 |
| `docker-compose.yml` | Docker service configuration | 2 |
| `deployment/k8s/local/` | Local K8s manifests | 3 |
| `deployment/k8s/prod/` | Production K8s manifests | 3 |

## 🔗 Quick Reference Commands

### Development Commands
```bash
# Start all services (Strategy 1)
./scripts/start-local.sh

# Docker deployment (Strategy 2)
./scripts/docker-compose-manage.sh start

# Kubernetes deployment (Strategy 3)
cd deployment/k8s && ./deploy.sh local deploy

# Check service status
./scripts/check-local.sh
./scripts/docker-compose-manage.sh status
```

### Service Access
```bash
# Health checks
curl http://localhost:8000/health
curl http://localhost:8501/_stcore/health

# API documentation
open http://localhost:8000/docs
open http://ml-emotion.local/docs  # Kubernetes
```

### Management Commands
```bash
# Stop services (Strategy 1)
./scripts/stop-local.sh

# Docker management
./scripts/docker-compose-manage.sh stop
./scripts/docker-compose-manage.sh clean

# Kubernetes management
cd deployment/k8s
./deploy.sh local delete
./deploy.sh local deploy
```

## 🎯 Choosing Your Deployment Strategy

### Development Workflow
1. **Start**: Strategy 1 for rapid development
2. **Collaborate**: Move to Strategy 2 for team work
3. **Test**: Use Strategy 2 for integration testing
4. **Production**: Deploy to Strategy 3 for staging/production

### Team Size Guidelines
- **1-2 developers**: Strategy 1 or 2
- **3-10 developers**: Strategy 2
- **10+ developers**: Strategy 3 with CI/CD

### Project Maturity
- **Prototype/MVP**: Strategy 1
- **Development phase**: Strategy 2
- **Production ready**: Strategy 3

---

## 🚀 Congratulations!

You now have a complete understanding of how to deploy the ML Speech Emotion Recognition application using three different strategies!

**Key Takeaways:**
- ✅ **Environment variables** eliminate hardcoded URLs
- ✅ **Progressive complexity** from local to production
- ✅ **Comprehensive documentation** for each strategy
- ✅ **Automated scripts** simplify deployment
- ✅ **Production-ready** architecture with Kubernetes

Choose the strategy that best fits your current needs and development workflow! 🎉