#!/bin/bash
set -e

# This script attaches the IAM role to the existing EBS CSI driver addon
# Run this AFTER terraform apply

CLUSTER_NAME="ml-speech-emotion-prod-eks"
REGION="us-east-1"

echo "Getting IAM role ARN from terraform output..."
ROLE_ARN=$(terraform output -raw ebs_csi_driver_role_arn)

if [ -z "$ROLE_ARN" ]; then
  echo "❌ Error: Could not get IAM role ARN from terraform"
  echo "Make sure you've run 'terraform apply' first"
  exit 1
fi

echo "IAM Role ARN: $ROLE_ARN"
echo ""
echo "Updating EBS CSI driver addon to use IAM role..."

aws eks update-addon \
  --cluster-name "$CLUSTER_NAME" \
  --addon-name aws-ebs-csi-driver \
  --service-account-role-arn "$ROLE_ARN" \
  --region "$REGION" \
  --resolve-conflicts OVERWRITE

echo ""
echo "✅ EBS CSI driver addon updated successfully!"
echo ""
echo "Waiting 30 seconds for pods to restart..."
sleep 30

echo ""
echo "Checking EBS CSI controller pods..."
kubectl get pods -n kube-system | grep ebs-csi-controller

echo ""
echo "Checking service account annotation..."
kubectl get sa ebs-csi-controller-sa -n kube-system -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}'
echo ""
