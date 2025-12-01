#!/bin/bash

# Import existing EKS addons into terraform state
# This resolves the "Addon already exists" error

CLUSTER_NAME="ml-speech-emotion-prod-eks"

echo "Importing aws-ebs-csi-driver addon..."
terraform import 'module.eks.aws_eks_addon.this["aws-ebs-csi-driver"]' "${CLUSTER_NAME}:aws-ebs-csi-driver"

echo ""
echo "✓ Import complete. You can now run 'terraform apply' to update the addon configuration."
