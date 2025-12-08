#!/bin/bash

set -e

# Configuration
DOMAIN_NAME="${1}"
AUTO_ADD_DNS="${2:-true}"  # Default to true if not specified
AWS_REGION="us-east-1"
NAMESPACE="ml-speech-emotion"
INGRESS_NAME="ml-emotion-ingress"

if [ -z "$DOMAIN_NAME" ]; then
  echo "Usage: $0 <domain-name> [auto-add-dns]"
  echo "Example: $0 ml-emotion.com"
  echo "         $0 ml-emotion.com false  # Skip automatic DNS record creation"
  exit 1
fi

echo "🚀 Setting up CloudFront + Custom Domain for: $DOMAIN_NAME"
echo ""

# Step 1: Get ALB DNS
echo "📡 Step 1: Getting ALB DNS..."
ALB_DNS=$(kubectl get ingress $INGRESS_NAME -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "✅ ALB DNS: $ALB_DNS"
echo ""

# Step 2: Check for existing certificate or request new one
echo "🔐 Step 2: Checking for existing certificate..."

# Check if certificate already exists for this domain
EXISTING_CERT=$(aws acm list-certificates --region $AWS_REGION \
  --query "CertificateSummaryList[?DomainName=='$DOMAIN_NAME'].CertificateArn" \
  --output text)

if [ -n "$EXISTING_CERT" ]; then
  echo "✅ Found existing certificate: $EXISTING_CERT"
  CERT_ARN="$EXISTING_CERT"

  # Check certificate status
  CERT_STATUS=$(aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --region $AWS_REGION \
    --query 'Certificate.Status' \
    --output text)

  echo "   Status: $CERT_STATUS"

  if [ "$CERT_STATUS" = "ISSUED" ]; then
    echo "   ✅ Certificate already validated!"
    echo ""
    # Skip to saving config
    SKIP_VALIDATION=true
  elif [ "$CERT_STATUS" = "PENDING_VALIDATION" ]; then
    echo "   ⏳ Certificate pending validation - will add/check DNS records"
    echo ""
    SKIP_VALIDATION=false
  else
    echo "   ❌ Certificate status: $CERT_STATUS"
    echo "   Please delete the certificate and try again, or check AWS Console"
    exit 1
  fi
else
  echo "📝 Requesting new ACM certificate..."
  CERT_ARN=$(aws acm request-certificate \
    --domain-name "$DOMAIN_NAME" \
    --subject-alternative-names "www.$DOMAIN_NAME" \
    --validation-method DNS \
    --region $AWS_REGION \
    --tags Key=Project,Value=ML-Speech-Emotion Key=Environment,Value=Production \
    --query 'CertificateArn' \
    --output text)

  echo "✅ Certificate ARN: $CERT_ARN"
  echo ""
  SKIP_VALIDATION=false
fi

# Step 3: Display DNS validation records
echo "📋 Step 3: DNS Validation Records"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Add these CNAME records to your DNS:"
echo ""
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region $AWS_REGION \
  --query 'Certificate.DomainValidationOptions[*].[DomainName,ResourceRecord.Name,ResourceRecord.Value]' \
  --output table

echo ""
echo "If using Route 53, run this command to add records automatically:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if Route 53 hosted zone exists
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='${DOMAIN_NAME}.'].Id" \
  --output text 2>/dev/null | cut -d'/' -f3 || echo "")

if [ -n "$HOSTED_ZONE_ID" ]; then
  echo "✅ Found Route 53 hosted zone: $HOSTED_ZONE_ID"
  echo ""

  if [ "$AUTO_ADD_DNS" = "true" ]; then
    echo "🔄 Automatically adding DNS validation records..."

    # Get validation record details for both domains
    VALIDATION_OPTIONS=$(aws acm describe-certificate \
      --certificate-arn $CERT_ARN \
      --region $AWS_REGION \
      --query 'Certificate.DomainValidationOptions[*].ResourceRecord' \
      --output json)

    # Extract unique validation records (both domains may use same record)
    UNIQUE_RECORDS=$(echo "$VALIDATION_OPTIONS" | jq -r 'unique_by(.Name) | .[] | "\(.Name)|\(.Value)"')

    # Add each validation record
    echo "$UNIQUE_RECORDS" | while IFS='|' read -r RECORD_NAME RECORD_VALUE; do
      if [ -n "$RECORD_NAME" ] && [ -n "$RECORD_VALUE" ]; then
        echo "   Adding record: $RECORD_NAME"

        cat > /tmp/acm-validation-${RECORD_NAME}.json <<EOF
{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "$RECORD_NAME",
      "Type": "CNAME",
      "TTL": 300,
      "ResourceRecords": [{"Value": "$RECORD_VALUE"}]
    }
  }]
}
EOF

        aws route53 change-resource-record-sets \
          --hosted-zone-id $HOSTED_ZONE_ID \
          --change-batch file:///tmp/acm-validation-${RECORD_NAME}.json
      fi
    done

    echo "✅ DNS validation records added to Route 53"
  else
    read -p "Add DNS validation records automatically? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      # Get validation record details
      VALIDATION_DATA=$(aws acm describe-certificate \
        --certificate-arn $CERT_ARN \
        --region $AWS_REGION \
        --query 'Certificate.DomainValidationOptions[0].ResourceRecord' \
        --output json)

      RECORD_NAME=$(echo $VALIDATION_DATA | jq -r '.Name')
      RECORD_VALUE=$(echo $VALIDATION_DATA | jq -r '.Value')

      # Create DNS validation record
      cat > /tmp/acm-validation.json <<EOF
{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "$RECORD_NAME",
      "Type": "CNAME",
      "TTL": 300,
      "ResourceRecords": [{"Value": "$RECORD_VALUE"}]
    }
  }]
}
EOF

      aws route53 change-resource-record-sets \
        --hosted-zone-id $HOSTED_ZONE_ID \
        --change-batch file:///tmp/acm-validation.json

      echo "✅ DNS validation records added to Route 53"
    fi
  fi
else
  echo "⚠️  No Route 53 hosted zone found for $DOMAIN_NAME"
  echo "Please add the DNS records manually at your DNS provider"
fi

if [ "$SKIP_VALIDATION" = "false" ]; then
  echo ""
  echo "⏳ Step 4: Waiting for certificate validation..."
  echo "This can take 5-30 minutes..."
  echo ""

  # Wait for validation with progress indicator
  SECONDS=0
  while true; do
    STATUS=$(aws acm describe-certificate \
      --certificate-arn $CERT_ARN \
      --region $AWS_REGION \
      --query 'Certificate.Status' \
      --output text)

    if [ "$STATUS" = "ISSUED" ]; then
      echo ""
      echo "✅ Certificate validated and issued! (took $SECONDS seconds)"
      break
    elif [ "$STATUS" = "FAILED" ]; then
      echo ""
      echo "❌ Certificate validation failed!"
      exit 1
    fi

    printf "\rStatus: $STATUS... elapsed: ${SECONDS}s"
    sleep 10
  done
else
  echo ""
  echo "⏭️  Step 4: Skipped (certificate already validated)"
fi

echo ""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup Complete! Here's your configuration:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Domain:          $DOMAIN_NAME"
echo "Certificate ARN: $CERT_ARN"
echo "ALB DNS:         $ALB_DNS"
echo ""

# Save configuration
cat > cloudfront-setup-config.txt <<EOF
# CloudFront + Custom Domain Setup Configuration
# Generated: $(date)

DOMAIN_NAME="$DOMAIN_NAME"
CERTIFICATE_ARN="$CERT_ARN"
ALB_DNS="$ALB_DNS"
AWS_REGION="$AWS_REGION"

# Next Steps:
# 1. Create CloudFront distribution (see below)
# 2. Point domain DNS to CloudFront
# 3. Test HTTPS access

# CloudFront Distribution Settings:
# - Origin Domain: $ALB_DNS
# - Alternate Domain Names (CNAMEs): $DOMAIN_NAME, www.$DOMAIN_NAME
# - Custom SSL Certificate: $CERT_ARN
# - Viewer Protocol Policy: Redirect HTTP to HTTPS
# - Cache Policy: CachingDisabled
# - Origin Request Policy: AllViewer
EOF

echo "Configuration saved to: cloudfront-setup-config.txt"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Create CloudFront distribution:"
echo "   → Go to: https://console.aws.amazon.com/cloudfront"
echo "   → Create Distribution with settings from cloudfront-setup-config.txt"
echo ""
echo "2. Or use AWS CLI to create distribution automatically:"
echo "   → Run: ./scripts/create-cloudfront-distribution.sh"
echo ""
echo "3. See full guide: docs/domain-purchase-cloudfront-setup.md"
echo ""
