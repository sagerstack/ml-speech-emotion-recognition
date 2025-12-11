#!/bin/bash
#
# Complete HTTPS Setup for ML Speech Emotion Recognition
# This script automates the entire process: ACM Certificate → CloudFront → DNS
#
# Supports both CREATE (new setup) and UPDATE (update existing CloudFront origin)
#
# Prerequisites:
# 1. Domain registered in Route 53 (Status: Successful)
# 2. EKS cluster running with ALB
# 3. AWS CLI configured with appropriate permissions
#
# Usage:
#   ./scripts/complete-https-setup.sh <domain-name> [--update]
#
# Examples:
#   ./scripts/complete-https-setup.sh sagerstack.com           # Auto-detect mode
#   ./scripts/complete-https-setup.sh sagerstack.com --update  # Force update mode
#   ./scripts/complete-https-setup.sh sagerstack.com --create  # Force create mode
#

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

DOMAIN_NAME="${1}"
MODE="${2:-auto}"  # auto, --update, or --create

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

print_step() {
  echo ""
  echo "═══════════════════════════════════════════════════════════════"
  echo "  $1"
  echo "═══════════════════════════════════════════════════════════════"
  echo ""
}

if [ -z "$DOMAIN_NAME" ]; then
  print_header "Complete HTTPS Setup for ML Speech Emotion Recognition"
  echo ""
  echo "Usage: $0 <domain-name> [--update|--create]"
  echo ""
  echo "Modes:"
  echo "  (default)   Auto-detect: update if exists, create if not"
  echo "  --update    Force update mode (update CloudFront origin only)"
  echo "  --create    Force create mode (full setup)"
  echo ""
  echo "Examples:"
  echo "  $0 sagerstack.com"
  echo "  $0 sagerstack.com --update"
  echo ""
  echo "Prerequisites:"
  echo "  1. ✅ Domain registered in Route 53"
  echo "  2. ✅ EKS cluster running with ALB"
  echo "  3. ✅ AWS CLI configured"
  echo ""
  exit 1
fi

print_header "HTTPS Setup for: $DOMAIN_NAME"
echo ""

# Verify AWS credentials
echo "🔐 Verifying AWS credentials..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
  echo -e "${RED}❌ AWS credentials not configured or expired${NC}"
  echo "Please run: aws sso login"
  exit 1
fi
echo -e "${GREEN}✓ AWS credentials valid${NC}"
echo ""

# Get current ALB DNS from EKS
echo "🔍 Getting current ALB DNS from EKS..."
ALB_DNS=$(kubectl get ingress -n ml-speech-emotion -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")

if [ -z "$ALB_DNS" ]; then
  echo -e "${RED}❌ Could not get ALB DNS from EKS${NC}"
  echo "Make sure the ingress is deployed and has an ALB assigned"
  exit 1
fi
echo -e "${GREEN}✓ ALB DNS: $ALB_DNS${NC}"
echo ""

# Check for existing CloudFront distribution
echo "🔍 Checking for existing CloudFront distribution..."
EXISTING_DIST=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Aliases.Items, '$DOMAIN_NAME')].{Id:Id,Domain:DomainName,Origin:Origins.Items[0].DomainName,Status:Status}" \
  --output json 2>/dev/null || echo "[]")

EXISTING_DIST_ID=$(echo "$EXISTING_DIST" | jq -r '.[0].Id // empty')
EXISTING_ORIGIN=$(echo "$EXISTING_DIST" | jq -r '.[0].Origin // empty')
EXISTING_CF_DOMAIN=$(echo "$EXISTING_DIST" | jq -r '.[0].Domain // empty')
EXISTING_STATUS=$(echo "$EXISTING_DIST" | jq -r '.[0].Status // empty')

# Determine mode
if [ "$MODE" = "--update" ]; then
  OPERATION="update"
elif [ "$MODE" = "--create" ]; then
  OPERATION="create"
elif [ -n "$EXISTING_DIST_ID" ] && [ "$EXISTING_DIST_ID" != "null" ]; then
  OPERATION="update"
  echo -e "${BLUE}📋 Found existing CloudFront distribution${NC}"
else
  OPERATION="create"
  echo -e "${BLUE}📋 No existing distribution found${NC}"
fi

echo ""
OPERATION_UPPER=$(echo "$OPERATION" | tr '[:lower:]' '[:upper:]')
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Operation Mode: $OPERATION_UPPER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Domain:          $DOMAIN_NAME"
echo "  Current ALB:     $ALB_DNS"
if [ "$OPERATION" = "update" ]; then
  echo "  Distribution ID: $EXISTING_DIST_ID"
  echo "  Current Origin:  $EXISTING_ORIGIN"
  echo "  Status:          $EXISTING_STATUS"
fi
echo ""

if [ "$OPERATION" = "update" ]; then
  # ============================================================
  # UPDATE MODE - Just update the CloudFront origin
  # ============================================================

  echo "This will:"
  echo "  1. Update CloudFront origin to new ALB"
  echo "  2. Invalidate CloudFront cache"
  echo ""
  read -p "Continue? (y/n): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi

  # Check if origin already matches
  if [ "$EXISTING_ORIGIN" = "$ALB_DNS" ]; then
    echo ""
    echo -e "${GREEN}✅ Origin is already up to date!${NC}"
    echo "   Current: $EXISTING_ORIGIN"
    echo "   New:     $ALB_DNS"
    echo ""
    echo "No changes needed."

    # Still offer to invalidate cache
    read -p "Would you like to invalidate the CloudFront cache anyway? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      echo "🔄 Creating cache invalidation..."
      INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id "$EXISTING_DIST_ID" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)
      echo -e "${GREEN}✓ Cache invalidation created: $INVALIDATION_ID${NC}"
    fi
    exit 0
  fi

  print_step "Updating CloudFront Origin"

  echo "🔄 Updating CloudFront origin..."
  echo "   From: $EXISTING_ORIGIN"
  echo "   To:   $ALB_DNS"
  echo ""

  # Get current distribution config
  aws cloudfront get-distribution-config --id "$EXISTING_DIST_ID" > /tmp/cf-current-config.json

  ETAG=$(jq -r '.ETag' /tmp/cf-current-config.json)

  # Update the origin in the config
  jq --arg new_origin "$ALB_DNS" '
    .DistributionConfig.Origins.Items[0].DomainName = $new_origin |
    .DistributionConfig.Origins.Items[0].Id = $new_origin |
    .DistributionConfig.DefaultCacheBehavior.TargetOriginId = $new_origin |
    .DistributionConfig
  ' /tmp/cf-current-config.json > /tmp/cf-update-config.json

  # Apply the update
  UPDATE_OUTPUT=$(aws cloudfront update-distribution \
    --id "$EXISTING_DIST_ID" \
    --if-match "$ETAG" \
    --distribution-config file:///tmp/cf-update-config.json \
    2>&1)

  if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to update distribution:${NC}"
    echo "$UPDATE_OUTPUT"
    exit 1
  fi

  echo -e "${GREEN}✅ CloudFront origin updated successfully!${NC}"
  echo ""

  # Create cache invalidation
  echo "🔄 Creating cache invalidation..."
  INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$EXISTING_DIST_ID" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text)
  echo -e "${GREEN}✓ Cache invalidation created: $INVALIDATION_ID${NC}"
  echo ""

  # Wait for deployment
  echo "⏳ Waiting for CloudFront deployment..."
  echo "   This typically takes 2-5 minutes for origin updates."
  echo ""

  SECONDS=0
  while true; do
    STATUS=$(aws cloudfront get-distribution \
      --id "$EXISTING_DIST_ID" \
      --query 'Distribution.Status' \
      --output text)

    if [ "$STATUS" = "Deployed" ]; then
      echo ""
      echo -e "${GREEN}✅ Distribution deployed! (took ${SECONDS}s)${NC}"
      break
    fi

    printf "\r   Status: $STATUS... elapsed: ${SECONDS}s"
    sleep 10

    # Timeout after 10 minutes
    if [ $SECONDS -gt 600 ]; then
      echo ""
      echo -e "${YELLOW}⚠ Deployment taking longer than expected${NC}"
      echo "  Check status in AWS Console"
      break
    fi
  done

  # Update local config file
  cat > cloudfront-setup-config.txt <<EOF
# CloudFront Setup Configuration
# Updated: $(date)

DOMAIN_NAME="$DOMAIN_NAME"
ALB_DNS="$ALB_DNS"
DISTRIBUTION_ID="$EXISTING_DIST_ID"
CLOUDFRONT_DOMAIN="$EXISTING_CF_DOMAIN"
EOF

  # Get certificate ARN for completeness
  CERTIFICATE_ARN=$(aws acm list-certificates \
    --query "CertificateSummaryList[?contains(DomainName, '$DOMAIN_NAME')].CertificateArn" \
    --output text 2>/dev/null | head -1)

  if [ -n "$CERTIFICATE_ARN" ]; then
    echo "CERTIFICATE_ARN=\"$CERTIFICATE_ARN\"" >> cloudfront-setup-config.txt
  fi

  echo ""
  print_header "✅ CloudFront Update Complete!"
  echo ""
  echo "Distribution ID:   $EXISTING_DIST_ID"
  echo "CloudFront Domain: $EXISTING_CF_DOMAIN"
  echo "New Origin:        $ALB_DNS"
  echo ""
  echo "🌐 Your application should now be accessible at:"
  echo "   https://$DOMAIN_NAME"
  echo ""
  echo "Configuration saved to: cloudfront-setup-config.txt"
  echo ""

else
  # ============================================================
  # CREATE MODE - Full setup (certificate, CloudFront, DNS)
  # ============================================================

  echo "This will set up:"
  echo "  1. SSL/TLS Certificate (ACM)"
  echo "  2. CloudFront Distribution"
  echo "  3. DNS Records (Route 53)"
  echo "  4. HTTPS enabled for your domain"
  echo ""
  read -p "Continue? (y/n): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi

  # Create initial config file for sub-scripts
  cat > cloudfront-setup-config.txt <<EOF
# CloudFront Setup Configuration
# Created: $(date)

DOMAIN_NAME="$DOMAIN_NAME"
ALB_DNS="$ALB_DNS"
EOF

  print_step "Step 1/3: Certificate Setup (ACM + DNS Validation)"

  "${SCRIPT_DIR}/setup-cloudfront-domain.sh" "$DOMAIN_NAME" true

  if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Certificate setup failed${NC}"
    exit 1
  fi

  print_step "Step 2/3: CloudFront Distribution Creation"

  "${SCRIPT_DIR}/create-cloudfront-distribution.sh"

  if [ $? -ne 0 ]; then
    echo -e "${RED}❌ CloudFront creation failed${NC}"
    exit 1
  fi

  print_step "Step 3/3: DNS Configuration (Route 53)"

  "${SCRIPT_DIR}/setup-dns-to-cloudfront.sh"

  if [ $? -ne 0 ]; then
    echo -e "${RED}❌ DNS setup failed${NC}"
    exit 1
  fi

  echo ""
  print_header "✅ HTTPS Setup Complete!"
  echo ""
  echo "🎉 Your application is now accessible via HTTPS:"
  echo ""
  echo "   🌐 https://$DOMAIN_NAME"
  echo "   🌐 https://www.$DOMAIN_NAME"
  echo ""
  print_header "Testing Your Setup"
  echo ""
  echo "Run these tests to verify everything works:"
  echo ""
  echo "1. Test HTTPS response:"
  echo "   curl -I https://$DOMAIN_NAME"
  echo ""
  echo "2. Open in browser:"
  echo "   open https://$DOMAIN_NAME"
  echo ""
  echo "3. Test these features in the app:"
  echo "   ✅ streamlit-antd-components load correctly"
  echo "   ✅ File upload works (no AxiosError 400)"
  echo "   ✅ Live audio recording works (microphone access)"
  echo ""
fi

# Common: Show config and cache invalidation instructions
print_header "Configuration & Next Steps"
echo ""
echo "Configuration saved to: cloudfront-setup-config.txt"
echo ""
cat cloudfront-setup-config.txt
echo ""

# Extract CloudFront Distribution ID from config
if [ -f "cloudfront-setup-config.txt" ]; then
  DISTRIBUTION_ID=$(grep "DISTRIBUTION_ID=" cloudfront-setup-config.txt | cut -d'"' -f2)

  if [ -n "$DISTRIBUTION_ID" ]; then
    print_header "🔄 Automatic Cache Invalidation (Recommended)"
    echo ""
    echo "To ensure new deployments are served immediately:"
    echo ""
    echo "1. Copy your CloudFront Distribution ID:"
    echo "   📋 $DISTRIBUTION_ID"
    echo ""
    echo "2. Add it to GitHub Actions secrets/variables:"
    echo "   → Name: CLOUDFRONT_DISTRIBUTION_ID"
    echo "   → Value: $DISTRIBUTION_ID"
    echo ""
    echo "3. Future CD deployments will automatically invalidate cache"
    echo ""
  fi
fi

echo ""
print_header "Troubleshooting"
echo ""
echo "If you see 502 errors after ALB changes, run:"
echo "  $0 $DOMAIN_NAME --update"
echo ""
echo "⏰ DNS/CloudFront propagation may take 5-15 minutes"
echo ""
