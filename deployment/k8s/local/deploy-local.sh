#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Correct image names
BACKEND_IMAGE="sagerstack/ml-speech-emotion-backend:latest"
STREAMLIT_IMAGE="sagerstack/ml-speech-emotion-streamlit:latest"
NAMESPACE="ml-speech-emotion"
MONITORING_NAMESPACE="monitoring"

# Parse command line arguments
SKIP_PUSH=false
DEPLOY_MONITORING=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-push)
      SKIP_PUSH=true
      shift
      ;;
    --with-monitoring)
      DEPLOY_MONITORING=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--skip-push] [--with-monitoring]"
      exit 1
      ;;
  esac
done

# Check required commands
command -v docker >/dev/null 2>&1 || { echo "Error: docker is required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "Error: kubectl is required"; exit 1; }
command -v minikube >/dev/null 2>&1 || { echo "Error: minikube is required"; exit 1; }

echo "=========================================="
echo "ML Speech Emotion Recognition - Local K8s Deployment"
echo "=========================================="
echo "Backend Image:    ${BACKEND_IMAGE}"
echo "Streamlit Image:  ${STREAMLIT_IMAGE}"
echo "Namespace:        ${NAMESPACE}"
echo "Skip Push:        ${SKIP_PUSH}"
echo "Deploy Monitoring: ${DEPLOY_MONITORING}"
echo "=========================================="

# Docker login (if not skipping push)
if [ "${SKIP_PUSH}" = false ]; then
  echo ""
  echo "Step 1: Docker Hub Login"
  echo "Checking Docker Hub authentication..."

  if ! docker info 2>/dev/null | grep -q "Username:"; then
    echo "Not logged in to Docker Hub. Please login now:"
    docker login
    if [ $? -ne 0 ]; then
      echo "Error: Docker login failed"
      exit 1
    fi
  else
    echo "Already logged in to Docker Hub ✓"
  fi
fi

# Start minikube if not running
echo ""
echo "Step 2: Minikube Setup"
if minikube status &>/dev/null; then
  echo "Minikube is already running ✓"
else
  echo "Minikube is not running. Starting minikube..."
  minikube start --cpus=4 --memory=8192
  if [ $? -ne 0 ]; then
    echo "Error: Failed to start minikube"
    exit 1
  fi
  echo "Minikube started successfully ✓"
fi

# Configure Docker to use minikube's daemon (for arm64 compatibility)
echo ""
echo "Step 3: Configure Docker Environment"
echo "Configuring Docker to use minikube's daemon..."
eval "$(minikube docker-env)"

# Build backend image
echo ""
echo "Step 4: Build Docker Images"
echo "Building backend image (${BACKEND_IMAGE})..."
docker build \
  -f "${REPO_ROOT}/deployment/docker/backend/Dockerfile" \
  -t "${BACKEND_IMAGE}" \
  "${REPO_ROOT}"

# Build streamlit image
echo ""
echo "Building streamlit image (${STREAMLIT_IMAGE})..."
docker build \
  -f "${REPO_ROOT}/deployment/docker/streamlit/Dockerfile" \
  -t "${STREAMLIT_IMAGE}" \
  "${REPO_ROOT}"

# Push images to Docker Hub (if not skipped)
if [ "${SKIP_PUSH}" = false ]; then
  echo ""
  echo "Step 5: Push Images to Docker Hub"
  echo "Pushing images to Docker Hub..."

  echo "Pushing backend image..."
  docker push "${BACKEND_IMAGE}"

  echo "Pushing streamlit image..."
  docker push "${STREAMLIT_IMAGE}"
else
  echo ""
  echo "Skipping Docker Hub push (using local images only)"
fi

# Apply Kubernetes manifests
echo ""
echo "Step 6: Deploy to Kubernetes"
echo "Applying Kubernetes manifests..."
kubectl apply -f "${SCRIPT_DIR}/namespace.yaml"
kubectl apply -f "${SCRIPT_DIR}/configmap.yaml"
kubectl apply -f "${SCRIPT_DIR}/backend-deployment.yaml"
kubectl apply -f "${SCRIPT_DIR}/streamlit-deployment.yaml"
kubectl apply -f "${SCRIPT_DIR}/ingress.yaml"

# Deploy monitoring stack if requested
if [ "${DEPLOY_MONITORING}" = true ]; then
  echo ""
  echo "Step 7: Deploy Monitoring Stack"
  echo "Deploying monitoring stack..."
  if [ -f "${SCRIPT_DIR}/monitoring-stack.yaml" ]; then
    kubectl apply -f "${SCRIPT_DIR}/monitoring-stack.yaml"
    echo "Monitoring stack deployed to namespace: ${MONITORING_NAMESPACE}"
  else
    echo "Warning: monitoring-stack.yaml not found, skipping monitoring deployment"
  fi
fi

# Wait for deployments to become ready
echo ""
echo "Step 8: Wait for Deployments"
echo "Waiting for deployments to become ready..."
kubectl rollout status deployment/backend -n "${NAMESPACE}" --timeout=300s
kubectl rollout status deployment/streamlit -n "${NAMESPACE}" --timeout=300s

# Wait for monitoring if deployed
if [ "${DEPLOY_MONITORING}" = true ]; then
  echo ""
  echo "Waiting for monitoring stack to be ready..."
  if kubectl get namespace "${MONITORING_NAMESPACE}" &>/dev/null; then
    kubectl rollout status deployment/prometheus -n "${MONITORING_NAMESPACE}" --timeout=300s || true
    kubectl rollout status deployment/grafana -n "${MONITORING_NAMESPACE}" --timeout=300s || true
  fi
fi

# Fetch service URLs
echo ""
echo "Step 9: Fetch Service URLs"
echo "Fetching service URLs via minikube..."
BACKEND_URL="$(minikube service backend -n "${NAMESPACE}" --url | head -n1)"
STREAMLIT_URL="$(minikube service streamlit -n "${NAMESPACE}" --url | head -n1)"

# Display deployment summary
cat <<EOF

========================================
Deployment Complete!
========================================
Backend Service:   ${BACKEND_URL}
Streamlit Service: ${STREAMLIT_URL}

Backend Health:    ${BACKEND_URL}/health
Backend Metrics:   ${BACKEND_URL}/metrics
Backend API Docs:  ${BACKEND_URL}/docs

Quick Access Commands:
  kubectl get pods -n ${NAMESPACE}
  kubectl logs -n ${NAMESPACE} deployment/backend --tail=50
  kubectl logs -n ${NAMESPACE} deployment/streamlit --tail=50

Port Forwarding (alternative to minikube service):
  kubectl port-forward -n ${NAMESPACE} svc/backend 8000:8000
  kubectl port-forward -n ${NAMESPACE} svc/streamlit 8501:8501

EOF

if [ "${DEPLOY_MONITORING}" = true ]; then
  cat <<EOF
Monitoring Stack:
  Prometheus: kubectl port-forward -n ${MONITORING_NAMESPACE} svc/prometheus 9090:9090
  Grafana:    kubectl port-forward -n ${MONITORING_NAMESPACE} svc/grafana 3000:3000

  Access at:
    - Prometheus: http://localhost:9090
    - Grafana:    http://localhost:3000 (admin/admin)

EOF
fi

cat <<EOF
Ingress Configuration:
  - Ensure ingress addon is enabled: minikube addons enable ingress
  - Add to /etc/hosts:
      $(minikube ip) ml-emotion.local
      $(minikube ip) streamlit.ml-emotion.local

  Then access via:
    - http://ml-emotion.local/api/health
    - http://streamlit.ml-emotion.local/

========================================
EOF
