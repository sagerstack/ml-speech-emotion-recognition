#!/bin/bash
#
# Complete HTTPS Setup for ML Speech Emotion Recognition
# This script automates the entire process: ACM Certificate → CloudFront → DNS
#
# Prerequisites:
# 1. Domain registered in Route 53 (Status: Successful)
# 2. EKS cluster running with ALB
# 3. AWS CLI configured with appropriate permissions
#
# Usage:
#   ./scripts/complete-https-setup.sh your-domain.com
#

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

DOMAIN_NAME="${1}"

if [ -z "$DOMAIN_NAME" ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Complete HTTPS Setup for ML Speech Emotion Recognition"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "Usage: $0 <domain-name>"
  echo ""
  echo "Example:"
  echo "  $0 ml-emotion.com"
  echo ""
  echo "Prerequisites:"
  echo "  1. ✅ Domain registered in Route 53"
  echo "  2. ✅ EKS cluster running with ALB"
  echo "  3. ✅ AWS CLI configured"
  echo ""
  exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Complete HTTPS Setup for: $DOMAIN_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
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

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 1/3: Certificate Setup (ACM + DNS Validation)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

"${SCRIPT_DIR}/setup-cloudfront-domain.sh" "$DOMAIN_NAME" true

if [ $? -ne 0 ]; then
  echo "❌ Certificate setup failed"
  exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 2/3: CloudFront Distribution Creation"
echo "═══════════════════════════════════════════════════════════════"
echo ""

"${SCRIPT_DIR}/create-cloudfront-distribution.sh"

if [ $? -ne 0 ]; then
  echo "❌ CloudFront creation failed"
  exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 3/3: DNS Configuration (Route 53)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

"${SCRIPT_DIR}/setup-dns-to-cloudfront.sh"

if [ $? -ne 0 ]; then
  echo "❌ DNS setup failed"
  exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ HTTPS Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 Your application is now accessible via HTTPS:"
echo ""
echo "   🌐 https://$DOMAIN_NAME"
echo "   🌐 https://www.$DOMAIN_NAME"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Testing Your Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
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
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Configuration Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Setup details saved in: cloudfront-setup-config.txt"
echo ""
cat cloudfront-setup-config.txt
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔄 Enable Automatic Cache Invalidation (Important!)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Extract CloudFront Distribution ID from config
if [ -f "cloudfront-setup-config.txt" ]; then
  DISTRIBUTION_ID=$(grep "DISTRIBUTION_ID=" cloudfront-setup-config.txt | cut -d'"' -f2)

  if [ -n "$DISTRIBUTION_ID" ]; then
    echo "To ensure new deployments are served immediately (not cached):"
    echo ""
    echo "1. Copy your CloudFront Distribution ID:"
    echo "   📋 $DISTRIBUTION_ID"
    echo ""
    echo "2. Add it to GitHub Actions:"
    echo "   → Go to: https://github.com/<your-org>/<your-repo>/settings/variables/actions"
    echo "   → Click: 'New repository variable'"
    echo "   → Name: CLOUDFRONT_DISTRIBUTION_ID"
    echo "   → Value: $DISTRIBUTION_ID"
    echo "   → Click: 'Add variable'"
    echo ""
    echo "3. Future CD deployments will automatically invalidate CloudFront cache"
    echo "   → No stale content"
    echo "   → Users see latest version immediately"
    echo ""
    echo "Without this, CloudFront may serve old cached versions for hours!"
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⏰ DNS propagation may take 5-15 minutes globally"
echo ""
echo "If you encounter issues, see:"
echo "  - docs/domain-purchase-cloudfront-setup.md"
echo "  - docs/route53-domain-registration.md"
echo ""
