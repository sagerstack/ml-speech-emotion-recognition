#!/bin/bash

set -e

# Check if config file exists
if [ ! -f "cloudfront-setup-config.txt" ]; then
  echo "❌ Error: cloudfront-setup-config.txt not found!"
  echo "Please run previous setup scripts first"
  exit 1
fi

# Load configuration
source cloudfront-setup-config.txt

# Check required variables
if [ -z "$DOMAIN_NAME" ] || [ -z "$CLOUDFRONT_DOMAIN" ]; then
  echo "❌ Error: Missing configuration"
  echo "Please ensure CloudFront distribution is created"
  exit 1
fi

echo "🌐 Setting up DNS for Custom Domain"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Domain:              $DOMAIN_NAME"
echo "CloudFront Domain:   $CLOUDFRONT_DOMAIN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Get Route 53 hosted zone ID
echo "📡 Finding Route 53 hosted zone..."
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='${DOMAIN_NAME}.'].Id" \
  --output text | cut -d'/' -f3)

if [ -z "$HOSTED_ZONE_ID" ]; then
  echo "❌ Error: No Route 53 hosted zone found for $DOMAIN_NAME"
  echo "Please create a hosted zone first"
  exit 1
fi

echo "✅ Found hosted zone: $HOSTED_ZONE_ID"
echo ""

# CloudFront Hosted Zone ID (this is always the same for all CloudFront distributions)
CLOUDFRONT_ZONE_ID="Z2FDTNDATAQYW2"

echo "📝 Creating DNS records..."

# Create DNS records for root domain and www subdomain
cat > /tmp/dns-cloudfront-records.json <<EOF
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$DOMAIN_NAME",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "$CLOUDFRONT_ZONE_ID",
          "DNSName": "$CLOUDFRONT_DOMAIN",
          "EvaluateTargetHealth": false
        }
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "www.$DOMAIN_NAME",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "$CLOUDFRONT_ZONE_ID",
          "DNSName": "$CLOUDFRONT_DOMAIN",
          "EvaluateTargetHealth": false
        }
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$DOMAIN_NAME",
        "Type": "AAAA",
        "AliasTarget": {
          "HostedZoneId": "$CLOUDFRONT_ZONE_ID",
          "DNSName": "$CLOUDFRONT_DOMAIN",
          "EvaluateTargetHealth": false
        }
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "www.$DOMAIN_NAME",
        "Type": "AAAA",
        "AliasTarget": {
          "HostedZoneId": "$CLOUDFRONT_ZONE_ID",
          "DNSName": "$CLOUDFRONT_DOMAIN",
          "EvaluateTargetHealth": false
        }
      }
    }
  ]
}
EOF

# Apply DNS changes
CHANGE_ID=$(aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/dns-cloudfront-records.json \
  --query 'ChangeInfo.Id' \
  --output text)

echo "✅ DNS records created!"
echo "Change ID: $CHANGE_ID"
echo ""

echo "⏳ Waiting for DNS propagation..."
aws route53 wait resource-record-sets-changed --id "$CHANGE_ID"

echo "✅ DNS records are live!"
echo ""

# Test DNS resolution
echo "🔍 Testing DNS resolution..."
echo ""

sleep 5  # Give it a few seconds

echo "Testing $DOMAIN_NAME:"
dig +short $DOMAIN_NAME A | head -1
dig +short $DOMAIN_NAME AAAA | head -1

echo ""
echo "Testing www.$DOMAIN_NAME:"
dig +short www.$DOMAIN_NAME A | head -1
dig +short www.$DOMAIN_NAME AAAA | head -1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DNS Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Your domain is now pointing to CloudFront!"
echo ""
echo "🌐 Test your site:"
echo "   https://$DOMAIN_NAME"
echo "   https://www.$DOMAIN_NAME"
echo ""
echo "⚠️  Note: It may take 5-15 minutes for DNS to fully propagate globally"
echo ""
echo "📋 Next steps:"
echo "   1. Test HTTPS access: curl -I https://$DOMAIN_NAME"
echo "   2. Test file upload in the app"
echo "   3. Test live audio recording"
echo ""
