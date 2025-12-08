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
echo -e "${YELLOW}[Step 1/8]${NC} Checking EKS cluster accessibility..."

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
    echo -e "${YELLOW}[Step 2/8]${NC} Deleting Kubernetes resources..."

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
    echo -e "${YELLOW}[Step 2/8]${NC} Skipping Kubernetes cleanup (cluster not accessible)"
fi

# Step 3: Wait for AWS Load Balancer Controller to clean up resources
if [ "$SKIP_K8S_CLEANUP" = false ]; then
    echo ""
    echo -e "${YELLOW}[Step 3/8]${NC} Waiting for AWS Load Balancer Controller to clean up AWS resources..."
    echo -e "${YELLOW}   This typically takes 30-60 seconds...${NC}"

    for i in {60..1}; do
        printf "\r${YELLOW}   ⏳ Waiting: %02d seconds remaining...${NC}" $i
        sleep 1
    done
    echo ""
    echo -e "${GREEN}✓${NC} Wait period complete"
else
    echo ""
    echo -e "${YELLOW}[Step 3/8]${NC} Skipping wait period (no Kubernetes cleanup performed)"
fi

# Step 4: Clean up SageMaker resources (CRITICAL - these cost money!)
echo ""
echo -e "${YELLOW}[Step 4/8]${NC} Cleaning up SageMaker resources..."

# Delete SageMaker endpoints (highest cost - runs 24/7)
echo -e "${YELLOW}   Checking for SageMaker endpoints...${NC}"
ENDPOINTS=$(aws sagemaker list-endpoints --region "$AWS_REGION" --query "Endpoints[?contains(EndpointName, 'ml-emotion')].EndpointName" --output text 2>/dev/null || echo "")

if [ -n "$ENDPOINTS" ]; then
    echo -e "${RED}   Found SageMaker endpoints (these cost ~\$36/month each!)${NC}"
    for endpoint in $ENDPOINTS; do
        echo -e "${YELLOW}   Deleting endpoint: $endpoint${NC}"
        aws sagemaker delete-endpoint --endpoint-name "$endpoint" --region "$AWS_REGION" 2>/dev/null || true
    done
    echo -e "${GREEN}✓${NC} SageMaker endpoints deleted"
else
    echo -e "${GREEN}✓${NC} No SageMaker endpoints found"
fi

# Delete SageMaker endpoint configurations
echo -e "${YELLOW}   Checking for SageMaker endpoint configs...${NC}"
CONFIGS=$(aws sagemaker list-endpoint-configs --region "$AWS_REGION" --query "EndpointConfigs[?contains(EndpointConfigName, 'ml-emotion')].EndpointConfigName" --output text 2>/dev/null || echo "")

if [ -n "$CONFIGS" ]; then
    # Wait for endpoints to fully delete before removing configs
    if [ -n "$ENDPOINTS" ]; then
        echo -e "${YELLOW}   Waiting 30s for endpoints to fully delete...${NC}"
        sleep 30
    fi

    for config in $CONFIGS; do
        echo -e "${YELLOW}   Deleting endpoint config: $config${NC}"
        aws sagemaker delete-endpoint-config --endpoint-config-name "$config" --region "$AWS_REGION" 2>/dev/null || true
    done
    echo -e "${GREEN}✓${NC} SageMaker endpoint configs deleted"
else
    echo -e "${GREEN}✓${NC} No SageMaker endpoint configs found"
fi

# Delete SageMaker models
echo -e "${YELLOW}   Checking for SageMaker models...${NC}"
MODELS=$(aws sagemaker list-models --region "$AWS_REGION" --query "Models[?contains(ModelName, 'ml-emotion')].ModelName" --output text 2>/dev/null || echo "")

if [ -n "$MODELS" ]; then
    for model in $MODELS; do
        echo -e "${YELLOW}   Deleting model: $model${NC}"
        aws sagemaker delete-model --model-name "$model" --region "$AWS_REGION" 2>/dev/null || true
    done
    echo -e "${GREEN}✓${NC} SageMaker models deleted"
else
    echo -e "${GREEN}✓${NC} No SageMaker models found"
fi

# Delete SageMaker custom container ECR repository
echo -e "${YELLOW}   Checking for SageMaker ECR repository...${NC}"
if aws ecr describe-repositories --repository-names "ml-speech-emotion-sklearn" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "${YELLOW}   Deleting ECR repository: ml-speech-emotion-sklearn${NC}"
    aws ecr delete-repository --repository-name "ml-speech-emotion-sklearn" --region "$AWS_REGION" --force 2>/dev/null || true
    echo -e "${GREEN}✓${NC} SageMaker ECR repository deleted"
else
    echo -e "${GREEN}✓${NC} No SageMaker ECR repository found"
fi

# Step 5: Manual cleanup of orphaned AWS resources
echo ""
echo -e "${YELLOW}[Step 5/8]${NC} Checking for orphaned AWS resources..."

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

    # Check for target groups (orphaned from deleted load balancers)
    echo -e "${YELLOW}   Checking for orphaned target groups...${NC}"
    TGS=$(aws elbv2 describe-target-groups --region "$AWS_REGION" --query "TargetGroups[?VpcId=='$VPC_ID' && contains(TargetGroupName, 'k8s')].TargetGroupArn" --output text 2>/dev/null || echo "")

    if [ -n "$TGS" ]; then
        echo -e "${RED}   Found orphaned target groups, deleting...${NC}"
        for tg_arn in $TGS; do
            echo -e "${YELLOW}   Deleting: $tg_arn${NC}"
            aws elbv2 delete-target-group --target-group-arn "$tg_arn" --region "$AWS_REGION" 2>/dev/null || true
        done
        echo -e "${GREEN}✓${NC} Orphaned target groups deleted"
    else
        echo -e "${GREEN}✓${NC} No orphaned target groups found"
    fi

    # Check for security groups
    echo -e "${YELLOW}   Checking for Kubernetes security groups...${NC}"
    K8S_SGS=$(aws ec2 describe-security-groups --region "$AWS_REGION" --filters "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[?contains(GroupName, 'k8s')].GroupId" --output text 2>/dev/null || echo "")

    if [ -n "$K8S_SGS" ]; then
        echo -e "${RED}   Found orphaned Kubernetes security groups, deleting...${NC}"
        for sg_id in $K8S_SGS; do
            echo -e "${YELLOW}   Deleting: $sg_id${NC}"
            aws ec2 delete-security-group --group-id "$sg_id" --region "$AWS_REGION" 2>/dev/null || true
        done
        echo -e "${GREEN}✓${NC} Orphaned security groups deleted"
    else
        echo -e "${GREEN}✓${NC} No orphaned Kubernetes security groups found"
    fi

    # Check for orphaned EBS volumes (from PVCs)
    echo -e "${YELLOW}   Checking for EBS volumes with Kubernetes tags...${NC}"
    VOLUMES=$(aws ec2 describe-volumes --region "$AWS_REGION" --filters "Name=tag-key,Values=kubernetes.io/cluster/${EKS_CLUSTER_NAME}" --query "Volumes[?State=='available'].VolumeId" --output text 2>/dev/null || echo "")

    if [ -n "$VOLUMES" ]; then
        echo -e "${RED}   Found orphaned EBS volumes, deleting...${NC}"
        for vol_id in $VOLUMES; do
            echo -e "${YELLOW}   Deleting: $vol_id${NC}"
            aws ec2 delete-volume --volume-id "$vol_id" --region "$AWS_REGION" 2>/dev/null || true
        done
        echo -e "${GREEN}✓${NC} Orphaned EBS volumes deleted"
    else
        echo -e "${GREEN}✓${NC} No orphaned EBS volumes found"
    fi
else
    echo -e "${YELLOW}⚠️  Could not retrieve VPC ID from Terraform state${NC}"
    echo -e "${YELLOW}   Skipping VPC-based orphaned resource check...${NC}"
fi

# Clean up CloudWatch log groups (not VPC-specific)
echo -e "${YELLOW}   Checking for CloudWatch log groups...${NC}"
LOG_GROUPS=$(aws logs describe-log-groups --region "$AWS_REGION" --query "logGroups[?starts_with(logGroupName, '/aws/sagemaker/') || starts_with(logGroupName, '/aws/eks/${EKS_CLUSTER_NAME}')].logGroupName" --output text 2>/dev/null || echo "")

if [ -n "$LOG_GROUPS" ]; then
    echo -e "${RED}   Found CloudWatch log groups, deleting...${NC}"
    for log_group in $LOG_GROUPS; do
        echo -e "${YELLOW}   Deleting: $log_group${NC}"
        aws logs delete-log-group --log-group-name "$log_group" --region "$AWS_REGION" 2>/dev/null || true
    done
    echo -e "${GREEN}✓${NC} CloudWatch log groups deleted"
else
    echo -e "${GREEN}✓${NC} No CloudWatch log groups found"
fi

# Step 6: Empty S3 buckets before Terraform destroy
echo ""
echo -e "${YELLOW}[Step 6/8]${NC} Emptying S3 buckets..."

# Get S3 bucket names from Terraform state
cd "$(dirname "$0")"
MODEL_BUCKET=$(terraform output -raw model_storage_bucket_name 2>/dev/null || echo "")

if [ -n "$MODEL_BUCKET" ]; then
    echo -e "${YELLOW}   Found S3 bucket: ${MODEL_BUCKET}${NC}"

    # Check if bucket exists
    if aws s3 ls "s3://${MODEL_BUCKET}" --region "$AWS_REGION" --profile "$AWS_PROFILE" > /dev/null 2>&1; then
        echo -e "${YELLOW}   Emptying bucket (including all versions)...${NC}"

        # Create temporary file for deletion manifest
        TEMP_DELETE_FILE="/tmp/s3_delete_manifest_$$.json"

        # Get all versions and delete markers
        echo -e "${YELLOW}   → Listing all object versions...${NC}"
        aws s3api list-object-versions \
            --bucket "${MODEL_BUCKET}" \
            --region "$AWS_REGION" \
            --profile "$AWS_PROFILE" \
            --output=json \
            --query='{Objects: [Versions,DeleteMarkers][].{Key:Key,VersionId:VersionId}[]}' > "$TEMP_DELETE_FILE" 2>/dev/null || echo '{"Objects":null}' > "$TEMP_DELETE_FILE"

        # Check if there are objects to delete
        OBJECT_LIST=$(cat "$TEMP_DELETE_FILE" | grep -c '"Key"' || echo "0")

        if [ "$OBJECT_LIST" -gt "0" ]; then
            echo -e "${YELLOW}   Found ${OBJECT_LIST} object versions to delete${NC}"
            echo -e "${YELLOW}   → Deleting all versions and markers...${NC}"

            # Delete all versions and markers
            aws s3api delete-objects \
                --bucket "${MODEL_BUCKET}" \
                --region "$AWS_REGION" \
                --profile "$AWS_PROFILE" \
                --delete "file://${TEMP_DELETE_FILE}" 2>&1 | head -20 || true

            echo -e "${GREEN}✓${NC} Object versions deleted"
        fi

        # Clean up temp file
        rm -f "$TEMP_DELETE_FILE"

        # Final verification - check if bucket is truly empty
        echo -e "${YELLOW}   → Verifying bucket is empty...${NC}"
        REMAINING=$(aws s3api list-object-versions \
            --bucket "${MODEL_BUCKET}" \
            --region "$AWS_REGION" \
            --profile "$AWS_PROFILE" \
            --query '[Versions,DeleteMarkers][]' \
            --output text 2>/dev/null | wc -l || echo "0")

        if [ "$REMAINING" -eq "0" ]; then
            echo -e "${GREEN}✓${NC} S3 bucket is now empty and ready for deletion"
        else
            echo -e "${RED}✗${NC} Warning: Bucket still contains ${REMAINING} versioned objects"
            echo -e "${YELLOW}   Listing remaining objects:${NC}"
            aws s3api list-object-versions \
                --bucket "${MODEL_BUCKET}" \
                --region "$AWS_REGION" \
                --profile "$AWS_PROFILE" \
                --query '[Versions[].{Key:Key,VersionId:VersionId},DeleteMarkers[].{Key:Key,VersionId:VersionId}][]' \
                --output table 2>/dev/null || true
            echo -e "${YELLOW}   Terraform destroy will likely fail. Consider manual cleanup:${NC}"
            echo -e "${YELLOW}   aws s3 rb s3://${MODEL_BUCKET} --force --profile ${AWS_PROFILE}${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  S3 bucket not found or already deleted${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Could not retrieve S3 bucket name from Terraform state${NC}"
    echo -e "${YELLOW}   Skipping S3 bucket cleanup...${NC}"
fi

# Step 7: Refresh Terraform state to sync with AWS reality
echo ""
echo -e "${YELLOW}[Step 7/8]${NC} Refreshing Terraform state from AWS..."
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

# Step 8: Run Terraform destroy
echo -e "${YELLOW}[Step 8/8]${NC} Running Terraform destroy..."
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
