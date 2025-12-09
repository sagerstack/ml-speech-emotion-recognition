#!/bin/bash

set -e

# Check if config file exists
if [ ! -f "cloudfront-setup-config.txt" ]; then
  echo "❌ Error: cloudfront-setup-config.txt not found!"
  echo "Please run ./scripts/setup-cloudfront-domain.sh first"
  exit 1
fi

# Load configuration
source cloudfront-setup-config.txt

echo "🚀 Setting up CloudFront Distribution"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Domain:      $DOMAIN_NAME"
echo "Certificate: $CERTIFICATE_ARN"
echo "Origin:      $ALB_DNS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if a CloudFront distribution already exists for this domain
echo "🔍 Checking for existing CloudFront distribution..."
EXISTING_DIST=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Aliases.Items, '$DOMAIN_NAME')].{Id:Id,Domain:DomainName,Origin:Origins.Items[0].DomainName}" \
  --output json 2>/dev/null || echo "[]")

EXISTING_DIST_ID=$(echo "$EXISTING_DIST" | jq -r '.[0].Id // empty')
EXISTING_ORIGIN=$(echo "$EXISTING_DIST" | jq -r '.[0].Origin // empty')

if [ -n "$EXISTING_DIST_ID" ] && [ "$EXISTING_DIST_ID" != "null" ]; then
  echo ""
  echo "📋 Found existing distribution: $EXISTING_DIST_ID"
  echo "   Current origin: $EXISTING_ORIGIN"
  echo "   New origin:     $ALB_DNS"
  echo ""

  if [ "$EXISTING_ORIGIN" = "$ALB_DNS" ]; then
    echo "✅ Origin is already up to date!"
    DISTRIBUTION_ID="$EXISTING_DIST_ID"
    CLOUDFRONT_DOMAIN=$(echo "$EXISTING_DIST" | jq -r '.[0].Domain')
  else
    echo "🔄 Updating CloudFront origin to new ALB..."

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
      echo "❌ Failed to update distribution:"
      echo "$UPDATE_OUTPUT"
      exit 1
    fi

    echo "✅ CloudFront origin updated successfully!"
    DISTRIBUTION_ID="$EXISTING_DIST_ID"
    CLOUDFRONT_DOMAIN=$(echo "$UPDATE_OUTPUT" | jq -r '.Distribution.DomainName')
  fi
else
  echo "📝 No existing distribution found. Creating new one..."

  # Create distribution config
  cat > /tmp/cloudfront-dist-config.json <<EOF
{
  "CallerReference": "ml-emotion-$(date +%s)",
  "Comment": "ML Speech Emotion Recognition - Created $(date)",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "$ALB_DNS",
        "DomainName": "$ALB_DNS",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only",
          "OriginSslProtocols": {
            "Quantity": 1,
            "Items": ["TLSv1.2"]
          },
          "OriginReadTimeout": 60,
          "OriginKeepaliveTimeout": 60
        },
        "ConnectionAttempts": 3,
        "ConnectionTimeout": 10
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "$ALB_DNS",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 7,
      "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad",
    "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3",
    "Compress": true,
    "TrustedSigners": {
      "Enabled": false,
      "Quantity": 0
    },
    "TrustedKeyGroups": {
      "Enabled": false,
      "Quantity": 0
    }
  },
  "Aliases": {
    "Quantity": 2,
    "Items": ["$DOMAIN_NAME", "www.$DOMAIN_NAME"]
  },
  "ViewerCertificate": {
    "ACMCertificateArn": "$CERTIFICATE_ARN",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021",
    "Certificate": "$CERTIFICATE_ARN",
    "CertificateSource": "acm"
  },
  "HttpVersion": "http2and3",
  "IsIPV6Enabled": true,
  "PriceClass": "PriceClass_100"
}
EOF

  echo "📝 Creating CloudFront distribution..."
  DISTRIBUTION_OUTPUT=$(aws cloudfront create-distribution \
    --distribution-config file:///tmp/cloudfront-dist-config.json \
    2>&1)

  if [ $? -ne 0 ]; then
    echo "❌ Failed to create distribution:"
    echo "$DISTRIBUTION_OUTPUT"
    exit 1
  fi

  DISTRIBUTION_ID=$(echo "$DISTRIBUTION_OUTPUT" | jq -r '.Distribution.Id')
  CLOUDFRONT_DOMAIN=$(echo "$DISTRIBUTION_OUTPUT" | jq -r '.Distribution.DomainName')

  echo "✅ CloudFront distribution created!"
fi

echo ""
echo "Distribution ID:     $DISTRIBUTION_ID"
echo "CloudFront Domain:   $CLOUDFRONT_DOMAIN"
echo ""

# Update config file with latest values
# Remove old CloudFront entries if they exist
if [ -f "cloudfront-setup-config.txt" ]; then
  grep -v "^DISTRIBUTION_ID=" cloudfront-setup-config.txt > /tmp/config-clean.txt 2>/dev/null || true
  grep -v "^CLOUDFRONT_DOMAIN=" /tmp/config-clean.txt > cloudfront-setup-config.txt 2>/dev/null || true
fi

# Add current values
cat >> cloudfront-setup-config.txt <<EOF

# CloudFront Details (updated $(date))
DISTRIBUTION_ID="$DISTRIBUTION_ID"
CLOUDFRONT_DOMAIN="$CLOUDFRONT_DOMAIN"
EOF

echo "⏳ Waiting for distribution changes to deploy..."
echo "This takes 2-5 minutes for updates, 5-15 minutes for new distributions."
echo ""

# Optional: Wait for deployment
read -p "Wait for deployment to complete? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Waiting for deployment..."

  SECONDS=0
  while true; do
    STATUS=$(aws cloudfront get-distribution \
      --id $DISTRIBUTION_ID \
      --query 'Distribution.Status' \
      --output text)

    if [ "$STATUS" = "Deployed" ]; then
      echo ""
      echo "✅ Distribution deployed! (took $SECONDS seconds)"
      break
    fi

    printf "\rStatus: $STATUS... elapsed: ${SECONDS}s"
    sleep 10
  done
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CloudFront Distribution Ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Distribution ID:   $DISTRIBUTION_ID"
echo "CloudFront Domain: https://$CLOUDFRONT_DOMAIN"
echo ""
echo "Next step: Point your domain DNS to CloudFront"
echo "Run: ./scripts/setup-dns-to-cloudfront.sh"
echo ""
