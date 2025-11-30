#!/bin/bash
set -e

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-ml-ser-deploy}"
EKS_CLUSTER_NAME="ml-speech-emotion-prod-eks"

export AWS_PROFILE

ACTION="${1:-}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ "$ACTION" = "helm" ]; then
    echo -e "${GREEN}=== AWS Load Balancer Controller Installation ===${NC}"
    echo ""

    # Step 3: Verify nodes are ready
    echo -e "${YELLOW}Step 1/4: Checking if nodes are ready...${NC}"

    # Check if kubectl is configured
    if ! kubectl get nodes &>/dev/null; then
        echo -e "${RED}Error: Cannot connect to cluster. Run this script without parameters first to setup the cluster.${NC}"
        exit 1
    fi

    # Get node status
    NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l || echo "0")
    READY_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | grep -c " Ready " || echo "0")

    if [ "$NODE_COUNT" -eq 0 ]; then
        echo -e "${RED}Error: No nodes found in the cluster.${NC}"
        echo -e "${YELLOW}Please wait for terraform to complete node provisioning.${NC}"
        exit 1
    fi

    if [ "$READY_COUNT" -lt "$NODE_COUNT" ]; then
        echo -e "${YELLOW}Nodes are not ready yet. Current status:${NC}"
        kubectl get nodes
        echo ""
        echo -e "${YELLOW}Please wait for all nodes to show 'Ready' status, then run:${NC}"
        echo -e "  ${GREEN}./tf-apply.sh helm${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ All $READY_COUNT nodes are ready${NC}"
    kubectl get nodes
    echo ""

    # Step 4: Wait for critical pods
    echo -e "${YELLOW}Step 2/4: Checking kube-system pods...${NC}"
    kubectl get pods -n kube-system
    echo ""

    # Check if coredns is running
    COREDNS_RUNNING=$(kubectl get pods -n kube-system -l k8s-app=kube-dns --no-headers 2>/dev/null | grep -c "Running" || echo "0")
    if [ "$COREDNS_RUNNING" -eq 0 ]; then
        echo -e "${YELLOW}Warning: CoreDNS pods are not running yet. Waiting may be required.${NC}"
    else
        echo -e "${GREEN}✓ CoreDNS is running${NC}"
    fi
    echo ""

    # Step 5: Install AWS Load Balancer Controller
    echo -e "${YELLOW}Step 3/4: Installing AWS Load Balancer Controller...${NC}"

    # Add helm repo if not already added
    if ! helm repo list | grep -q "^eks"; then
        echo "Adding EKS helm repository..."
        helm repo add eks https://aws.github.io/eks-charts
    fi

    echo "Updating helm repositories..."
    helm repo update

    # Get VPC ID from terraform output
    echo "Retrieving VPC ID from terraform..."
    VPC_ID=$(terraform output -raw vpc_id)
    echo "VPC ID: $VPC_ID"
    echo ""

    # Check if controller is already installed
    if helm list -n kube-system | grep -q "aws-load-balancer-controller"; then
        echo -e "${YELLOW}AWS Load Balancer Controller is already installed. Upgrading...${NC}"
        helm upgrade aws-load-balancer-controller eks/aws-load-balancer-controller \
          -n kube-system \
          --set clusterName=${EKS_CLUSTER_NAME} \
          --set serviceAccount.create=true \
          --set serviceAccount.name=aws-load-balancer-controller \
          --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::303440520181:role/ml-speech-emotion-prod-alb-controller \
          --set region=${AWS_REGION} \
          --set vpcId=${VPC_ID} \
          --reuse-values
        echo -e "${GREEN}✓ Helm upgrade completed${NC}"
    else
        echo "Installing AWS Load Balancer Controller..."
        helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
          -n kube-system \
          --set clusterName=${EKS_CLUSTER_NAME} \
          --set serviceAccount.create=true \
          --set serviceAccount.name=aws-load-balancer-controller \
          --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::303440520181:role/ml-speech-emotion-prod-alb-controller \
          --set region=${AWS_REGION} \
          --set vpcId=${VPC_ID}
        echo -e "${GREEN}✓ Helm install completed${NC}"
    fi
    echo ""

    # Step 6: Verify controller is running
    echo -e "${YELLOW}Step 4/4: Verifying AWS Load Balancer Controller deployment...${NC}"
    echo "Waiting for controller pods to be ready (timeout: 60s)..."

    if kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=aws-load-balancer-controller \
        -n kube-system \
        --timeout=60s; then
        echo ""
        echo -e "${GREEN}✓ AWS Load Balancer Controller is successfully deployed!${NC}"
        echo ""
        kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
    else
        echo ""
        echo -e "${RED}Warning: Controller pods are not ready yet. Check status:${NC}"
        kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
        kubectl describe pods -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
        exit 1
    fi

    echo ""
    echo -e "${GREEN}=== Installation Complete ===${NC}"
    echo -e "You can now deploy applications that use LoadBalancer services or Ingress resources."

else
    # Default mode: Steps 1-2-3
    echo -e "${GREEN}=== Terraform Apply and EKS Setup ===${NC}"
    echo ""

    # Step 1: Terraform apply
    echo -e "${YELLOW}Step 1/3: Running terraform apply...${NC}"
    terraform apply -auto-approve
    echo ""

    # Step 2: Update kubeconfig
    echo -e "${YELLOW}Step 2/3: Updating kubeconfig...${NC}"
    aws eks update-kubeconfig --name ${EKS_CLUSTER_NAME} --region ${AWS_REGION}
    echo ""

    # Step 3: Restart ALB controller pods (to pick up IAM policy changes)
    echo -e "${YELLOW}Step 3/3: Restarting AWS Load Balancer Controller...${NC}"

    # Check if ALB controller is installed
    if kubectl get deployment aws-load-balancer-controller -n kube-system &>/dev/null; then
        echo "Found AWS Load Balancer Controller, restarting to pick up IAM policy changes..."
        kubectl rollout restart deployment/aws-load-balancer-controller -n kube-system

        echo "Waiting for controller to restart..."
        if kubectl rollout status deployment/aws-load-balancer-controller -n kube-system --timeout=60s; then
            echo -e "${GREEN}✓ AWS Load Balancer Controller restarted successfully${NC}"
        else
            echo -e "${YELLOW}⚠ Controller restart timed out, but may still be in progress${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ AWS Load Balancer Controller not found (may need to install it first)${NC}"
        echo "Run: ${GREEN}./tf-apply.sh helm${NC} to install the controller"
    fi
    echo ""

    echo -e "${GREEN}✓ Terraform apply completed successfully${NC}"
    echo -e "${GREEN}✓ Kubeconfig updated${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. If this is first-time setup, install AWS Load Balancer Controller:"
    echo -e "   ${GREEN}./tf-apply.sh helm${NC}"
    echo "2. Deploy application via CD workflow:"
    echo -e "   ${GREEN}gh workflow run cd.yml${NC}"
fi
