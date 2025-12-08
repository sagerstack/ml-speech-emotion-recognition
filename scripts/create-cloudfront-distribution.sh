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

echo "🚀 Creating CloudFront Distribution"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Domain:      $DOMAIN_NAME"
echo "Certificate: $CERTIFICATE_ARN"
echo "Origin:      $ALB_DNS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

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
        "Id": "ml-emotion-alb",
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
    "TargetOriginId": "ml-emotion-alb",
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
echo ""
echo "Distribution ID:     $DISTRIBUTION_ID"
echo "CloudFront Domain:   $CLOUDFRONT_DOMAIN"
echo ""

# Save to config
cat >> cloudfront-setup-config.txt <<EOF

# CloudFront Details (added $(date))
DISTRIBUTION_ID="$DISTRIBUTION_ID"
CLOUDFRONT_DOMAIN="$CLOUDFRONT_DOMAIN"
EOF

echo "⏳ Waiting for distribution to deploy..."
echo "This takes 5-15 minutes. You can continue to the next step."
echo ""

# Optional: Wait for deployment
read -p "Wait for deployment to complete? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Waiting for deployment (this may take up to 15 minutes)..."

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
