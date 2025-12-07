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
CLEAN_DEPLOY=false

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
    --clean)
      CLEAN_DEPLOY=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--skip-push] [--with-monitoring] [--clean]"
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
echo "Clean Deploy:     ${CLEAN_DEPLOY}"
echo "=========================================="

# Function to cleanup existing resources
cleanup_resources() {
  echo ""
  echo "🧹 Cleanup: Removing existing resources..."

  # Kill existing port forwards
  echo "Stopping existing port forwards..."
  pkill -f "kubectl port-forward.*${NAMESPACE}" 2>/dev/null || true
  pkill -f "kubectl port-forward.*${MONITORING_NAMESPACE}" 2>/dev/null || true
  sleep 2

  # Check if namespaces exist and delete resources
  if kubectl get namespace "${NAMESPACE}" &>/dev/null; then
    echo "Deleting resources in namespace: ${NAMESPACE}"
    kubectl delete all --all -n "${NAMESPACE}" --timeout=60s 2>/dev/null || true
    kubectl delete configmap --all -n "${NAMESPACE}" --timeout=30s 2>/dev/null || true
    kubectl delete ingress --all -n "${NAMESPACE}" --timeout=30s 2>/dev/null || true
    echo "Deleting namespace: ${NAMESPACE}"
    kubectl delete namespace "${NAMESPACE}" --timeout=60s 2>/dev/null || true
  else
    echo "Namespace ${NAMESPACE} does not exist, skipping cleanup"
  fi

  if kubectl get namespace "${MONITORING_NAMESPACE}" &>/dev/null; then
    echo "Deleting resources in namespace: ${MONITORING_NAMESPACE}"
    kubectl delete all --all -n "${MONITORING_NAMESPACE}" --timeout=60s 2>/dev/null || true
    kubectl delete configmap --all -n "${MONITORING_NAMESPACE}" --timeout=30s 2>/dev/null || true
    kubectl delete pvc --all -n "${MONITORING_NAMESPACE}" --timeout=30s 2>/dev/null || true
    echo "Deleting namespace: ${MONITORING_NAMESPACE}"
    kubectl delete namespace "${MONITORING_NAMESPACE}" --timeout=60s 2>/dev/null || true
  else
    echo "Namespace ${MONITORING_NAMESPACE} does not exist, skipping cleanup"
  fi

  echo "Resource cleanup completed ✓"
}

# Function to stop and delete minikube
reset_minikube() {
  echo ""
  echo "🔄 Resetting Minikube..."

  if minikube status &>/dev/null; then
    echo "Stopping minikube..."
    minikube stop
    echo "Minikube stopped ✓"
  else
    echo "Minikube is not running, skipping stop"
  fi

  echo "Deleting minikube cluster..."
  minikube delete
  echo "Minikube cluster deleted ✓"
}

# Perform cleanup if --clean flag is provided
if [ "${CLEAN_DEPLOY}" = true ]; then
  echo ""
  echo "╔════════════════════════════════════════════════════════════╗"
  echo "║         CLEAN DEPLOYMENT MODE ENABLED                      ║"
  echo "║  This will delete all existing resources and minikube      ║"
  echo "╚════════════════════════════════════════════════════════════╝"

  # Cleanup existing resources
  cleanup_resources

  # Reset minikube
  reset_minikube

  echo ""
  echo "✓ Cleanup completed. Starting fresh deployment..."
  echo ""
fi

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
  echo "Configuring: 4 CPUs, 6GB RAM"
  minikube start --cpus=4 --memory=6144
  if [ $? -ne 0 ]; then
    echo "Error: Failed to start minikube"
    echo "Tip: Check Docker Desktop has at least 6GB memory allocated"
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

# When using --skip-push, patch imagePullPolicy to Never so k8s uses local images
if [ "${SKIP_PUSH}" = true ]; then
  echo "Using local images (imagePullPolicy: Never)..."
  # Apply manifests with sed to change imagePullPolicy from Always to Never
  sed 's/imagePullPolicy: Always/imagePullPolicy: Never/g' "${SCRIPT_DIR}/backend-deployment.yaml" | kubectl apply -f -
  sed 's/imagePullPolicy: Always/imagePullPolicy: Never/g' "${SCRIPT_DIR}/streamlit-deployment.yaml" | kubectl apply -f -
else
  kubectl apply -f "${SCRIPT_DIR}/backend-deployment.yaml"
  kubectl apply -f "${SCRIPT_DIR}/streamlit-deployment.yaml"
fi
kubectl apply -f "${SCRIPT_DIR}/ingress.yaml"

# Force pod restart to ensure new images are pulled
# This is necessary because kubectl apply won't restart pods if only the image content changed
# (even with imagePullPolicy: Always, k8s won't pull unless the pod is recreated)
echo ""
echo "Forcing pod restart to pull latest images..."
kubectl rollout restart deployment/backend -n "${NAMESPACE}"
kubectl rollout restart deployment/streamlit -n "${NAMESPACE}"

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

  # Apply Grafana dashboards ConfigMap from static YAML file
  DASHBOARD_CM_FILE="${SCRIPT_DIR}/grafana-dashboards-configmap.yaml"
  if [ -f "${DASHBOARD_CM_FILE}" ]; then
    echo "Applying Grafana dashboards ConfigMap..."
    kubectl apply -f "${DASHBOARD_CM_FILE}"
    echo "Dashboards ConfigMap applied successfully"
  else
    echo "Warning: grafana-dashboards-configmap.yaml not found"
  fi

  # Deploy kube-state-metrics
  if [ -f "${SCRIPT_DIR}/kube-state-metrics.yaml" ]; then
    kubectl apply -f "${SCRIPT_DIR}/kube-state-metrics.yaml"
    echo "kube-state-metrics deployed"
  else
    echo "Warning: kube-state-metrics.yaml not found"
  fi

  # Deploy node-exporter
  if [ -f "${SCRIPT_DIR}/node-exporter.yaml" ]; then
    kubectl apply -f "${SCRIPT_DIR}/node-exporter.yaml"
    echo "node-exporter deployed"
  else
    echo "Warning: node-exporter.yaml not found"
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

# Setup port forwarding
echo ""
echo "Step 9: Setup Port Forwarding"
echo "Setting up port forwarding for easy access..."

# Kill any existing port forwards
pkill -f "kubectl port-forward.*${NAMESPACE}" 2>/dev/null || true
pkill -f "kubectl port-forward.*${MONITORING_NAMESPACE}" 2>/dev/null || true

# Wait a moment for ports to be released
sleep 2

# Start port forwarding in background
echo "Starting port forwards..."
kubectl port-forward -n "${NAMESPACE}" svc/backend 8000:8000 >/dev/null 2>&1 &
BACKEND_PF_PID=$!
kubectl port-forward -n "${NAMESPACE}" svc/streamlit 8501:8501 >/dev/null 2>&1 &
STREAMLIT_PF_PID=$!

# Setup monitoring port forwards if deployed
if [ "${DEPLOY_MONITORING}" = true ]; then
  kubectl port-forward -n "${MONITORING_NAMESPACE}" svc/prometheus 9090:9090 >/dev/null 2>&1 &
  PROMETHEUS_PF_PID=$!
  kubectl port-forward -n "${MONITORING_NAMESPACE}" svc/grafana 3000:3000 >/dev/null 2>&1 &
  GRAFANA_PF_PID=$!
fi

# Wait for port forwards to establish
sleep 3

# Test backend connectivity
echo "Testing backend connectivity..."
if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
  echo "Backend is accessible ✓"
else
  echo "Warning: Backend health check failed. Port forward may still be establishing."
fi

# Display deployment summary
cat <<EOF

╔══════════════════════════════════════════════════════════════╗
║                   DEPLOYMENT COMPLETE! ✓                     ║
╚══════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────┐
│  🌐 ACCESS YOUR SERVICES                                      │
└──────────────────────────────────────────────────────────────┘

📱 STREAMLIT WEB APP (Main Interface)
   👉 http://localhost:8501

   This is your main application interface for:
   - Uploading audio files
   - Running emotion analysis
   - Viewing results and visualizations

🔧 BACKEND API
   👉 http://localhost:8000

   Key Endpoints:
   • Health Check:  http://localhost:8000/health
   • API Docs:      http://localhost:8000/docs
   • Metrics:       http://localhost:8000/metrics
   • Model Info:    http://localhost:8000/v1/models/local/latest

EOF

if [ "${DEPLOY_MONITORING}" = true ]; then
  cat <<EOF
📊 MONITORING STACK

   📈 Prometheus (Metrics Collection)
   👉 http://localhost:9090

   📉 Grafana (Dashboards & Visualization)
   👉 http://localhost:3000

   📝 Credentials: admin / admin

   Note: Loki is running internally for log aggregation
         Access logs via Grafana's Explore view

EOF
fi

cat <<EOF
┌──────────────────────────────────────────────────────────────┐
│  🛠️  MANAGEMENT                                               │
└──────────────────────────────────────────────────────────────┘

Port Forward PIDs:
  • Backend:   ${BACKEND_PF_PID}
  • Streamlit: ${STREAMLIT_PF_PID}
EOF

if [ "${DEPLOY_MONITORING}" = true ]; then
  cat <<EOF
  • Prometheus: ${PROMETHEUS_PF_PID}
  • Grafana:    ${GRAFANA_PF_PID}
EOF
fi

cat <<EOF

To Stop Port Forwarding:
  kill ${BACKEND_PF_PID} ${STREAMLIT_PF_PID}
EOF

if [ "${DEPLOY_MONITORING}" = true ]; then
  echo "  kill ${PROMETHEUS_PF_PID} ${GRAFANA_PF_PID}"
fi

cat <<EOF

Kubernetes Commands:
  # View running pods
  kubectl get pods -n ${NAMESPACE}

  # Stream backend logs
  kubectl logs -n ${NAMESPACE} deployment/backend --tail=50 -f

  # Stream streamlit logs
  kubectl logs -n ${NAMESPACE} deployment/streamlit --tail=50 -f
EOF

if [ "${DEPLOY_MONITORING}" = true ]; then
  cat <<EOF

  # View monitoring pods
  kubectl get pods -n ${MONITORING_NAMESPACE}
EOF
fi

cat <<EOF

┌──────────────────────────────────────────────────────────────┐
│  📝 OPTIONAL: INGRESS SETUP                                   │
└──────────────────────────────────────────────────────────────┘

If you want to use hostnames instead of localhost:

1. Enable ingress addon:
   minikube addons enable ingress

2. Add to /etc/hosts:
   $(minikube ip) ml-emotion.local
   $(minikube ip) streamlit.ml-emotion.local

3. Access via:
   http://ml-emotion.local/api/health
   http://streamlit.ml-emotion.local/

┌──────────────────────────────────────────────────────────────┐
│  🔄 DEPLOYMENT OPTIONS                                        │
└──────────────────────────────────────────────────────────────┘

Script Usage:
  $0 [OPTIONS]

Options:
  --skip-push         Skip pushing images to Docker Hub (use local images)
  --with-monitoring   Deploy Prometheus, Grafana, and Loki monitoring stack
  --clean            Clean deploy: delete all resources and minikube, then redeploy

Examples:
  # Standard deployment
  $0

  # Deploy with monitoring
  $0 --with-monitoring

  # Clean deployment (removes everything first)
  $0 --clean

  # Clean deployment with monitoring and local images
  $0 --clean --with-monitoring --skip-push

╔══════════════════════════════════════════════════════════════╗
║  Port forwards will continue running in the background       ║
║  Press Ctrl+C to exit this script (services stay running)    ║
╚══════════════════════════════════════════════════════════════╝

EOF
