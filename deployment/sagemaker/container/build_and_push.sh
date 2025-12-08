#!/bin/bash
set -e

# Build and push custom SageMaker inference container to ECR
# Usage: ./build_and_push.sh [--profile <aws-profile>]

# Configuration
IMAGE_NAME="ml-speech-emotion-sklearn"
IMAGE_TAG="1.7.2-py310"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-default}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)
      AWS_PROFILE="$2"
      shift 2
      ;;
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile "$AWS_PROFILE")

# Full image URI
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_URI="${ECR_URI}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Building Custom SageMaker Container"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Image Name:  ${IMAGE_NAME}"
echo "  Image Tag:   ${IMAGE_TAG}"
echo "  ECR URI:     ${FULL_IMAGE_URI}"
echo "  Region:      ${AWS_REGION}"
echo "  Account:     ${ACCOUNT_ID}"
echo ""

# Create ECR repository if it doesn't exist
echo "Creating ECR repository (if needed)..."
aws ecr describe-repositories --repository-names "${IMAGE_NAME}" --region "${AWS_REGION}" --profile "$AWS_PROFILE" > /dev/null 2>&1 || \
  aws ecr create-repository --repository-name "${IMAGE_NAME}" --region "${AWS_REGION}" --profile "$AWS_PROFILE"
echo "✓ ECR repository ready"

# Login to ECR
echo ""
echo "Logging into ECR..."
aws ecr get-login-password --region "${AWS_REGION}" --profile "$AWS_PROFILE" | \
  docker login --username AWS --password-stdin "${ECR_URI}"
echo "✓ ECR login successful"

# Build the Docker image
echo ""
echo "Building Docker image..."
cd "$SCRIPT_DIR"
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .
echo "✓ Docker image built"

# Tag for ECR
echo ""
echo "Tagging image for ECR..."
docker tag "${IMAGE_NAME}:${IMAGE_TAG}" "${FULL_IMAGE_URI}"
echo "✓ Image tagged"

# Push to ECR
echo ""
echo "Pushing to ECR (this may take a few minutes)..."
docker push "${FULL_IMAGE_URI}"
echo "✓ Image pushed to ECR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Container build and push complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Container URI: ${FULL_IMAGE_URI}"
echo ""
echo "To use this container, update deploy_to_sagemaker.py:"
echo ""
echo "  SKLEARN_CONTAINER_IMAGES = {"
echo "      'us-east-1': '${FULL_IMAGE_URI}',"
echo "  }"
echo ""
