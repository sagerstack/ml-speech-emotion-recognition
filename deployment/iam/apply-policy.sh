#!/bin/bash
#
# Apply IAM Policy for CloudFront HTTPS Setup
# This script creates and attaches the necessary IAM policy to ml-ser-deploy user
#

set -e

ACCOUNT_ID="303440520181"
USER_NAME="ml-ser-deploy"
POLICY_NAME="ML-SER-CloudFront-HTTPS-Setup"
POLICY_FILE="deployment/iam/cloudfront-https-setup-policy.json"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  IAM Policy Setup for HTTPS CloudFront Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will create and attach IAM policy: $POLICY_NAME"
echo "To IAM user: $USER_NAME"
echo ""

# Check if policy file exists
if [ ! -f "$POLICY_FILE" ]; then
  echo "❌ Error: Policy file not found: $POLICY_FILE"
  exit 1
fi

# Check if policy already exists
EXISTING_POLICY_ARN=$(aws iam list-policies \
  --query "Policies[?PolicyName=='$POLICY_NAME'].Arn" \
  --output text 2>/dev/null || echo "")

if [ -n "$EXISTING_POLICY_ARN" ]; then
  echo "⚠️  Policy already exists: $EXISTING_POLICY_ARN"
  echo ""
  read -p "Update existing policy? (y/n): " -n 1 -r
  echo

  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📝 Creating new policy version..."

    aws iam create-policy-version \
      --policy-arn "$EXISTING_POLICY_ARN" \
      --policy-document file://$POLICY_FILE \
      --set-as-default

    echo "✅ Policy updated successfully"
    POLICY_ARN="$EXISTING_POLICY_ARN"
  else
    echo "Skipping policy update"
    POLICY_ARN="$EXISTING_POLICY_ARN"
  fi
else
  echo "📝 Creating new IAM policy..."

  POLICY_ARN=$(aws iam create-policy \
    --policy-name "$POLICY_NAME" \
    --policy-document file://$POLICY_FILE \
    --description "Permissions for ML Speech Emotion Recognition HTTPS setup with CloudFront" \
    --query 'Policy.Arn' \
    --output text)

  echo "✅ Policy created: $POLICY_ARN"
fi

echo ""

# Check if policy is already attached to user
ATTACHED=$(aws iam list-attached-user-policies \
  --user-name "$USER_NAME" \
  --query "AttachedPolicies[?PolicyArn=='$POLICY_ARN'].PolicyName" \
  --output text 2>/dev/null || echo "")

if [ -n "$ATTACHED" ]; then
  echo "✅ Policy already attached to user: $USER_NAME"
else
  echo "📎 Attaching policy to user: $USER_NAME..."

  aws iam attach-user-policy \
    --user-name "$USER_NAME" \
    --policy-arn "$POLICY_ARN"

  echo "✅ Policy attached successfully"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Policies attached to user $USER_NAME:"
aws iam list-attached-user-policies --user-name "$USER_NAME" --output table

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Testing Permissions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Switching to ml-ser-deploy profile for testing..."
export AWS_PROFILE=ml-ser-deploy

echo ""
echo "Testing ACM permissions..."
if aws acm list-certificates --region us-east-1 >/dev/null 2>&1; then
  echo "✅ ACM permissions working"
else
  echo "❌ ACM permissions failed"
fi

echo ""
echo "Testing Route 53 permissions..."
if aws route53 list-hosted-zones >/dev/null 2>&1; then
  echo "✅ Route 53 permissions working"
else
  echo "❌ Route 53 permissions failed"
fi

echo ""
echo "Testing CloudFront permissions..."
if aws cloudfront list-distributions >/dev/null 2>&1; then
  echo "✅ CloudFront permissions working"
else
  echo "❌ CloudFront permissions failed"
fi

echo ""
echo "Testing EKS permissions..."
if aws eks list-clusters --region us-east-1 >/dev/null 2>&1; then
  echo "✅ EKS permissions working"
else
  echo "❌ EKS permissions failed"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Policy ARN: $POLICY_ARN"
echo ""
echo "Next steps:"
echo "  1. Ensure AWS_PROFILE is set: export AWS_PROFILE=ml-ser-deploy"
echo "  2. Run HTTPS setup: ./scripts/complete-https-setup.sh sagerstack.com"
echo ""
