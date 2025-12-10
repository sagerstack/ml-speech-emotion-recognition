# HTTPS Setup Checklist - Route 53 + CloudFront

Follow these steps to get your ML Speech Emotion Recognition app running on HTTPS with a custom domain.

## ✅ Prerequisites

- [ ] AWS Account with payment method configured
- [ ] EKS cluster deployed and running
- [ ] ALB (Application Load Balancer) created via Kubernetes Ingress
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] kubectl configured to access your EKS cluster
- [ ] ~$15-20 budget ($13/year for domain + hosting costs)

---

## Step 1: Register Domain in Route 53 (10 minutes)

### Option A: AWS Console (Recommended - Visual)

1. **Open Route 53**:
   ```bash
   open "https://console.aws.amazon.com/route53/home#DomainRegistration:"
   ```

2. Click **"Register domain"**

3. **Search for domain**:
   - Example ideas:
     - `ml-emotion.com`
     - `mlemotion.com`
     - `emotion-ai.com`
     - `speechemotion.com`

4. **Add to cart** (~$13/year for `.com`)

5. **Fill contact information**
   - Use a valid email address!
   - ✅ Check "Enable privacy protection"

6. **Complete purchase**

7. **VERIFY EMAIL** (within 15 minutes):
   - Check inbox for "Email Address Verification"
   - Click the verification link
   - ⚠️ Must verify or domain will be suspended!

8. **Wait for registration** (10-15 minutes)
   - Status: Pending → In Progress → **Successful**
   - Check: Route 53 → Registered domains

- [ ] Domain registered
- [ ] Email verified
- [ ] Registration status: **Successful**
- [ ] My domain name: `____________________`

### Option B: AWS CLI (Alternative)

```bash
# Check availability
aws route53domains check-domain-availability \
  --domain-name ml-emotion.com \
  --region us-east-1

# If available, register via console (easier for first-time)
```

---

## Step 2: Verify Domain is Ready

```bash
# Check domain status
aws route53domains list-domains

# Should show Status: Successful
```

**Verify**:
- [ ] Domain status is "Successful"
- [ ] Hosted zone auto-created in Route 53
- [ ] Email verified

---

## Step 3: Run Complete HTTPS Setup (Automated!)

This single script does everything:
- ✅ Creates ACM SSL certificate
- ✅ Validates certificate via DNS (automatic with Route 53!)
- ✅ Creates CloudFront distribution
- ✅ Configures DNS records
- ✅ Enables HTTPS

```bash
cd /Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition

# Replace with YOUR domain
./scripts/complete-https-setup.sh ml-emotion.com
```

**The script will**:

1. Get your ALB DNS from Kubernetes
2. Request ACM certificate
3. Add DNS validation records to Route 53 (automatic!)
4. Wait for certificate validation (~5-10 minutes)
5. Create CloudFront distribution
6. Point your domain DNS to CloudFront
7. Test DNS propagation

**Time**: 15-20 minutes total (mostly waiting)

- [ ] Script completed successfully
- [ ] Certificate validated
- [ ] CloudFront distribution deployed
- [ ] DNS records created
- [ ] Configuration saved to `cloudfront-setup-config.txt`

---

## Step 4: Test Your HTTPS Site (5 minutes)

### Test 1: HTTPS Access

```bash
# Test root domain
curl -I https://ml-emotion.com

# Should return:
# HTTP/2 200
# via: 1.1 xxx.cloudfront.net (CloudFront)
```

### Test 2: www subdomain

```bash
curl -I https://www.ml-emotion.com

# Should also return HTTP/2 200
```

### Test 3: Browser Access

```bash
# Open in browser
open https://ml-emotion.com
```

**Expected**:
- ✅ Green padlock (secure HTTPS)
- ✅ No certificate warnings
- ✅ Page loads correctly

### Test 4: All Three Issues Fixed!

Open your app and test:

1. **streamlit-antd-components**:
   - [ ] No yellow banner about component loading
   - [ ] Tabs and UI components work correctly

2. **File Upload**:
   - [ ] Upload an audio file
   - [ ] No AxiosError 400
   - [ ] File processes successfully

3. **Live Audio Recording**:
   - [ ] Click "Live Recording" option
   - [ ] Allow microphone access
   - [ ] Record audio successfully
   - [ ] No "An error has occurred" message

---

## Troubleshooting

### Issue: DNS not resolving

**Wait 5-15 minutes** for DNS propagation

```bash
# Check DNS
dig ml-emotion.com
nslookup ml-emotion.com

# Online checker
open "https://www.whatsmydns.net/#A/ml-emotion.com"
```

### Issue: Certificate error in browser

**Cause**: Certificate not fully propagated to CloudFront

**Wait**: 5-10 more minutes and refresh

### Issue: 502 Bad Gateway

**Cause**: ALB not responding

```bash
# Check backend health
kubectl get pods -n ml-speech-emotion
kubectl logs -n ml-speech-emotion deployment/streamlit
kubectl logs -n ml-speech-emotion deployment/backend

# Test ALB directly
curl -I http://YOUR-ALB-DNS.elb.amazonaws.com
```

### Issue: "Too many redirects"

**Check**: CloudFront origin protocol should be "HTTP only", not "HTTPS only"

### Issue: Microphone still not working

**Verify**:
1. Accessing via `https://` (not `http://`)
2. Browser shows green padlock
3. No certificate warnings
4. Using Chrome/Firefox/Safari (not Internet Explorer)

---

## Cost Summary

### One-Time / Annual Costs

- **Domain Registration**: $13/year (`.com`)
- **ACM Certificate**: FREE

### Monthly Costs

- **Route 53 Hosted Zone**: $0.50/month
- **DNS Queries**: $0.01/month (low traffic)
- **CloudFront**: $0-5/month (within free tier for first 12 months)

**Total**: ~$1.59/month (~$19/year including domain)

### Free Tier (First 12 Months)

- 1 TB CloudFront data transfer
- 10M HTTP/HTTPS requests
- 2M CloudFront Function invocations

For a demo/low-traffic app, you'll likely stay within free tier!

---

## Next Steps (After Setup Complete)

### 1. Update Application to Use Custom Domain

Update any hardcoded URLs in your application:

```bash
# If you have environment variables pointing to ALB
# Update them to use your custom domain
```

### 2. Set Up Monitoring

```bash
# CloudWatch for CloudFront
# Set up alarms for errors
```

### 3. Configure Auto-Renewal

**Domain**: Auto-renews by default in Route 53 ✅

**Certificate**: Auto-renews automatically via ACM ✅

Nothing to do! Both renew automatically.

### 4. Optional: Invalidate CloudFront Cache After Deployments

```bash
# After deploying new app version
DISTRIBUTION_ID=$(cat cloudfront-setup-config.txt | grep DISTRIBUTION_ID | cut -d'"' -f2)

aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"
```

### 5. Optional: Set Up WAF (Web Application Firewall)

For production, consider adding WAF rules for security.

---

## Quick Reference

### Important Files

- `cloudfront-setup-config.txt` - All your setup details
- `docs/route53-domain-registration.md` - Domain registration guide
- `docs/domain-purchase-cloudfront-setup.md` - Complete CloudFront guide
- `docs/acm-certificate-setup.md` - Certificate management

### Useful Commands

```bash
# Check domain status
aws route53domains list-domains

# Check certificate status
aws acm list-certificates --region us-east-1

# List CloudFront distributions
aws cloudfront list-distributions

# Check DNS records
aws route53 list-resource-record-sets \
  --hosted-zone-id $(aws route53 list-hosted-zones \
    --query "HostedZones[?Name=='ml-emotion.com.'].Id" \
    --output text | cut -d'/' -f3)

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

### Support Resources

- **AWS Documentation**: https://docs.aws.amazon.com/route53/
- **CloudFront Docs**: https://docs.aws.amazon.com/cloudfront/
- **ACM Docs**: https://docs.aws.amazon.com/acm/
- **AWS Support**: https://console.aws.amazon.com/support

---

## Summary

After completing this checklist:

✅ Custom domain (e.g., `ml-emotion.com`)
✅ HTTPS enabled with valid SSL certificate
✅ CloudFront CDN for better performance
✅ All three app issues fixed:
   - streamlit-antd-components loading
   - File upload working
   - Live audio recording working

**Access your app**:
- 🌐 https://ml-emotion.com
- 🌐 https://www.ml-emotion.com

🎉 **Congratulations! Your app is production-ready with HTTPS!**
