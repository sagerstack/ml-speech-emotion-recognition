# IAM Policy Setup for HTTPS CloudFront Deployment

This guide shows how to attach the necessary IAM permissions to the `ml-ser-deploy` user for running the HTTPS setup scripts.

## Quick Apply (Recommended)

### Option 1: Attach Policy via AWS CLI

```bash
# Set your AWS account ID
ACCOUNT_ID="303440520181"
USER_NAME="ml-ser-deploy"

# Create the IAM policy
aws iam create-policy \
  --policy-name ML-SER-CloudFront-HTTPS-Setup \
  --policy-document file://deployment/iam/cloudfront-https-setup-policy.json \
  --description "Permissions for ML Speech Emotion Recognition HTTPS setup with CloudFront"

# Attach policy to user
aws iam attach-user-policy \
  --user-name $USER_NAME \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/ML-SER-CloudFront-HTTPS-Setup
```

### Option 2: Attach Policy via AWS Console

1. **Go to IAM Console**:
   ```
   https://console.aws.amazon.com/iam/home#/policies
   ```

2. **Create Policy**:
   - Click **"Create policy"**
   - Switch to **JSON** tab
   - Copy the contents of `deployment/iam/cloudfront-https-setup-policy.json`
   - Paste into the JSON editor
   - Click **"Next"**

3. **Name the Policy**:
   - **Name**: `ML-SER-CloudFront-HTTPS-Setup`
   - **Description**: `Permissions for ML Speech Emotion Recognition HTTPS setup with CloudFront`
   - Click **"Create policy"**

4. **Attach to User**:
   - Go to **IAM → Users → ml-ser-deploy**
   - Click **"Add permissions"** → **"Attach policies directly"**
   - Search for: `ML-SER-CloudFront-HTTPS-Setup`
   - Select it and click **"Next"**
   - Click **"Add permissions"**

---

## What Permissions Are Included

### 1. ACM (Certificate Manager)
```json
- acm:RequestCertificate       // Create SSL certificate
- acm:DescribeCertificate       // Check certificate status
- acm:ListCertificates          // List existing certificates
- acm:AddTagsToCertificate      // Tag certificates for organization
```
**Why needed**: To create and validate SSL/TLS certificates for HTTPS.

### 2. Route 53 (DNS Management)
```json
- route53:ListHostedZones           // Find your domain's hosted zone
- route53:GetHostedZone             // Get hosted zone details
- route53:ListResourceRecordSets    // List existing DNS records
- route53:ChangeResourceRecordSets  // Add DNS validation records
- route53:GetChange                 // Check if DNS changes applied
```
**Why needed**: To add DNS validation records for certificate and point domain to CloudFront.

### 3. Route 53 Domains
```json
- route53domains:GetDomainDetail    // Check domain status
- route53domains:ListDomains        // List registered domains
```
**Why needed**: To verify domain is registered and ready.

### 4. CloudFront (CDN)
```json
- cloudfront:CreateDistribution     // Create CloudFront distribution
- cloudfront:GetDistribution        // Get distribution details
- cloudfront:UpdateDistribution     // Update distribution settings
- cloudfront:ListDistributions      // List distributions
- cloudfront:CreateInvalidation     // Invalidate cache after deployments
- cloudfront:TagResource            // Tag distributions
```
**Why needed**: To create and manage CloudFront distribution.

### 5. EKS (Kubernetes)
```json
- eks:DescribeCluster              // Get cluster information
- eks:ListClusters                 // List available clusters
```
**Why needed**: To get ALB DNS from EKS cluster (used as CloudFront origin).

---

## Verify Policy is Attached

```bash
# Check policies attached to user
aws iam list-attached-user-policies --user-name ml-ser-deploy

# Should show:
# {
#     "AttachedPolicies": [
#         {
#             "PolicyName": "ML-SER-CloudFront-HTTPS-Setup",
#             "PolicyArn": "arn:aws:iam::303440520181:policy/ML-SER-CloudFront-HTTPS-Setup"
#         }
#     ]
# }
```

---

## Test Permissions

After attaching the policy:

```bash
# Switch to ml-ser-deploy profile
export AWS_PROFILE=ml-ser-deploy

# Test ACM permissions
aws acm list-certificates --region us-east-1

# Test Route 53 permissions
aws route53 list-hosted-zones

# Test CloudFront permissions
aws cloudfront list-distributions

# Test EKS permissions
aws eks list-clusters --region us-east-1
```

All commands should succeed without `AccessDeniedException`.

---

## Minimal Policy (Least Privilege Alternative)

If you want even more restrictive permissions, use this minimal version:

File: `deployment/iam/cloudfront-https-setup-policy-minimal.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ACMCertificateOperations",
      "Effect": "Allow",
      "Action": [
        "acm:RequestCertificate",
        "acm:DescribeCertificate"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    },
    {
      "Sid": "Route53DNSOperations",
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones",
        "route53:ChangeResourceRecordSets",
        "route53:GetChange"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudFrontOperations",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateDistribution",
        "cloudfront:GetDistribution",
        "cloudfront:CreateInvalidation"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EKSReadOnly",
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster"
      ],
      "Resource": "arn:aws:eks:*:303440520181:cluster/*"
    }
  ]
}
```

This removes:
- List operations (if you already know resource ARNs)
- Tagging operations
- Update operations
- Logging operations

---

## Troubleshooting

### Error: AccessDeniedException

**Problem**: User still doesn't have permission for a specific action.

**Solution**:
1. Check which action is failing from error message
2. Verify policy is attached: `aws iam list-attached-user-policies --user-name ml-ser-deploy`
3. Check policy has the required action
4. Wait 5-10 seconds for IAM changes to propagate

### Error: Policy already exists

**Problem**: Policy name already exists.

**Solutions**:

**Option A - Update existing policy**:
```bash
# Get existing policy ARN
POLICY_ARN=$(aws iam list-policies --query "Policies[?PolicyName=='ML-SER-CloudFront-HTTPS-Setup'].Arn" --output text)

# Create new version
aws iam create-policy-version \
  --policy-arn $POLICY_ARN \
  --policy-document file://deployment/iam/cloudfront-https-setup-policy.json \
  --set-as-default
```

**Option B - Delete and recreate**:
```bash
# Detach from user first
aws iam detach-user-policy \
  --user-name ml-ser-deploy \
  --policy-arn arn:aws:iam::303440520181:policy/ML-SER-CloudFront-HTTPS-Setup

# Delete policy
aws iam delete-policy \
  --policy-arn arn:aws:iam::303440520181:policy/ML-SER-CloudFront-HTTPS-Setup

# Recreate (run commands from Option 1 above)
```

### Error: Cannot find hosted zone

**Problem**: Script can't find Route 53 hosted zone for your domain.

**Check**:
```bash
aws route53 list-hosted-zones

# Should show your domain (sagerstack.com)
```

If missing, the domain registration may not be complete or hosted zone not created.

---

## Security Best Practices

### 1. Use IAM Roles Instead of Users (Production)

For production, create an IAM role and assume it:

```bash
# Create role with this policy
# Then assume role when needed
aws sts assume-role --role-arn arn:aws:iam::303440520181:role/ML-SER-Deployer --role-session-name setup-https
```

### 2. Add Resource Restrictions (Advanced)

Restrict to specific hosted zones:

```json
{
  "Sid": "Route53DNSRecordManagement",
  "Effect": "Allow",
  "Action": [
    "route53:ChangeResourceRecordSets"
  ],
  "Resource": "arn:aws:route53:::hostedzone/Z1234567890ABC"
}
```

### 3. Time-Based Access

Add condition to only allow during business hours:

```json
"Condition": {
  "DateGreaterThan": {"aws:CurrentTime": "2025-01-01T00:00:00Z"},
  "DateLessThan": {"aws:CurrentTime": "2025-12-31T23:59:59Z"}
}
```

### 4. MFA Required (Recommended)

Require MFA for sensitive operations:

```json
"Condition": {
  "Bool": {
    "aws:MultiFactorAuthPresent": "true"
  }
}
```

---

## Next Steps

After attaching the policy:

1. **Verify permissions**:
   ```bash
   export AWS_PROFILE=ml-ser-deploy
   aws sts get-caller-identity
   aws acm list-certificates --region us-east-1
   ```

2. **Run the setup script**:
   ```bash
   ./scripts/complete-https-setup.sh sagerstack.com
   ```

3. **Monitor for any permission errors**:
   - If you see `AccessDeniedException`, note the action
   - Add that action to the policy
   - Update the policy version

---

## Policy Maintenance

### Update Policy

When you need to add more permissions:

1. Edit `deployment/iam/cloudfront-https-setup-policy.json`
2. Create new policy version:
   ```bash
   POLICY_ARN="arn:aws:iam::303440520181:policy/ML-SER-CloudFront-HTTPS-Setup"

   aws iam create-policy-version \
     --policy-arn $POLICY_ARN \
     --policy-document file://deployment/iam/cloudfront-https-setup-policy.json \
     --set-as-default
   ```

### Remove Policy (Cleanup)

When no longer needed:

```bash
# Detach from user
aws iam detach-user-policy \
  --user-name ml-ser-deploy \
  --policy-arn arn:aws:iam::303440520181:policy/ML-SER-CloudFront-HTTPS-Setup

# Delete all versions
aws iam delete-policy \
  --policy-arn arn:aws:iam::303440520181:policy/ML-SER-CloudFront-HTTPS-Setup
```

---

## Summary

The policy grants permissions for:
- ✅ Creating ACM certificates (us-east-1 only)
- ✅ Managing Route 53 DNS records
- ✅ Creating CloudFront distributions
- ✅ Accessing EKS cluster info
- ✅ Invalidating CloudFront cache

**Total permissions**: 30+ actions across 5 AWS services

**Estimated setup time**: 5 minutes via Console, 2 minutes via CLI

After applying, the `ml-ser-deploy` user will have all necessary permissions to run the HTTPS setup scripts successfully.
