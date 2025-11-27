#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

BACKEND_IMAGE="sagerstack/ml-speech-backend:latest"
STREAMLIT_IMAGE="sagerstack/ml-speech-frontend:latest"
NAMESPACE="ml-speech-emotion"

command -v docker >/dev/null 2>&1 || { echo "docker is required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required"; exit 1; }
command -v minikube >/dev/null 2>&1 || { echo "minikube is required"; exit 1; }

echo "Building backend image (${BACKEND_IMAGE})..."
docker build \
  -f "${REPO_ROOT}/deployment/docker/backend/Dockerfile" \
  -t "${BACKEND_IMAGE}" \
  "${REPO_ROOT}"

echo "Building streamlit image (${STREAMLIT_IMAGE})..."
docker build \
  -f "${REPO_ROOT}/deployment/docker/streamlit/Dockerfile" \
  -t "${STREAMLIT_IMAGE}" \
  "${REPO_ROOT}"

echo "Pushing backend image..."
docker push "${BACKEND_IMAGE}"

echo "Pushing streamlit image..."
docker push "${STREAMLIT_IMAGE}"

echo "Applying Kubernetes manifests..."
kubectl apply -f "${SCRIPT_DIR}/namespace.yaml"
kubectl apply -f "${SCRIPT_DIR}/configmap.yaml"
kubectl apply -f "${SCRIPT_DIR}/backend-deployment.yaml"
kubectl apply -f "${SCRIPT_DIR}/streamlit-deployment.yaml"
kubectl apply -f "${SCRIPT_DIR}/ingress.yaml"

echo "Waiting for deployments to become ready..."
kubectl rollout status deployment/backend -n "${NAMESPACE}"
kubectl rollout status deployment/streamlit -n "${NAMESPACE}"

echo "Fetching service URLs via minikube..."
BACKEND_URL="$(minikube service backend -n "${NAMESPACE}" --url | head -n1)"
STREAMLIT_URL="$(minikube service streamlit -n "${NAMESPACE}" --url | head -n1)"

cat <<EOF

Deployment complete!
  Backend service URL:   ${BACKEND_URL}
  Streamlit service URL: ${STREAMLIT_URL}

Note: If you leverage the ingress hosts, ensure 'minikube addons enable ingress' is run and update /etc/hosts accordingly.
EOF
