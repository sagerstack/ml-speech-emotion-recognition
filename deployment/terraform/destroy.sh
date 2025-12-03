#!/bin/bash

# Cleanup script for proper EKS teardown
# This script ensures Kubernetes-created AWS resources are cleaned up before Terraform destroy

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-ml-ser-deploy}"
EKS_CLUSTER_NAME="ml-speech-emotion-prod-eks"
K8S_NAMESPACE="ml-speech-emotion"

# Export AWS_PROFILE to ensure all commands use it
export AWS_PROFILE

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  EKS Cluster Cleanup and Terraform Destroy Script         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo -e "  AWS Profile: ${GREEN}${AWS_PROFILE}${NC}"
echo -e "  AWS Region:  ${GREEN}${AWS_REGION}${NC}"
echo -e "  EKS Cluster: ${GREEN}${EKS_CLUSTER_NAME}${NC}"
echo -e "  Namespace:   ${GREEN}${K8S_NAMESPACE}${NC}"
echo ""

# Step 1: Check if cluster exists and is accessible
echo -e "${YELLOW}[Step 1/6]${NC} Checking EKS cluster accessibility..."

if ! aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$AWS_REGION" --profile "$AWS_PROFILE" &>/dev/null; then
    echo -e "${YELLOW}⚠️  EKS cluster not found or not accessible${NC}"
    echo -e "${YELLOW}   Skipping Kubernetes cleanup, proceeding directly to Terraform destroy...${NC}"
    SKIP_K8S_CLEANUP=true
else
    echo -e "${GREEN}✓${NC} EKS cluster found and accessible"
    SKIP_K8S_CLEANUP=false

    # Update kubeconfig
    echo -e "${YELLOW}   Updating kubeconfig...${NC}"
    aws eks update-kubeconfig --name "$EKS_CLUSTER_NAME" --region "$AWS_REGION" --profile "$AWS_PROFILE" > /dev/null 2>&1
    echo -e "${GREEN}✓${NC} Kubeconfig updated"
fi

# Step 2: Delete Kubernetes resources if cluster is accessible
if [ "$SKIP_K8S_CLEANUP" = false ]; then
    echo ""
    echo -e "${YELLOW}[Step 2/6]${NC} Deleting Kubernetes resources..."

    # Check if app namespace exists
    if kubectl get namespace "$K8S_NAMESPACE" &>/dev/null; then
        echo -e "${YELLOW}   Deleting namespace: ${K8S_NAMESPACE}${NC}"
        kubectl delete namespace "$K8S_NAMESPACE" --timeout=120s || true
        echo -e "${GREEN}✓${NC} Namespace deleted"
    else
        echo -e "${YELLOW}⚠️  Namespace ${K8S_NAMESPACE} not found, skipping...${NC}"
    fi

    # Check if monitoring namespace exists
    if kubectl get namespace "monitoring" &>/dev/null; then
        echo -e "${YELLOW}   Deleting monitoring namespace...${NC}"
        kubectl delete namespace "monitoring" --timeout=120s || true
        echo -e "${GREEN}✓${NC} Monitoring namespace deleted"
    else
        echo -e "${YELLOW}⚠️  Monitoring namespace not found, skipping...${NC}"
    fi

    # Also clean up any standalone load balancers/services outside the namespace
    echo -e "${YELLOW}   Checking for services with LoadBalancer type...${NC}"
    LB_SERVICES=$(kubectl get svc --all-namespaces -o json | jq -r '.items[] | select(.spec.type=="LoadBalancer") | "\(.metadata.namespace)/\(.metadata.name)"')

    if [ -n "$LB_SERVICES" ]; then
        echo -e "${YELLOW}   Found LoadBalancer services:${NC}"
        echo "$LB_SERVICES"
        echo -e "${YELLOW}   Deleting them...${NC}"
        echo "$LB_SERVICES" | while read -r svc; do
            kubectl delete svc "${svc#*/}" -n "${svc%/*}" --timeout=60s || true
        done
        echo -e "${GREEN}✓${NC} LoadBalancer services deleted"
    else
        echo -e "${GREEN}✓${NC} No LoadBalancer services found"
    fi
else
    echo ""
    echo -e "${YELLOW}[Step 2/6]${NC} Skipping Kubernetes cleanup (cluster not accessible)"
fi

# Step 3: Wait for AWS Load Balancer Controller to clean up resources
if [ "$SKIP_K8S_CLEANUP" = false ]; then
    echo ""
    echo -e "${YELLOW}[Step 3/6]${NC} Waiting for AWS Load Balancer Controller to clean up AWS resources..."
    echo -e "${YELLOW}   This typically takes 30-60 seconds...${NC}"

    for i in {60..1}; do
        printf "\r${YELLOW}   ⏳ Waiting: %02d seconds remaining...${NC}" $i
        sleep 1
    done
    echo ""
    echo -e "${GREEN}✓${NC} Wait period complete"
else
    echo ""
    echo -e "${YELLOW}[Step 3/6]${NC} Skipping wait period (no Kubernetes cleanup performed)"
fi

# Step 4: Manual cleanup of any orphaned AWS resources
echo ""
echo -e "${YELLOW}[Step 4/6]${NC} Checking for orphaned AWS resources..."

# Get VPC ID from Terraform state
VPC_ID=$(cd "$(dirname "$0")" && terraform output -raw vpc_id 2>/dev/null || echo "")

if [ -n "$VPC_ID" ]; then
    echo -e "${YELLOW}   VPC ID: ${VPC_ID}${NC}"

    # Check for load balancers
    echo -e "${YELLOW}   Checking for load balancers in VPC...${NC}"
    LBS=$(AWS_PROFILE="$AWS_PROFILE" aws elbv2 describe-load-balancers --region "$AWS_REGION" --query "LoadBalancers[?VpcId=='$VPC_ID' && contains(LoadBalancerName, 'k8s')].LoadBalancerArn" --output text 2>/dev/null || echo "")

    if [ -n "$LBS" ]; then
        echo -e "${RED}   Found orphaned load balancers, deleting...${NC}"
        for lb_arn in $LBS; do
            echo -e "${YELLOW}   Deleting: $lb_arn${NC}"
            AWS_PROFILE="$AWS_PROFILE" aws elbv2 delete-load-balancer --load-balancer-arn "$lb_arn" --region "$AWS_REGION" 2>/dev/null || true
        done
        echo -e "${YELLOW}   Waiting for load balancers to be deleted...${NC}"
        sleep 15
        echo -e "${GREEN}✓${NC} Orphaned load balancers deleted"
    else
        echo -e "${GREEN}✓${NC} No orphaned load balancers found"
    fi

    # Check for security groups
    echo -e "${YELLOW}   Checking for Kubernetes security groups...${NC}"
    K8S_SGS=$(AWS_PROFILE="$AWS_PROFILE" aws ec2 describe-security-groups --region "$AWS_REGION" --filters "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[?contains(GroupName, 'k8s')].GroupId" --output text 2>/dev/null || echo "")

    if [ -n "$K8S_SGS" ]; then
        echo -e "${RED}   Found orphaned Kubernetes security groups, deleting...${NC}"
        for sg_id in $K8S_SGS; do
            echo -e "${YELLOW}   Deleting: $sg_id${NC}"
            AWS_PROFILE="$AWS_PROFILE" aws ec2 delete-security-group --group-id "$sg_id" --region "$AWS_REGION" 2>/dev/null || true
        done
        echo -e "${GREEN}✓${NC} Orphaned security groups deleted"
    else
        echo -e "${GREEN}✓${NC} No orphaned Kubernetes security groups found"
    fi
else
    echo -e "${YELLOW}⚠️  Could not retrieve VPC ID from Terraform state${NC}"
    echo -e "${YELLOW}   Skipping orphaned resource check...${NC}"
fi

# Step 5: Refresh Terraform state to sync with AWS reality
echo ""
echo -e "${YELLOW}[Step 5/6]${NC} Refreshing Terraform state from AWS..."
echo ""

cd "$(dirname "$0")"

echo -e "${YELLOW}   Syncing local state with actual AWS resources...${NC}"
if terraform refresh -lock=true; then
    echo -e "${GREEN}✓${NC} Terraform state refreshed successfully"
else
    echo -e "${RED}✗${NC} Failed to refresh Terraform state"
    echo -e "${YELLOW}   Continuing anyway (state might already be empty)...${NC}"
fi

echo ""

# Step 6: Run Terraform destroy
echo -e "${YELLOW}[Step 6/6]${NC} Running Terraform destroy..."
echo ""

# First, check what will be destroyed
echo -e "${YELLOW}   Checking what resources exist...${NC}"
RESOURCE_COUNT=$(terraform state list 2>/dev/null | wc -l | tr -d ' ')

if [ "$RESOURCE_COUNT" -eq "0" ]; then
    echo -e "${GREEN}✓${NC} No resources found in Terraform state"
    echo -e "${GREEN}   All infrastructure has already been destroyed!${NC}"
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ No resources to destroy - infrastructure is clean!     ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
fi

echo -e "${YELLOW}   Found ${RESOURCE_COUNT} resources to destroy${NC}"
echo ""

# Confirmation prompt
read -p "$(echo -e "${RED}⚠️  This will destroy all infrastructure. Are you sure? (yes/no): ${NC}")" confirmation

if [ "$confirmation" != "yes" ]; then
    echo -e "${RED}✗${NC} Terraform destroy cancelled by user"
    exit 1
fi

echo -e "${YELLOW}   Running terraform destroy with profile: ${AWS_PROFILE}${NC}"
if terraform destroy -auto-approve; then
    echo -e "${GREEN}✓${NC} Terraform destroy completed successfully"
else
    echo -e "${RED}✗${NC} Terraform destroy encountered errors"
    echo -e "${YELLOW}   Check the output above for details${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Cleanup and Terraform destroy completed successfully!  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
