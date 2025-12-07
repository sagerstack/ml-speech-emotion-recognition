#!/bin/bash
set -e

# Script to download trained models from S3 for local development
# Usage: ./scripts/download_model_from_s3.sh <version> [--profile <aws-profile>]
# Example: ./scripts/download_model_from_s3.sh v5 --profile ml-ser-deploy

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
  echo "Usage: ./scripts/download_model_from_s3.sh <version> [--profile <aws-profile>]"
  echo "Example: ./scripts/download_model_from_s3.sh v5 --profile ml-ser-deploy"
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

# Create directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p "$MODEL_DIR"
mkdir -p "$METADATA_DIR"

# Check if model exists in S3
echo -e "${BLUE}🔍 Checking if model exists in S3...${NC}"
if ! aws s3 ls "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/model.pkl" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo -e "${RED}❌ Error: Model $MODEL_VERSION not found in S3${NC}"
  echo ""
  echo "Available models in S3:"
  aws s3 ls "s3://$S3_BUCKET/raw-models/" --profile "$AWS_PROFILE" | grep "PRE v" | awk '{print "  - " $2}' | sed 's|/||'
  exit 1
fi

echo -e "${GREEN}✓ Model found in S3${NC}"

# Download files from S3
echo ""
echo -e "${BLUE}📥 Downloading model $MODEL_VERSION from S3...${NC}"

# Download model.pkl (large file)
echo -e "${YELLOW}  → Downloading model.pkl (this may take a few minutes)...${NC}"
aws s3 cp "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/model.pkl" \
  "$MODEL_DIR/model.pkl" \
  --profile "$AWS_PROFILE"

FILE_SIZE=$(du -h "$MODEL_DIR/model.pkl" | cut -f1)
echo -e "${GREEN}  ✓ model.pkl downloaded ($FILE_SIZE)${NC}"

# Download metadata.json
echo -e "${YELLOW}  → Downloading metadata.json...${NC}"
aws s3 cp "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/metadata.json" \
  "$METADATA_DIR/metadata.json" \
  --profile "$AWS_PROFILE"

echo -e "${GREEN}  ✓ metadata.json downloaded${NC}"

# Download feature_extractor.py
echo -e "${YELLOW}  → Downloading feature_extractor.py...${NC}"
aws s3 cp "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/feature_extractor.py" \
  "$METADATA_DIR/feature_extractor.py" \
  --profile "$AWS_PROFILE"

echo -e "${GREEN}  ✓ feature_extractor.py downloaded${NC}"

# Download __init__.py if exists
if aws s3 ls "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/__init__.py" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo -e "${YELLOW}  → Downloading __init__.py...${NC}"
  aws s3 cp "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/__init__.py" \
    "$METADATA_DIR/__init__.py" \
    --profile "$AWS_PROFILE"
  echo -e "${GREEN}  ✓ __init__.py downloaded${NC}"
else
  echo -e "${YELLOW}  ⚠ __init__.py not found in S3 (optional file)${NC}"
fi

# Download manifest if exists
if aws s3 ls "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/manifest.json" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo -e "${YELLOW}  → Downloading manifest.json...${NC}"
  aws s3 cp "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/manifest.json" \
    "/tmp/model-manifest-$MODEL_VERSION.json" \
    --profile "$AWS_PROFILE"

  echo -e "${GREEN}  ✓ manifest.json downloaded${NC}"
  echo ""
  echo -e "${BLUE}📋 Model manifest:${NC}"
  cat "/tmp/model-manifest-$MODEL_VERSION.json" | python3 -m json.tool
  rm "/tmp/model-manifest-$MODEL_VERSION.json"
fi

# Success message
echo ""
echo -e "${GREEN}✅ Model $MODEL_VERSION downloaded successfully!${NC}"
echo -e "${BLUE}   Local path: $MODEL_DIR/${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Verify model: python -c \"import pickle; model = pickle.load(open('$MODEL_DIR/model.pkl', 'rb')); print(model)\""
echo "  2. Run backend: poetry run uvicorn app.main:app --reload"
echo ""
