# Complete Guide: Buy Domain + CloudFront + HTTPS Setup

This guide covers everything from buying a domain to setting up CloudFront with HTTPS.

## Part 1: Where to Buy a Domain

### Best Domain Registrars (Ranked)

#### 1. **AWS Route 53** ⭐ Recommended for AWS Projects
- **Price**: $12-13/year for `.com`, cheaper for other TLDs
- **Pros**:
  - ✅ Seamless AWS integration
  - ✅ Auto-configures DNS in Route 53
  - ✅ One-click DNS setup for ACM validation
  - ✅ No separate login needed
  - ✅ Pay with same AWS account
- **Cons**:
  - Slightly more expensive than some competitors
  - No free privacy protection on some TLDs

**How to buy**:
```bash
# Check if domain is available
aws route53domains check-domain-availability \
  --domain-name ml-emotion.com \
  --region us-east-1

# Register domain (CLI)
aws route53domains register-domain \
  --domain-name ml-emotion.com \
  --duration-in-years 1 \
  --admin-contact file://contact.json \
  --registrant-contact file://contact.json \
  --tech-contact file://contact.json \
  --privacy-protection \
  --auto-renew \
  --region us-east-1
```

**Or use AWS Console** (easier):
1. Go to Route 53 → Registered domains → Register domain
2. Search for your domain
3. Add to cart and checkout

#### 2. **Namecheap** ⭐ Best Value
- **Price**: $5.98-8.88/year for `.com`, $0.98/year for `.xyz`
- **Pros**:
  - ✅ Cheapest prices
  - ✅ Free WHOIS privacy protection
  - ✅ Easy to use interface
  - ✅ Good customer support
  - ✅ Frequent promotions
- **Cons**:
  - Need to manage DNS separately (or point to Route 53)

**Website**: https://www.namecheap.com

**Popular cheap TLDs**:
- `.xyz` - $0.98/year (first year)
- `.online` - $0.99/year
- `.site` - $0.99/year
- `.tech` - $2.88/year
- `.com` - $8.88/year

#### 3. **Cloudflare Registrar** ⭐ Best for Advanced Users
- **Price**: At-cost pricing (usually $8-10/year for `.com`)
- **Pros**:
  - ✅ No markup - pay what Cloudflare pays
  - ✅ Free WHOIS privacy
  - ✅ Free DNS (fastest DNS globally)
  - ✅ Free CDN (alternative to CloudFront)
  - ✅ Free SSL certificates
- **Cons**:
  - Must transfer domain from another registrar (can't register new)
  - Requires Cloudflare account

**Website**: https://www.cloudflare.com/products/registrar/

#### 4. **Google Domains** (Now Squarespace)
- **Price**: $12/year for `.com`
- **Pros**:
  - ✅ Free privacy protection
  - ✅ Simple interface
  - ✅ Reliable
- **Cons**:
  - Recently acquired by Squarespace (uncertain future)
  - More expensive

**Website**: https://domains.google (redirects to Squarespace)

#### 5. **Porkbun** - Rising Star
- **Price**: $6.59/year for `.com`
- **Pros**:
  - ✅ Competitive pricing
  - ✅ Free WHOIS privacy
  - ✅ Good reputation
  - ✅ Modern interface
- **Cons**:
  - Smaller company

**Website**: https://porkbun.com

### Free Subdomain Options (No Cost)

If you want to test without spending money:

#### 1. **FreeDNS (afraid.org)** ⭐ Best Free Option
- **Price**: FREE forever
- **Domains**: Choose from 100+ free domains
- **Example**: `ml-emotion.mooo.com`, `ml-emotion.chickenkiller.com`

**Setup**:
1. Go to https://freedns.afraid.org
2. Sign up (free)
3. Dashboard → Subdomains → Add
4. Choose a domain from dropdown
5. Point to your CloudFront or ALB URL

#### 2. **DuckDNS**
- **Price**: FREE
- **Domain**: `ml-emotion.duckdns.org`
- **Website**: https://www.duckdns.org

#### 3. **No-IP**
- **Price**: FREE (must confirm every 30 days)
- **Domain**: `ml-emotion.ddns.net`
- **Website**: https://www.noip.com

---

## Part 2: Complete Setup (CloudFront + Custom Domain)

### Architecture

```
User Browser (HTTPS)
    ↓
https://ml-emotion.yourdomain.com (Custom Domain)
    ↓
CloudFront Distribution (HTTPS, CDN)
    ↓
Application Load Balancer (HTTP)
    ↓
EKS Cluster → Streamlit + Backend
```

### Prerequisites

- Domain name (purchased or free subdomain)
- AWS Account
- EKS cluster with ALB running

---

## Step-by-Step Setup

### Step 1: Set Up Route 53 Hosted Zone (If using Route 53 for DNS)

**If you bought domain from Route 53**: Skip this step, already done automatically.

**If you bought domain elsewhere** (Namecheap, etc.):

```bash
# Create hosted zone
aws route53 create-hosted-zone \
  --name ml-emotion.com \
  --caller-reference $(date +%s)

# Note the 4 nameservers from output
# Example output:
# ns-123.awsdns-12.com
# ns-456.awsdns-34.net
# ns-789.awsdns-56.org
# ns-012.awsdns-78.co.uk
```

**Then update nameservers at your domain registrar**:

**For Namecheap**:
1. Log into Namecheap
2. Go to Domain List → Manage
3. Find "Nameservers" section
4. Select "Custom DNS"
5. Enter the 4 Route 53 nameservers
6. Save (takes 24-48 hours to propagate)

**For other registrars**: Similar process in DNS settings

---

### Step 2: Request ACM Certificate for CloudFront

**IMPORTANT**: CloudFront requires certificates from **us-east-1** region ONLY!

#### Option A: AWS Console

1. Go to **Certificate Manager** in **us-east-1** region:
   ```
   https://console.aws.amazon.com/acm/home?region=us-east-1
   ```

2. Click **"Request a certificate"**

3. Choose **"Request a public certificate"**

4. Enter domain names:
   ```
   ml-emotion.com
   www.ml-emotion.com
   ```
   (Add both to support www and non-www)

5. Select **"DNS validation"**

6. Click **"Request"**

7. Click **"View certificate"**

8. **Add CNAME records for validation**:

   **If using Route 53**:
   - Click **"Create records in Route 53"** button
   - ACM will automatically add validation records
   - Wait 5-10 minutes

   **If using other DNS**:
   - Manually add the CNAME records shown
   - Wait 10-30 minutes for validation

9. Wait for status to change to **"Issued"**

10. **Copy the Certificate ARN**

#### Option B: AWS CLI

```bash
# Request certificate (must be in us-east-1 for CloudFront!)
CERT_ARN=$(aws acm request-certificate \
  --domain-name ml-emotion.com \
  --subject-alternative-names www.ml-emotion.com \
  --validation-method DNS \
  --region us-east-1 \
  --query 'CertificateArn' \
  --output text)

echo "Certificate ARN: $CERT_ARN"

# Get validation CNAME records
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[*].[DomainName,ResourceRecord.Name,ResourceRecord.Value]' \
  --output table

# If using Route 53, add records automatically:
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='ml-emotion.com.'].Id" \
  --output text | cut -d'/' -f3)

# Get validation details
VALIDATION_RECORD=$(aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord')

RECORD_NAME=$(echo $VALIDATION_RECORD | jq -r '.Name')
RECORD_VALUE=$(echo $VALIDATION_RECORD | jq -r '.Value')

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

# Wait for validation (can take 5-30 minutes)
aws acm wait certificate-validated \
  --certificate-arn $CERT_ARN \
  --region us-east-1

echo "✅ Certificate validated and issued!"
```

---

### Step 3: Create CloudFront Distribution

#### Option A: AWS Console

1. Go to **CloudFront** → Create Distribution

2. **Origin Settings**:
   - **Origin Domain**: Your ALB DNS (paste from kubectl):
     ```bash
     kubectl get ingress ml-emotion-ingress -n ml-speech-emotion -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
     # Example: k8s-mlspeech-mlemotio-0ee21d53c8-632773106.us-east-1.elb.amazonaws.com
     ```
   - **Protocol**: HTTP only
   - **HTTP Port**: 80
   - **Name**: `ml-emotion-alb`

3. **Default Cache Behavior**:
   - **Viewer Protocol Policy**: Redirect HTTP to HTTPS ✅
   - **Allowed HTTP Methods**: GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE
   - **Cache Policy**: CachingDisabled (important for dynamic apps!)
   - **Origin Request Policy**: AllViewer
   - **Response Headers Policy**: None

4. **Settings**:
   - **Alternate Domain Names (CNAMEs)**: Add your domains:
     ```
     ml-emotion.com
     www.ml-emotion.com
     ```
   - **Custom SSL Certificate**: Select your certificate from dropdown
   - **Security Policy**: TLSv1.2_2021 (recommended)
   - **Supported HTTP Versions**: HTTP/2 and HTTP/3
   - **Default Root Object**: Leave empty (Streamlit handles routing)
   - **Standard Logging**: Off (or configure if needed)

5. Click **"Create Distribution"**

6. **Wait 5-15 minutes** for deployment (Status changes to "Enabled")

7. **Copy CloudFront Domain**: `d1234567890abc.cloudfront.net`

#### Option B: AWS CLI

```bash
# Get ALB DNS
ALB_DNS=$(kubectl get ingress ml-emotion-ingress -n ml-speech-emotion -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Your certificate ARN from Step 2
CERT_ARN="arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID"

# Your custom domain
DOMAIN_NAME="ml-emotion.com"

# Create distribution config
cat > /tmp/cloudfront-config.json <<EOF
{
  "CallerReference": "ml-emotion-$(date +%s)",
  "Comment": "ML Speech Emotion Recognition",
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
          }
        }
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
    "MinTTL": 0,
    "DefaultTTL": 0,
    "MaxTTL": 0
  },
  "Aliases": {
    "Quantity": 2,
    "Items": ["$DOMAIN_NAME", "www.$DOMAIN_NAME"]
  },
  "ViewerCertificate": {
    "ACMCertificateArn": "$CERT_ARN",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  },
  "HttpVersion": "http2and3",
  "IsIPV6Enabled": true,
  "PriceClass": "PriceClass_100"
}
EOF

# Create distribution
DISTRIBUTION_ID=$(aws cloudfront create-distribution \
  --distribution-config file:///tmp/cloudfront-config.json \
  --query 'Distribution.Id' \
  --output text)

echo "CloudFront Distribution ID: $DISTRIBUTION_ID"

# Get CloudFront domain
CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
  --id $DISTRIBUTION_ID \
  --query 'Distribution.DomainName' \
  --output text)

echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"
echo "Waiting for deployment... (this takes 5-15 minutes)"

# Wait for deployment
aws cloudfront wait distribution-deployed --id $DISTRIBUTION_ID

echo "✅ CloudFront distribution deployed!"
```

---

### Step 4: Point Your Domain to CloudFront

Now we need to create DNS records pointing your domain to CloudFront.

#### Option A: AWS Console (Route 53)

1. Go to **Route 53** → Hosted Zones
2. Click on your domain (e.g., `ml-emotion.com`)
3. Click **"Create Record"**

**Record 1 - Root domain**:
- **Record name**: Leave empty (for root domain)
- **Record type**: A
- **Alias**: Toggle ON ✅
- **Route traffic to**:
  - Choose: "Alias to CloudFront distribution"
  - Select your CloudFront distribution from dropdown
- **Routing policy**: Simple routing
- Click **"Create records"**

**Record 2 - www subdomain**:
- **Record name**: `www`
- **Record type**: A
- **Alias**: Toggle ON ✅
- **Route traffic to**:
  - Choose: "Alias to CloudFront distribution"
  - Select your CloudFront distribution
- Click **"Create records"**

#### Option B: AWS CLI (Route 53)

```bash
# Get hosted zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='ml-emotion.com.'].Id" \
  --output text | cut -d'/' -f3)

# Get CloudFront distribution domain
CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution \
  --id $DISTRIBUTION_ID \
  --query 'Distribution.DomainName' \
  --output text)

# Get CloudFront Hosted Zone ID (always this for CloudFront)
CLOUDFRONT_ZONE_ID="Z2FDTNDATAQYW2"

# Create DNS records
cat > /tmp/dns-records.json <<EOF
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "ml-emotion.com",
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
        "Name": "www.ml-emotion.com",
        "Type": "A",
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

# Apply DNS records
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/dns-records.json

echo "✅ DNS records created!"
```

#### Option C: Other DNS Providers (Namecheap, Cloudflare, etc.)

**If using Namecheap/GoDaddy/etc**:

1. Log into your domain registrar
2. Go to DNS Management / Advanced DNS
3. Add these records:

**Record 1**:
```
Type: CNAME
Host: @  (or leave empty for root)
Value: d1234567890abc.cloudfront.net
TTL: Automatic (or 300)
```

**Record 2**:
```
Type: CNAME
Host: www
Value: d1234567890abc.cloudfront.net
TTL: Automatic
```

**Note**: Some registrars don't allow CNAME on root domain. In that case:
- Use ALIAS record (if supported)
- Or use A record pointing to CloudFront IP (not recommended, IPs change)
- Or use subdomain only: `app.ml-emotion.com`

---

### Step 5: Wait for DNS Propagation

```bash
# Check DNS propagation (may take 5 minutes to 48 hours)
# Usually works within 5-15 minutes

# Check root domain
dig ml-emotion.com

# Check www subdomain
dig www.ml-emotion.com

# Or use online tool
open https://www.whatsmydns.net/#A/ml-emotion.com
```

---

### Step 6: Test Your Setup

```bash
# Test HTTPS access
curl -I https://ml-emotion.com
curl -I https://www.ml-emotion.com

# Should return:
# HTTP/2 200
# via: 1.1 xxx.cloudfront.net (CloudFront)
# x-cache: Miss from cloudfront

# Open in browser
open https://ml-emotion.com
```

**Test all features**:
1. ✅ Page loads over HTTPS
2. ✅ streamlit-antd-components load correctly
3. ✅ File upload works (no AxiosError 400)
4. ✅ Live audio recording works (microphone access)

---

## Cost Summary

### One-Time Costs
- Domain registration: $0.98 - $13/year (or FREE with subdomain)
- ACM Certificate: FREE

### Monthly Costs

**CloudFront** (after free tier):
- Data transfer: $0.085/GB (first 10TB)
- HTTPS requests: $0.0075 per 10,000
- **Estimated for demo app**: $0-5/month

**Route 53** (if used):
- Hosted zone: $0.50/month
- DNS queries: $0.40 per million queries
- **Estimated**: ~$0.50/month

**Total monthly cost**: $0.50 - $5.50/month

### Free Tier (12 months)
- 1 TB data transfer out
- 10M HTTP/HTTPS requests
- 2M CloudFront function invocations

---

## Troubleshooting

### Issue: "Certificate doesn't match domain"

**Cause**: Certificate not validated or wrong region

**Solution**:
- Ensure certificate is in `us-east-1` (CloudFront requirement)
- Verify certificate status is "Issued"
- Check domain names match exactly

### Issue: CloudFront returns 502/504 errors

**Cause**: ALB not responding

**Solution**:
```bash
# Test ALB directly
curl -I http://k8s-mlspeech-mlemotio-0ee21d53c8-632773106.us-east-1.elb.amazonaws.com

# Check backend health
kubectl get pods -n ml-speech-emotion
kubectl logs -n ml-speech-emotion deployment/streamlit
```

### Issue: DNS not resolving

**Cause**: DNS propagation delay or wrong nameservers

**Solution**:
```bash
# Check nameservers
dig NS ml-emotion.com

# Verify Route 53 nameservers match
aws route53 get-hosted-zone --id $HOSTED_ZONE_ID
```

### Issue: "Too many redirects"

**Cause**: Redirect loop

**Solution**:
- Check CloudFront origin protocol policy is "HTTP only"
- Remove SSL redirect from ALB ingress (CloudFront handles HTTPS)

---

## Automation Script (All-in-One)

Save this as `scripts/setup-cloudfront-domain.sh`:

```bash
#!/bin/bash

set -e

# Configuration
DOMAIN_NAME="${1:-ml-emotion.com}"
AWS_REGION="us-east-1"
NAMESPACE="ml-speech-emotion"
INGRESS_NAME="ml-emotion-ingress"

echo "🚀 Setting up CloudFront + Custom Domain for: $DOMAIN_NAME"

# Step 1: Get ALB DNS
echo "📡 Getting ALB DNS..."
ALB_DNS=$(kubectl get ingress $INGRESS_NAME -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "ALB DNS: $ALB_DNS"

# Step 2: Request ACM Certificate
echo "🔐 Requesting ACM certificate..."
CERT_ARN=$(aws acm request-certificate \
  --domain-name "$DOMAIN_NAME" \
  --subject-alternative-names "www.$DOMAIN_NAME" \
  --validation-method DNS \
  --region $AWS_REGION \
  --query 'CertificateArn' \
  --output text)

echo "Certificate ARN: $CERT_ARN"

# Step 3: Display DNS validation records
echo "📋 Add these DNS records for validation:"
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region $AWS_REGION \
  --query 'Certificate.DomainValidationOptions[*].[DomainName,ResourceRecord.Name,ResourceRecord.Value]' \
  --output table

echo ""
echo "⏳ Waiting for certificate validation..."
echo "Please add the DNS records above and press ENTER to continue..."
read

# Wait for validation
aws acm wait certificate-validated \
  --certificate-arn $CERT_ARN \
  --region $AWS_REGION

echo "✅ Certificate validated!"

# Save configuration
cat > /tmp/cloudfront-setup-info.txt <<EOF
Domain: $DOMAIN_NAME
Certificate ARN: $CERT_ARN
ALB DNS: $ALB_DNS
EOF

echo "✅ Setup information saved to /tmp/cloudfront-setup-info.txt"
echo ""
echo "Next steps:"
echo "1. Create CloudFront distribution with these details"
echo "2. Point your domain DNS to CloudFront"
echo ""
echo "Full guide: docs/domain-purchase-cloudfront-setup.md"
```

Make it executable:
```bash
chmod +x scripts/setup-cloudfront-domain.sh
./scripts/setup-cloudfront-domain.sh ml-emotion.com
```

---

## Quick Reference

### Command Cheat Sheet

```bash
# Check certificate status
aws acm describe-certificate --certificate-arn $CERT_ARN --region us-east-1

# List CloudFront distributions
aws cloudfront list-distributions --query 'DistributionList.Items[*].[Id,DomainName,Status]' --output table

# Invalidate CloudFront cache (after deployments)
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"

# Check DNS propagation
dig ml-emotion.com
nslookup ml-emotion.com

# Test HTTPS
curl -I https://ml-emotion.com
```

---

## Next Steps

After setup is complete:

1. **Test thoroughly**:
   - File upload
   - Live recording
   - All pages/features

2. **Set up monitoring**:
   - CloudWatch for CloudFront metrics
   - Set up alarms for errors

3. **Optimize**:
   - Configure cache policies for static assets
   - Enable compression

4. **Security**:
   - Set up WAF rules (optional)
   - Configure rate limiting
