# AWS Certificate Manager (ACM) Setup Guide

This guide walks you through creating an SSL/TLS certificate for your Streamlit application to enable HTTPS and fix the live audio recording issue.

## Prerequisites

- AWS Account with appropriate permissions
- A domain name (e.g., `ml-emotion.example.com`)
- Access to domain DNS settings

## Method 1: AWS Console (GUI)

### Step 1: Navigate to ACM

1. Log in to AWS Console
2. Go to **Certificate Manager** service
   - Search for "Certificate Manager" in the AWS services search bar
   - OR navigate to: https://console.aws.amazon.com/acm/home
3. **IMPORTANT**: Select the **same region** as your EKS cluster (check your terraform/kubectl config)
   - For most ALB setups, use `us-east-1` (N. Virginia)

### Step 2: Request a Certificate

1. Click **"Request a certificate"** button
2. Select **"Request a public certificate"**
3. Click **"Next"**

### Step 3: Add Domain Names

1. Enter your fully qualified domain name (FQDN):
   ```
   ml-emotion.example.com
   ```

2. **(Optional)** Add additional names:
   - To cover both www and non-www:
     ```
     ml-emotion.example.com
     www.ml-emotion.example.com
     ```
   - To cover subdomains with wildcard:
     ```
     *.ml-emotion.example.com
     ```

3. Click **"Next"**

### Step 4: Select Validation Method

Choose **DNS validation** (recommended):
- Faster and automated
- No email access required
- Certificate auto-renews if DNS record remains

Alternative: **Email validation**:
- Requires access to admin email addresses
- Manual renewal process

Click **"Next"**

### Step 5: Add Tags (Optional)

Add tags for organization:
```
Key: Project          Value: ML-Speech-Emotion-Recognition
Key: Environment      Value: Production
Key: Service          Value: Streamlit
```

Click **"Next"**

### Step 6: Review and Request

1. Review your configuration
2. Click **"Request"**

### Step 7: Validate Domain Ownership

#### For DNS Validation:

1. After requesting, click **"View certificate"**
2. You'll see a status: **"Pending validation"**
3. Expand the **"Domains"** section
4. For each domain, you'll see:
   - **CNAME name**: `_abc123.ml-emotion.example.com`
   - **CNAME value**: `_xyz456.acm-validations.aws.`

5. Add these CNAME records to your DNS:

   **If using Route 53:**
   - Click **"Create records in Route 53"** button (easiest option)
   - ACM will automatically add the records
   - Wait 5-10 minutes for validation

   **If using other DNS providers (GoDaddy, Namecheap, Cloudflare, etc.):**
   - Log into your DNS provider
   - Create a new CNAME record:
     ```
     Name/Host:  _abc123.ml-emotion.example.com
     Type:       CNAME
     Value:      _xyz456.acm-validations.aws.
     TTL:        300 (5 minutes)
     ```
   - Wait 10-30 minutes for DNS propagation and validation

### Step 8: Wait for Validation

- Certificate status will change from **"Pending validation"** to **"Issued"**
- This can take 5-30 minutes depending on DNS propagation
- You'll receive an email notification when issued

### Step 9: Copy Certificate ARN

1. Once issued, click on the certificate
2. Copy the **Certificate ARN** - it looks like:
   ```
   arn:aws:acm:us-east-1:123456789012:certificate/abcd1234-5678-90ab-cdef-EXAMPLE11111
   ```

---

## Method 2: AWS CLI (Automated)

### Step 1: Request Certificate

```bash
# Request certificate for your domain
aws acm request-certificate \
  --domain-name ml-emotion.example.com \
  --validation-method DNS \
  --subject-alternative-names www.ml-emotion.example.com \
  --tags Key=Project,Value=ML-Speech-Emotion-Recognition Key=Environment,Value=Production \
  --region us-east-1

# Output will be:
# {
#     "CertificateArn": "arn:aws:acm:us-east-1:123456789012:certificate/abcd1234-5678-90ab-cdef-EXAMPLE11111"
# }
```

**Note the Certificate ARN** from the output.

### Step 2: Get Validation Records

```bash
# Replace with your certificate ARN
CERT_ARN="arn:aws:acm:us-east-1:123456789012:certificate/abcd1234-5678-90ab-cdef-EXAMPLE11111"

# Get DNS validation records
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[*].[DomainName,ResourceRecord.Name,ResourceRecord.Value]' \
  --output table
```

### Step 3: Add DNS Records

**If using Route 53:**

```bash
# Get Hosted Zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='example.com.'].Id" \
  --output text)

# Get validation record details
VALIDATION_RECORD=$(aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord' \
  --output json)

RECORD_NAME=$(echo $VALIDATION_RECORD | jq -r '.Name')
RECORD_VALUE=$(echo $VALIDATION_RECORD | jq -r '.Value')

# Create change batch file
cat > /tmp/dns-validation.json <<EOF
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "$RECORD_NAME",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [
          {
            "Value": "$RECORD_VALUE"
          }
        ]
      }
    }
  ]
}
EOF

# Apply DNS record
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/dns-validation.json
```

**If using other DNS providers:**
- Manually add the CNAME records shown in Step 2

### Step 4: Wait for Validation

```bash
# Check certificate status
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --region us-east-1 \
  --query 'Certificate.Status' \
  --output text

# Wait until status is "ISSUED" (can take 5-30 minutes)
# You can run this in a loop:
while true; do
  STATUS=$(aws acm describe-certificate \
    --certificate-arn $CERT_ARN \
    --region us-east-1 \
    --query 'Certificate.Status' \
    --output text)

  echo "Certificate Status: $STATUS"

  if [ "$STATUS" = "ISSUED" ]; then
    echo "✅ Certificate has been issued!"
    break
  fi

  echo "Waiting 30 seconds..."
  sleep 30
done
```

---

## Step 10: Update Kubernetes Ingress

Once you have your Certificate ARN, update the ingress configuration:

```bash
# Edit the ingress file
nano deployment/k8s/prod/ingress.yaml

# Uncomment line 26 and add your certificate ARN:
# alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/abcd1234-5678-90ab-cdef-EXAMPLE11111
```

Or use this command to update it automatically:

```bash
# Replace with your actual certificate ARN
CERT_ARN="arn:aws:acm:us-east-1:123456789012:certificate/abcd1234-5678-90ab-cdef-EXAMPLE11111"

# Update ingress.yaml
sed -i.bak "s|# alb.ingress.kubernetes.io/certificate-arn:.*|alb.ingress.kubernetes.io/certificate-arn: $CERT_ARN|" \
  deployment/k8s/prod/ingress.yaml

# Verify the change
grep "certificate-arn" deployment/k8s/prod/ingress.yaml
```

---

## Troubleshooting

### Issue: Certificate stuck in "Pending validation"

**Causes:**
- DNS records not added correctly
- DNS propagation delay
- Wrong hosted zone used

**Solutions:**
1. Verify DNS records are correct:
   ```bash
   # Check if CNAME exists
   nslookup -type=CNAME _abc123.ml-emotion.example.com
   ```

2. Wait longer (up to 72 hours for some DNS providers)

3. Check ACM is using the right region

### Issue: "Certificate not found" when applying to ALB

**Cause:** Certificate in wrong region

**Solution:** ACM certificates must be in the same region as your ALB/EKS cluster

### Issue: Don't have a domain name

**Options:**
1. **Buy a domain** ($10-15/year):
   - Route 53: AWS's registrar
   - Namecheap, GoDaddy, Google Domains

2. **Use existing AWS resources**:
   - Use the ALB DNS name directly (no custom domain needed)
   - Request cert for: `*.us-east-1.elb.amazonaws.com` (not recommended, won't work for ACM)

3. **For testing only** - Use self-signed certificate:
   ```bash
   # Generate self-signed cert (browsers will show warning)
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout tls.key -out tls.crt \
     -subj "/CN=*.elb.amazonaws.com"

   # Import to ACM
   aws acm import-certificate \
     --certificate fileb://tls.crt \
     --private-key fileb://tls.key \
     --region us-east-1
   ```

---

## Verification

After applying the certificate to your ingress:

```bash
# Check ALB listeners
aws elbv2 describe-listeners \
  --load-balancer-arn $(kubectl get ingress ml-emotion-ingress -n ml-speech-emotion -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' | xargs aws elbv2 describe-load-balancers --query "LoadBalancers[?DNSName=='{}'].LoadBalancerArn" --output text) \
  --query 'Listeners[*].[Port,Protocol,Certificates[0].CertificateArn]' \
  --output table

# Test HTTPS access
curl -I https://your-alb-dns-name.us-east-1.elb.amazonaws.com

# Test if microphone access works
# Open browser to: https://your-alb-dns-name.us-east-1.elb.amazonaws.com
# Try live audio recording
```

---

## Cost

- ACM certificates are **FREE** for public certificates
- You only pay for the resources using the certificate (ALB, CloudFront, etc.)
- Certificate auto-renews before expiration (no manual renewal needed)

---

## Next Steps

After certificate is issued and ingress is updated:

1. Apply the updated ingress:
   ```bash
   kubectl apply -f deployment/k8s/prod/ingress.yaml
   ```

2. Wait 2-5 minutes for ALB to update

3. Test the application:
   - Access via HTTPS
   - Test file upload (should fix AxiosError 400)
   - Test live audio recording (should fix microphone error)

4. Set up DNS CNAME/A record to point your domain to ALB:
   ```
   Type: CNAME
   Name: ml-emotion.example.com
   Value: k8s-mlspeechemotio-abcd1234-12345678.us-east-1.elb.amazonaws.com
   ```
