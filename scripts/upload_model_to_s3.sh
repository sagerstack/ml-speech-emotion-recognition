#!/bin/bash
set -e

# Script to upload trained models to S3 for SageMaker deployment
# Usage: ./scripts/upload_model_to_s3.sh <version> [--profile <aws-profile>]
# Example: ./scripts/upload_model_to_s3.sh v5 --profile ml-ser-deploy

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
MODEL_VERSION=""
AWS_PROFILE="default"

while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)
      AWS_PROFILE="$2"
      shift 2
      ;;
    *)
      if [ -z "$MODEL_VERSION" ]; then
        MODEL_VERSION="$1"
      else
        echo -e "${RED}❌ Error: Unknown argument: $1${NC}"
        exit 1
      fi
      shift
      ;;
  esac
done

# Validate model version provided
if [ -z "$MODEL_VERSION" ]; then
  echo -e "${RED}❌ Error: Model version required${NC}"
  echo ""
  echo "Usage: ./scripts/upload_model_to_s3.sh <version> [--profile <aws-profile>]"
  echo "Example: ./scripts/upload_model_to_s3.sh v5 --profile ml-ser-deploy"
  echo ""
  echo "Available versions:"
  ls -d backend/models/v* 2>/dev/null | xargs -n 1 basename || echo "  (none found)"
  exit 1
fi

# Get S3 bucket name from Terraform output
echo -e "${BLUE}📡 Fetching S3 bucket name from Terraform...${NC}"
cd deployment/terraform
S3_BUCKET=$(terraform output -raw model_storage_bucket_name 2>/dev/null || echo "")
cd ../..

if [ -z "$S3_BUCKET" ]; then
  echo -e "${RED}❌ Error: Could not get S3 bucket name from Terraform${NC}"
  echo "Please ensure Terraform has been applied and outputs are available"
  echo "Run: cd deployment/terraform && terraform output model_storage_bucket_name"
  exit 1
fi

echo -e "${GREEN}✓ Using S3 bucket: $S3_BUCKET${NC}"

# Define paths
MODEL_DIR="backend/models/$MODEL_VERSION"
METADATA_DIR="backend/app/infrastructure/model/$MODEL_VERSION"

# Validate model files exist locally
echo -e "${BLUE}🔍 Validating model files...${NC}"

if [ ! -f "$MODEL_DIR/model.pkl" ]; then
  echo -e "${RED}❌ Error: Model not found at $MODEL_DIR/model.pkl${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ Found model.pkl ($(du -h "$MODEL_DIR/model.pkl" | cut -f1))${NC}"

if [ ! -f "$METADATA_DIR/metadata.json" ]; then
  echo -e "${RED}❌ Error: Metadata not found at $METADATA_DIR/metadata.json${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ Found metadata.json${NC}"

if [ ! -f "$METADATA_DIR/feature_extractor.py" ]; then
  echo -e "${RED}❌ Error: Feature extractor not found at $METADATA_DIR/feature_extractor.py${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ Found feature_extractor.py${NC}"

# Upload files to S3
echo ""
echo -e "${BLUE}📦 Uploading model $MODEL_VERSION to S3...${NC}"

# Upload model.pkl (large file)
echo -e "${YELLOW}  → Uploading model.pkl (this may take a few minutes)...${NC}"
aws s3 cp "$MODEL_DIR/model.pkl" \
  "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/model.pkl" \
  --profile "$AWS_PROFILE" \
  --no-progress

echo -e "${GREEN}  ✓ model.pkl uploaded${NC}"

# Upload metadata.json
echo -e "${YELLOW}  → Uploading metadata.json...${NC}"
aws s3 cp "$METADATA_DIR/metadata.json" \
  "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/metadata.json" \
  --profile "$AWS_PROFILE"

echo -e "${GREEN}  ✓ metadata.json uploaded${NC}"

# Upload feature_extractor.py
echo -e "${YELLOW}  → Uploading feature_extractor.py...${NC}"
aws s3 cp "$METADATA_DIR/feature_extractor.py" \
  "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/feature_extractor.py" \
  --profile "$AWS_PROFILE"

echo -e "${GREEN}  ✓ feature_extractor.py uploaded${NC}"

# Upload __init__.py if exists
if [ -f "$METADATA_DIR/__init__.py" ]; then
  echo -e "${YELLOW}  → Uploading __init__.py...${NC}"
  aws s3 cp "$METADATA_DIR/__init__.py" \
    "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/__init__.py" \
    --profile "$AWS_PROFILE"
  echo -e "${GREEN}  ✓ __init__.py uploaded${NC}"
fi

# Create and upload manifest
echo -e "${YELLOW}  → Creating upload manifest...${NC}"
MODEL_SIZE=$(stat -f%z "$MODEL_DIR/model.pkl" 2>/dev/null || stat -c%s "$MODEL_DIR/model.pkl")
GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo 'unknown')
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')

cat > /tmp/manifest.json <<EOF
{
  "model_version": "$MODEL_VERSION",
  "uploaded_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "uploaded_by": "$(whoami)@$(hostname)",
  "git_commit": "$GIT_COMMIT",
  "git_branch": "$GIT_BRANCH",
  "model_size_bytes": $MODEL_SIZE,
  "s3_bucket": "$S3_BUCKET",
  "s3_prefix": "raw-models/$MODEL_VERSION/"
}
EOF

aws s3 cp /tmp/manifest.json \
  "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/manifest.json" \
  --profile "$AWS_PROFILE"

echo -e "${GREEN}  ✓ manifest.json uploaded${NC}"
rm /tmp/manifest.json

# Success message
echo ""
echo -e "${GREEN}✅ Model $MODEL_VERSION uploaded successfully!${NC}"
echo -e "${BLUE}   S3 URI: s3://$S3_BUCKET/raw-models/$MODEL_VERSION/${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Verify upload: aws s3 ls s3://$S3_BUCKET/raw-models/$MODEL_VERSION/ --profile $AWS_PROFILE"
echo "  2. Trigger deployment: gh workflow run cd.yml -f model_version=$MODEL_VERSION"
echo ""
