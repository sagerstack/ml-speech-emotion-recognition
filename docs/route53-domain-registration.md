# AWS Route 53 Domain Registration Guide

## Step-by-Step Domain Registration

### 1. Go to Route 53 Console

Open in browser:
```
https://console.aws.amazon.com/route53/home#DomainRegistration:
```

Or:
1. Log into AWS Console
2. Search for "Route 53" in services
3. Click **"Registered domains"** in left sidebar
4. Click **"Register domain"** button

### 2. Search for Your Domain

**Domain Name Ideas**:
- `ml-emotion.com`
- `mlemotion.com`
- `ml-speech-emotion.com`
- `emotion-ai.com`
- `speechemotion.com`

**Tips**:
- Shorter is better
- Easy to type and remember
- `.com` is most professional ($13/year)
- `.ai` for AI/ML projects ($100/year - expensive!)
- `.io` for tech projects ($39/year)
- `.co` as alternative to .com ($30/year)

Example search:
```
ml-emotion.com
```

### 3. Check Availability

- ✅ **Green checkmark** = Available
- ❌ **Red X** = Taken

If taken, try:
- Different TLD: `ml-emotion.io`, `ml-emotion.co`, `ml-emotion.net`
- Different name: `mlemotion.com`, `emotion-ml.com`
- Add dash: `ml-emotion-ai.com`

### 4. Add to Cart

Click **"Add to cart"** for your chosen domain

**Optional**: Add privacy protection (recommended)
- Hides your personal info from WHOIS lookup
- Usually FREE for Route 53 domains
- Check the box: "Enable privacy protection"

### 5. Configure Contact Information

Fill in:
- **Contact Type**: Person or Company
- **First Name / Last Name**
- **Email**: Use a valid email (important for verification!)
- **Phone Number**: Format: +1.5555555555
- **Address**: Your actual address

**Copy to all contacts**: Check the boxes to use same info for:
- Registrant contact
- Administrative contact
- Technical contact

### 6. Review and Complete Purchase

- Review domain name (double-check spelling!)
- Review contact information
- Check **"I have read and agree to the AWS Domain Name Registration Agreement"**
- Click **"Complete order"**

**Payment**:
- Charged to your AWS account
- For `.com`: ~$13 USD/year
- Auto-renews by default (can disable later)

### 7. Verify Email Address

**Important**: Within 15 minutes, you'll receive an email:

```
Subject: Email Address Verification
From: no-reply@registrar.amazon.com
```

**Action Required**:
1. Open the email
2. Click the verification link
3. You have 3-15 days to verify (varies by TLD)

**If you don't verify**:
- Domain registration may be suspended
- You won't be able to use the domain

### 8. Wait for Registration (10-15 minutes)

**Status progression**:
```
Pending → In Progress → Successful
```

Check status in Route 53 Console:
- **Registered domains** → Your domain
- Status should change to "Successful"

**Automatically created for you**:
- ✅ Route 53 Hosted Zone (DNS)
- ✅ Default DNS records (NS, SOA)
- ✅ Ready for use!

---

## Verify Registration

### Check via AWS Console

1. Go to Route 53 → Registered domains
2. Your domain should show:
   - **Status**: Successful
   - **Auto-renew**: Enabled
   - **Transfer lock**: Enabled

### Check via CLI

```bash
# List your registered domains
aws route53domains list-domains

# Get domain details
aws route53domains get-domain-detail --domain-name ml-emotion.com

# Check hosted zone was created
aws route53 list-hosted-zones
```

### Check DNS is Working

```bash
# Check nameservers
dig NS ml-emotion.com

# Should return Route 53 nameservers like:
# ns-123.awsdns-12.com
# ns-456.awsdns-34.net
# ns-789.awsdns-56.org
# ns-012.awsdns-78.co.uk
```

---

## Cost Breakdown

### Domain Registration (Annual)

| TLD | Price/Year | Best For |
|-----|-----------|----------|
| `.com` | $13 | Professional, general purpose |
| `.net` | $13 | Networks, tech |
| `.org` | $13 | Organizations |
| `.io` | $39 | Tech startups, developers |
| `.ai` | $100 | AI/ML projects (expensive!) |
| `.co` | $30 | Alternative to .com |
| `.dev` | $13 | Developer projects |
| `.app` | $19 | Web applications |

### Additional Route 53 Costs

**Hosted Zone**: $0.50/month ($6/year)
- Created automatically with domain
- Includes DNS management

**DNS Queries**: $0.40 per million queries
- First 1 billion queries/month for Route 53 Alias records = FREE
- Standard queries: $0.40 per million

**Example monthly cost for low-traffic site**:
```
Domain: $13/year = $1.08/month
Hosted Zone: $0.50/month
DNS Queries: ~$0.01/month (for 25,000 queries)
─────────────────────────────
Total: ~$1.59/month
```

---

## What Happens Next?

After registration is complete:

1. ✅ **Domain is yours** for 1 year (auto-renews)
2. ✅ **Hosted Zone created** automatically
3. ✅ **DNS ready** to use
4. ✅ **Privacy protection** enabled (if selected)

**Now you can**:
- Create SSL certificate in ACM
- Set up CloudFront
- Point domain to your app

---

## Troubleshooting

### Issue: Email verification not received

**Solutions**:
- Check spam folder
- Verify email address in contact info
- Resend verification email:
  ```bash
  aws route53domains resend-contact-reachability-email --domain-name ml-emotion.com
  ```

### Issue: Registration failed

**Common causes**:
- Invalid contact information
- Payment method declined
- Domain already taken (someone bought it between search and checkout)

**Solution**:
- Check AWS billing dashboard
- Try different domain name
- Contact AWS support

### Issue: Can't see hosted zone

**Check**:
```bash
# List hosted zones
aws route53 list-hosted-zones

# If missing, create manually:
aws route53 create-hosted-zone \
  --name ml-emotion.com \
  --caller-reference $(date +%s)
```

---

## Domain Management

### Turn Off Auto-Renew (if needed)

```bash
# Via CLI
aws route53domains disable-domain-auto-renew --domain-name ml-emotion.com

# Via Console
Route 53 → Registered domains → Your domain → Disable auto-renew
```

### Enable Transfer Lock (Recommended)

```bash
# Prevents unauthorized transfers
aws route53domains enable-domain-transfer-lock --domain-name ml-emotion.com
```

### View Domain Expiration

```bash
aws route53domains get-domain-detail \
  --domain-name ml-emotion.com \
  --query 'ExpirationDate' \
  --output text
```

---

## Next Steps

Once domain is registered (Status: Successful):

1. **Run the setup script**:
   ```bash
   cd /Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition
   ./scripts/setup-cloudfront-domain.sh ml-emotion.com
   ```

2. **Create CloudFront distribution** (manual or automated)

3. **Point domain to CloudFront** (automated with Route 53!)

4. **Test your HTTPS site**

See: `docs/domain-purchase-cloudfront-setup.md` for complete CloudFront setup.

---

## Quick Reference

### Useful Commands

```bash
# List registered domains
aws route53domains list-domains

# Get domain details
aws route53domains get-domain-detail --domain-name ml-emotion.com

# List hosted zones
aws route53 list-hosted-zones

# Check domain availability
aws route53domains check-domain-availability --domain-name test.com

# Update contact info
aws route53domains update-domain-contact --domain-name ml-emotion.com --admin-contact file://contact.json
```

### Important Links

- Route 53 Console: https://console.aws.amazon.com/route53
- Domain Pricing: https://aws.amazon.com/route53/pricing/
- Domain Registration Docs: https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-register.html

---

## Support

If you encounter issues:
- AWS Support Console: https://console.aws.amazon.com/support
- Route 53 Forum: https://repost.aws/tags/TA4IvCeWI1TE-6F3p3qC9ocQ/amazon-route-53
- AWS re:Post: https://repost.aws/
