# CloudFront HTTPS Setup (Without Custom Domain)

This guide shows how to get HTTPS working without owning a domain name by using AWS CloudFront.

## How It Works

CloudFront provides a free HTTPS-enabled domain like:
```
https://d1234567890abc.cloudfront.net
```

This domain automatically has SSL/TLS enabled, so your app will work over HTTPS.

## Setup Steps

### 1. Create CloudFront Distribution

```bash
# Get your ALB DNS name
ALB_DNS=$(kubectl get ingress ml-emotion-ingress -n ml-speech-emotion -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "ALB DNS: $ALB_DNS"

# Create CloudFront distribution
aws cloudfront create-distribution \
  --origin-domain-name $ALB_DNS \
  --default-root-object "/" \
  --query 'Distribution.DomainName' \
  --output text

# This returns your CloudFront domain: d1234567890abc.cloudfront.net
```

Or use AWS Console:

1. Go to **CloudFront** in AWS Console
2. Click **"Create Distribution"**
3. Under **Origin Settings**:
   - **Origin Domain**: Your ALB URL (without http://)
     ```
     k8s-mlspeech-mlemotio-0ee21d53c8-632773106.us-east-1.elb.amazonaws.com
     ```
   - **Protocol**: HTTP only (or Match viewer)
   - **HTTP Port**: 80

4. Under **Default Cache Behavior Settings**:
   - **Viewer Protocol Policy**: Redirect HTTP to HTTPS
   - **Allowed HTTP Methods**: GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE
   - **Cache Policy**: CachingDisabled (for dynamic app)
   - **Origin Request Policy**: AllViewer

5. Under **Settings**:
   - **Price Class**: Use All Edge Locations (or choose based on your needs)
   - **Alternate Domain Names (CNAMEs)**: Leave empty (no custom domain)

6. Click **"Create Distribution"**

7. Wait 5-15 minutes for deployment (Status: "Deployed")

8. Copy your CloudFront domain: `https://d1234567890abc.cloudfront.net`

### 2. Test Your Application

```bash
# Access via CloudFront (HTTPS enabled)
curl -I https://d1234567890abc.cloudfront.net

# Open in browser
open https://d1234567890abc.cloudfront.net
```

Now test:
- ✅ File upload should work
- ✅ Live audio recording should work (HTTPS enabled!)
- ✅ streamlit-antd-components should load

## Pros & Cons

### Pros ✅
- **FREE** (CloudFront free tier: 1TB data transfer/month)
- **HTTPS enabled** automatically
- **No domain name needed**
- **Better performance** (CDN caching at edge locations)
- **DDoS protection** included

### Cons ❌
- Ugly URL: `d1234567890abc.cloudfront.net`
- Can't customize the domain
- Extra hop (slight latency, but usually faster due to CDN)

## Cost Estimate

**CloudFront Free Tier (12 months):**
- 1 TB data transfer out per month
- 10,000,000 HTTP/HTTPS requests per month
- 2,000,000 CloudFront Function invocations per month

**After Free Tier:**
- $0.085 per GB data transfer (first 10TB/month)
- $0.0075 per 10,000 HTTPS requests

For a low-traffic demo app: **~$0-5/month**

## Alternative: Quick Fix for Testing

If you just want to test locally with HTTPS:

### Option A: ngrok (Easiest)

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Get your ALB URL
kubectl port-forward -n ml-speech-emotion service/streamlit 8501:8501

# In another terminal, expose with HTTPS
ngrok http 8501

# ngrok provides an HTTPS URL:
# https://abc123.ngrok.io
```

**Pros**: Instant HTTPS, free tier available
**Cons**: Temporary URL (changes on restart), not for production

### Option B: Cloudflare Tunnel (Free Forever)

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create ml-emotion-app

# Run tunnel
cloudflared tunnel --url http://localhost:8501
```

Gives you a free HTTPS subdomain: `https://abc-123.trycloudflare.com`

## Recommendation

For your use case (testing/demo without custom domain):

**Best option: CloudFront**
- Professional solution
- Free
- Reliable
- Production-ready

**Second option: Free subdomain (afraid.org)**
- Nicer URL
- Free forever
- Custom name

**Avoid**: Running without HTTPS - microphone won't work
