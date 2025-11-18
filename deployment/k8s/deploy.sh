#!/bin/bash

# Kubernetes deployment script for ML Speech Emotion Recognition
# Usage: ./deploy.sh [environment] [action]
# Environment: local, prod
# Action: deploy, delete, status

set -e

# Default values
ENVIRONMENT=${1:-local}
ACTION=${2:-deploy}
NAMESPACE=""
NAMESPACE_PROD="ml-emotion-prod"
NAMESPACE_LOCAL="ml-emotion"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Validate environment
validate_environment() {
    if [[ ! "$ENVIRONMENT" =~ ^(local|prod)$ ]]; then
        print_error "Invalid environment: $ENVIRONMENT"
        echo "Usage: $0 [local|prod] [deploy|delete|status]"
        exit 1
    fi

    if [[ ! "$ACTION" =~ ^(deploy|delete|status)$ ]]; then
        print_error "Invalid action: $ACTION"
        echo "Usage: $0 [local|prod] [deploy|delete|status]"
        exit 1
    fi

    NAMESPACE=$([ "$ENVIRONMENT" = "prod" ] && echo "$NAMESPACE_PROD" || echo "$NAMESPACE_LOCAL")
}

# Check if kubectl is available
check_dependencies() {
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed or not in PATH"
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    print_success "kubectl is available and cluster is accessible"
}

# Check if namespace exists
namespace_exists() {
    kubectl get namespace "$1" &> /dev/null
}

# Deploy manifests
deploy() {
    print_status "Deploying to $ENVIRONMENT environment..."

    local deploy_dir="$(dirname "$0")/$ENVIRONMENT"
    local manifests=()

    # Order of deployment matters
    if [[ "$ENVIRONMENT" = "local" ]]; then
        manifests=(
            "namespace.yaml"
            "configmap.yaml"
            "backend-deployment.yaml"
            "streamlit-deployment.yaml"
            "frontend-deployment.yaml"
            "ingress.yaml"
        )
    else
        manifests=(
            "namespace.yaml"
            "secrets.yaml"
            "configmap.yaml"
            "backend-deployment.yaml"
            "streamlit-deployment.yaml"
            "frontend-deployment.yaml"
            "ingress.yaml"
            "../monitoring.yaml"
        )
    fi

    # Create namespace first if it doesn't exist
    if ! namespace_exists "$NAMESPACE"; then
        print_status "Creating namespace: $NAMESPACE"
        kubectl apply -f "$deploy_dir/namespace.yaml"
        print_success "Namespace created: $NAMESPACE"
    fi

    # Deploy other manifests
    for manifest in "${manifests[@]}"; do
        local manifest_path="$deploy_dir/$manifest"

        # Handle monitoring.yaml separately (in root of k8s directory)
        if [[ "$manifest" == "../monitoring.yaml" ]]; then
            manifest_path="$(dirname "$0")/monitoring.yaml"
        fi

        if [[ -f "$manifest_path" ]]; then
            print_status "Applying $manifest..."
            kubectl apply -f "$manifest_path" -n "$([ "$manifest" == "../monitoring.yaml" ] && echo "monitoring" || echo "$NAMESPACE")"
            print_success "Applied $manifest"
        else
            print_warning "Manifest not found: $manifest_path"
        fi
    done

    print_success "Deployment completed for $ENVIRONMENT environment"
}

# Delete resources
delete() {
    print_warning "Deleting deployment from $ENVIRONMENT environment..."
    read -p "Are you sure you want to delete all resources? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Deletion cancelled"
        exit 0
    fi

    local deploy_dir="$(dirname "$0")/$ENVIRONMENT"
    local manifests=()

    # Reverse order for deletion
    if [[ "$ENVIRONMENT" = "local" ]]; then
        manifests=(
            "ingress.yaml"
            "frontend-deployment.yaml"
            "streamlit-deployment.yaml"
            "backend-deployment.yaml"
            "configmap.yaml"
            "namespace.yaml"
        )
    else
        manifests=(
            "ingress.yaml"
            "frontend-deployment.yaml"
            "streamlit-deployment.yaml"
            "backend-deployment.yaml"
            "configmap.yaml"
            "secrets.yaml"
            "../monitoring.yaml"
            "namespace.yaml"
        )
    fi

    for manifest in "${manifests[@]}"; do
        local manifest_path="$deploy_dir/$manifest"

        # Handle monitoring.yaml separately
        if [[ "$manifest" == "../monitoring.yaml" ]]; then
            manifest_path="$(dirname "$0")/monitoring.yaml"
        fi

        if [[ -f "$manifest_path" ]]; then
            print_status "Deleting $manifest..."
            kubectl delete -f "$manifest_path" -n "$([ "$manifest" == "../monitoring.yaml" ] && echo "monitoring" || echo "$NAMESPACE")" --ignore-not-found=true
            print_success "Deleted $manifest"
        else
            print_warning "Manifest not found: $manifest_path"
        fi
    done

    print_success "Deletion completed for $ENVIRONMENT environment"
}

# Show status
status() {
    print_status "Status for $ENVIRONMENT environment (namespace: $NAMESPACE)..."

    if ! namespace_exists "$NAMESPACE"; then
        print_warning "Namespace '$NAMESPACE' does not exist"
        return
    fi

    echo
    echo -e "${BLUE}=== Namespace Status ===${NC}"
    kubectl get namespace "$NAMESPACE"

    echo
    echo -e "${BLUE}=== Pods ===${NC}"
    kubectl get pods -n "$NAMESPACE" -o wide

    echo
    echo -e "${BLUE}=== Services ===${NC}"
    kubectl get services -n "$NAMESPACE"

    echo
    echo -e "${BLUE}=== Deployments ===${NC}"
    kubectl get deployments -n "$NAMESPACE"

    echo
    echo -e "${BLUE}=== Ingress ===${NC}"
    kubectl get ingress -n "$NAMESPACE"

    if [[ "$ENVIRONMENT" = "prod" ]]; then
        echo
        echo -e "${BLUE}=== Horizontal Pod Autoscalers ===${NC}"
        kubectl get hpa -n "$NAMESPACE"

        echo
        echo -e "${BLUE}=== Monitoring Status ===${NC}"
        if namespace_exists "monitoring"; then
            kubectl get pods -n monitoring -l app=prometheus
        else
            print_warning "Monitoring namespace not found"
        fi
    fi

    echo
    echo -e "${BLUE}=== Recent Events ===${NC}"
    kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -10
}

# Show usage
usage() {
    echo "Kubernetes deployment script for ML Speech Emotion Recognition"
    echo
    echo "Usage: $0 [environment] [action]"
    echo
    echo "Environment:"
    echo "  local    Deploy to local Minikube cluster"
    echo "  prod     Deploy to production EKS cluster"
    echo
    echo "Action:"
    echo "  deploy   Deploy all manifests (default)"
    echo "  delete   Delete all deployed resources"
    echo "  status   Show deployment status"
    echo
    echo "Examples:"
    echo "  $0 local deploy    # Deploy to local Minikube"
    echo "  $0 prod status     # Show production status"
    echo "  $0 local delete    # Delete local deployment"
}

# Main execution
main() {
    print_status "ML Speech Emotion Recognition - Kubernetes Deployment"
    print_status "Environment: $ENVIRONMENT, Action: $ACTION"
    echo

    validate_environment
    check_dependencies

    case $ACTION in
        "deploy")
            deploy
            echo
            print_status "Deployment summary:"
            echo "- Environment: $ENVIRONMENT"
            echo "- Namespace: $NAMESPACE"
            echo "- Access URLs:"
            if [[ "$ENVIRONMENT" = "local" ]]; then
                echo "  - Backend API: http://ml-emotion.local/api"
                echo "  - Frontend: http://dashboard.ml-emotion.local"
                echo "  - Streamlit: http://streamlit.ml-emotion.local"
                echo "  - Local: http://localhost"
            else
                echo "  - Main App: https://ml-emotion.example.com"
                echo "  - API: https://api.ml-emotion.example.com"
                echo "  - Dashboard: https://dashboard.ml-emotion.example.com"
                echo "  - Streamlit: https://app.ml-emotion.example.com"
            fi
            ;;
        "delete")
            delete
            ;;
        "status")
            status
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"