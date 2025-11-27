#!/bin/bash
# Setup ECR lifecycle policies for cost management
# This script applies lifecycle policies to both backend and streamlit ECR repositories

set -e

AWS_REGION="${AWS_REGION:-us-east-1}"
BACKEND_REPO="ml-speech-emotion-backend"
STREAMLIT_REPO="ml-speech-emotion-streamlit"
POLICY_FILE="$(dirname "$0")/ecr-lifecycle-policy.json"

echo "Setting up ECR lifecycle policies in region: ${AWS_REGION}"
echo "Policy file: ${POLICY_FILE}"

# Verify policy file exists
if [ ! -f "${POLICY_FILE}" ]; then
  echo "Error: Policy file not found: ${POLICY_FILE}"
  exit 1
fi

# Apply to backend repository
echo ""
echo "Applying lifecycle policy to ${BACKEND_REPO}..."
aws ecr put-lifecycle-policy \
  --region "${AWS_REGION}" \
  --repository-name "${BACKEND_REPO}" \
  --lifecycle-policy-text "file://${POLICY_FILE}"

if [ $? -eq 0 ]; then
  echo "✅ Successfully applied lifecycle policy to ${BACKEND_REPO}"
else
  echo "❌ Failed to apply lifecycle policy to ${BACKEND_REPO}"
  exit 1
fi

# Apply to streamlit repository
echo ""
echo "Applying lifecycle policy to ${STREAMLIT_REPO}..."
aws ecr put-lifecycle-policy \
  --region "${AWS_REGION}" \
  --repository-name "${STREAMLIT_REPO}" \
  --lifecycle-policy-text "file://${POLICY_FILE}"

if [ $? -eq 0 ]; then
  echo "✅ Successfully applied lifecycle policy to ${STREAMLIT_REPO}"
else
  echo "❌ Failed to apply lifecycle policy to ${STREAMLIT_REPO}"
  exit 1
fi

echo ""
echo "🎉 ECR lifecycle policies configured successfully!"
echo ""
echo "Policy summary:"
echo "  - Keep last 10 PR images (pr-*)"
echo "  - Keep last 20 production images (SHA tags)"
echo "  - Always keep 'latest' tag"
echo ""
echo "Estimated storage: ~36 GB (30 images × 1.2 GB average)"
echo "Estimated cost: ~\$3.60/month"
