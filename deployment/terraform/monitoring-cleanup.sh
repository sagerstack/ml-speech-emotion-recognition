#!/bin/bash

# Optional Monitoring Stack Cleanup Script
# This script safely removes the monitoring stack from EKS
#
# Usage:
#   ./monitoring-cleanup.sh           # Removes monitoring stack
#   ./monitoring-cleanup.sh --keep    # Scales to zero but keeps PVCs

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-ml-ser-deploy}"
EKS_CLUSTER_NAME="ml-speech-emotion-prod-eks"
MONITORING_NAMESPACE="monitoring"

export AWS_PROFILE

MODE="${1:-delete}"

echo -e "${BLUE}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Monitoring Stack Cleanup Script             ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════╝${NC}"
echo ""

# Check cluster access
echo -e "${YELLOW}Checking EKS cluster accessibility...${NC}"
if ! aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$AWS_REGION" --profile "$AWS_PROFILE" &>/dev/null; then
    echo -e "${RED}✗ EKS cluster not found or not accessible${NC}"
    exit 1
fi

echo -e "${GREEN}✓ EKS cluster accessible${NC}"
aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$AWS_REGION" --profile "$AWS_PROFILE" > /dev/null 2>&1
echo ""

# Check if monitoring namespace exists
if ! kubectl get namespace "$MONITORING_NAMESPACE" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Monitoring namespace doesn't exist${NC}"
    echo -e "${GREEN}Nothing to clean up!${NC}"
    exit 0
fi

if [ "$MODE" = "--keep" ]; then
    # Scale to zero but keep data
    echo -e "${YELLOW}Mode: Scale to Zero (keeping data)${NC}"
    echo ""
    echo -e "${YELLOW}Scaling deployments to zero...${NC}"

    kubectl scale deployment prometheus --replicas=0 -n "$MONITORING_NAMESPACE" 2>/dev/null || true
    kubectl scale deployment grafana --replicas=0 -n "$MONITORING_NAMESPACE" 2>/dev/null || true
    kubectl scale deployment loki --replicas=0 -n "$MONITORING_NAMESPACE" 2>/dev/null || true

    echo -e "${GREEN}✓ Monitoring pods scaled to zero${NC}"
    echo -e "${GREEN}✓ Persistent volumes and data retained${NC}"
    echo ""
    echo -e "${BLUE}To resume monitoring:${NC}"
    echo -e "  kubectl scale deployment prometheus --replicas=1 -n monitoring"
    echo -e "  kubectl scale deployment grafana --replicas=1 -n monitoring"
    echo -e "  kubectl scale deployment loki --replicas=1 -n monitoring"

else
    # Full cleanup
    echo -e "${YELLOW}Mode: Complete Removal${NC}"
    echo ""
    echo -e "${RED}This will delete:${NC}"
    echo -e "  - All monitoring deployments"
    echo -e "  - Prometheus, Grafana, Loki data"
    echo -e "  - Persistent volumes (metrics history will be lost)"
    echo ""

    read -p "$(echo -e "${YELLOW}Are you sure? (yes/no): ${NC}")" confirmation

    if [ "$confirmation" != "yes" ]; then
        echo -e "${YELLOW}Cleanup cancelled${NC}"
        exit 0
    fi

    echo ""
    echo -e "${YELLOW}Deleting monitoring stack...${NC}"

    # Delete using the monitoring manifest
    if [ -f "../../k8s/prod/monitoring-stack.yaml" ]; then
        kubectl delete -f ../../k8s/prod/monitoring-stack.yaml --timeout=120s || true
    else
        # Fallback: delete namespace
        kubectl delete namespace "$MONITORING_NAMESPACE" --timeout=120s || true
    fi

    echo -e "${GREEN}✓ Monitoring stack removed${NC}"

    # Check for orphaned PVCs
    echo -e "${YELLOW}Checking for orphaned persistent volumes...${NC}"
    ORPHANED_PVCS=$(kubectl get pvc -n "$MONITORING_NAMESPACE" 2>/dev/null || echo "")

    if [ -n "$ORPHANED_PVCS" ]; then
        echo -e "${YELLOW}Found orphaned PVCs, cleaning up...${NC}"
        kubectl delete pvc --all -n "$MONITORING_NAMESPACE" --timeout=60s || true
        echo -e "${GREEN}✓ Orphaned PVCs cleaned up${NC}"
    fi

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ Monitoring cleanup completed!             ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}To re-enable monitoring:${NC}"
    echo -e "  kubectl apply -f deployment/k8s/prod/monitoring-stack.yaml"
fi
