#!/bin/bash
set -e

# Script to upload trained models to S3 for SageMaker deployment
# Usage: ./scripts/upload_model_to_s3.sh <version> [--profile <aws-profile>]
# Example: ./scripts/upload_model_to_s3.sh v5 --profile ml-ser-deploy

# Determine project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

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
cd "$PROJECT_ROOT/deployment/terraform"
S3_BUCKET=$(terraform output -raw model_storage_bucket_name 2>/dev/null || echo "")
cd "$PROJECT_ROOT"

if [ -z "$S3_BUCKET" ]; then
  echo -e "${RED}❌ Error: Could not get S3 bucket name from Terraform${NC}"
  echo "Please ensure Terraform has been applied and outputs are available"
  echo "Run: cd deployment/terraform && terraform output model_storage_bucket_name"
  exit 1
fi

echo -e "${GREEN}✓ Using S3 bucket: $S3_BUCKET${NC}"

# Define paths (all files should be in MODEL_DIR)
MODEL_DIR="$PROJECT_ROOT/backend/models/$MODEL_VERSION"

# Validate model files exist locally
echo -e "${BLUE}🔍 Validating model files...${NC}"

if [ ! -f "$MODEL_DIR/model.pkl" ]; then
  echo -e "${RED}❌ Error: Model not found at $MODEL_DIR/model.pkl${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ Found model.pkl ($(du -h "$MODEL_DIR/model.pkl" | cut -f1))${NC}"

if [ ! -f "$MODEL_DIR/metadata.json" ]; then
  echo -e "${RED}❌ Error: Metadata not found at $MODEL_DIR/metadata.json${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ Found metadata.json${NC}"

if [ ! -f "$MODEL_DIR/ultra_ensemble.py" ]; then
  echo -e "${RED}❌ Error: UltraEnsembleModel class not found at $MODEL_DIR/ultra_ensemble.py${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ Found ultra_ensemble.py${NC}"

if [ ! -f "$MODEL_DIR/inference.py" ]; then
  echo -e "${RED}❌ Error: Inference handler not found at $MODEL_DIR/inference.py${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ Found inference.py${NC}"

if [ ! -f "$MODEL_DIR/requirements.txt" ]; then
  echo -e "${RED}❌ Error: Requirements not found at $MODEL_DIR/requirements.txt${NC}"
  exit 1
fi
echo -e "${GREEN}  ✓ Found requirements.txt${NC}"

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
aws s3 cp "$MODEL_DIR/metadata.json" \
  "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/metadata.json" \
  --profile "$AWS_PROFILE"

echo -e "${GREEN}  ✓ metadata.json uploaded${NC}"

# Upload ultra_ensemble.py (CRITICAL for unpickling model.pkl)
echo -e "${YELLOW}  → Uploading ultra_ensemble.py...${NC}"
aws s3 cp "$MODEL_DIR/ultra_ensemble.py" \
  "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/ultra_ensemble.py" \
  --profile "$AWS_PROFILE"

echo -e "${GREEN}  ✓ ultra_ensemble.py uploaded${NC}"

# Upload inference.py (SageMaker inference handler)
echo -e "${YELLOW}  → Uploading inference.py...${NC}"
aws s3 cp "$MODEL_DIR/inference.py" \
  "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/inference.py" \
  --profile "$AWS_PROFILE"

echo -e "${GREEN}  ✓ inference.py uploaded${NC}"

# Upload requirements.txt (Python dependencies)
echo -e "${YELLOW}  → Uploading requirements.txt...${NC}"
aws s3 cp "$MODEL_DIR/requirements.txt" \
  "s3://$S3_BUCKET/raw-models/$MODEL_VERSION/requirements.txt" \
  --profile "$AWS_PROFILE"

echo -e "${GREEN}  ✓ requirements.txt uploaded${NC}"

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

# Success message for raw models
echo ""
echo -e "${GREEN}✅ Raw model files uploaded successfully!${NC}"
echo -e "${BLUE}   S3 URI: s3://$S3_BUCKET/raw-models/$MODEL_VERSION/${NC}"

# ============================================================================
# Package for SageMaker
# ============================================================================

echo ""
echo -e "${BLUE}📦 Packaging model for SageMaker deployment...${NC}"
echo ""

# Create temporary packaging directory
TEMP_PACKAGE_DIR="/tmp/sagemaker_package_$$"
mkdir -p "$TEMP_PACKAGE_DIR/code"

# Copy model files to package structure
echo -e "${YELLOW}  → Copying files to package structure...${NC}"

# Root level files
cp "$MODEL_DIR/model.pkl" "$TEMP_PACKAGE_DIR/"
cp "$MODEL_DIR/metadata.json" "$TEMP_PACKAGE_DIR/"

# Code directory
cp "$MODEL_DIR/ultra_ensemble.py" "$TEMP_PACKAGE_DIR/code/"
cp "$MODEL_DIR/inference.py" "$TEMP_PACKAGE_DIR/code/"
cp "$MODEL_DIR/requirements.txt" "$TEMP_PACKAGE_DIR/code/"

echo -e "${GREEN}  ✓ Files copied to package structure${NC}"

# Create tar.gz archive
echo -e "${YELLOW}  → Creating model.tar.gz (this may take a few minutes)...${NC}"
cd "$TEMP_PACKAGE_DIR"
tar -czf "$PROJECT_ROOT/model.tar.gz" .
cd "$PROJECT_ROOT"

PACKAGE_SIZE=$(du -h model.tar.gz | cut -f1)
echo -e "${GREEN}  ✓ model.tar.gz created ($PACKAGE_SIZE)${NC}"

# Upload SageMaker package to S3
echo ""
echo -e "${YELLOW}  → Uploading SageMaker package to S3...${NC}"
aws s3 cp model.tar.gz \
  "s3://$S3_BUCKET/sagemaker-models/$MODEL_VERSION/model.tar.gz" \
  --profile "$AWS_PROFILE" \
  --no-progress

echo -e "${GREEN}  ✓ SageMaker package uploaded${NC}"

# Cleanup
rm -rf "$TEMP_PACKAGE_DIR"
rm model.tar.gz

# Final success message
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Model $MODEL_VERSION uploaded and packaged successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📁 Raw model files:${NC}"
echo "   s3://$S3_BUCKET/raw-models/$MODEL_VERSION/"
echo ""
echo -e "${BLUE}📦 SageMaker package:${NC}"
echo "   s3://$S3_BUCKET/sagemaker-models/$MODEL_VERSION/model.tar.gz"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Verify upload: aws s3 ls s3://$S3_BUCKET/sagemaker-models/$MODEL_VERSION/ --profile $AWS_PROFILE"
echo "  2. Trigger deployment: gh workflow run cd.yml -f model_version=$MODEL_VERSION"
echo ""
