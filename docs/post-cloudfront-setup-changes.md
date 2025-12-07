# Post-CloudFront Setup: Required Changes

After setting up CloudFront with custom domain, you need to update several components to ensure everything works correctly and infrastructure stays in sync.

## Architecture Change

### Before (Direct ALB Access)
```
User Browser → ALB (HTTPS) → EKS Pods
```

### After (CloudFront + ALB)
```
User Browser → CloudFront (HTTPS) → ALB (HTTP) → EKS Pods
```

**Key Point**: CloudFront now handles HTTPS, so ALB only needs HTTP.

---

## 1. ALB Ingress Configuration Changes

### What to Change

**Remove from ingress**:
- HTTPS listener (CloudFront handles HTTPS)
- SSL redirect (CloudFront does redirect)
- ACM certificate on ALB (certificate is on CloudFront)

**Keep**:
- HTTP listener on port 80
- Session stickiness for Streamlit
- CORS settings
- All routing rules

### Updated Ingress Configuration

File: `deployment/k8s/prod/ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ml-emotion-ingress
  namespace: ml-speech-emotion
  labels:
    app: ml-speech-emotion-recognition
    environment: production
  annotations:
    kubernetes.io/ingress.class: "alb"
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTP
    alb.ingress.kubernetes.io/healthcheck-port: traffic-port
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '30'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
    alb.ingress.kubernetes.io/healthy-threshold-count: '3'
    alb.ingress.kubernetes.io/unhealthy-threshold-count: '3'
    alb.ingress.kubernetes.io/success-codes: '200,302'
    alb.ingress.kubernetes.io/load-balancer-attributes: idle_timeout.timeout_seconds=300
    # HTTP only - CloudFront handles HTTPS
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}]'
    # NO SSL redirect - CloudFront handles this
    # NO certificate-arn - Certificate is on CloudFront
    # Session stickiness for WebSocket support (required for Streamlit)
    alb.ingress.kubernetes.io/target-group-attributes: stickiness.enabled=true,stickiness.lb_cookie.duration_seconds=86400
    # Enable CORS
    alb.ingress.kubernetes.io/enable-cors: 'true'
    alb.ingress.kubernetes.io/cors-allow-origin: '["*"]'
    alb.ingress.kubernetes.io/cors-allow-methods: '["GET", "POST", "PUT", "DELETE", "OPTIONS"]'
    alb.ingress.kubernetes.io/cors-allow-headers: '["DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization,X-Amz-Date,X-Amz-Security-Token,X-Api-Key"]'
    alb.ingress.kubernetes.io/cors-max-age: '86400'
    alb.ingress.kubernetes.io/rate-limit-requests-per-second: '100'
    alb.ingress.kubernetes.io/rate-limit-burst: '200'
spec:
  rules:
  - http:
      paths:
      # Backend API v1 endpoints
      - path: /v1
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      # Backend API v2 endpoints (for inference)
      - path: /v2
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      # Legacy /api prefix support
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      # Backend health check
      - path: /health
        pathType: Exact
        backend:
          service:
            name: backend
            port:
              number: 8000
      # API documentation
      - path: /docs
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      # Prometheus metrics
      - path: /metrics
        pathType: Exact
        backend:
          service:
            name: backend
            port:
              number: 9090
      # Streamlit frontend - must be last (catch-all)
      - path: /
        pathType: Prefix
        backend:
          service:
            name: streamlit
            port:
              number: 8501
```

### Apply Changes

```bash
kubectl apply -f deployment/k8s/prod/ingress.yaml

# Wait for ALB to update (2-5 minutes)
kubectl get ingress ml-emotion-ingress -n ml-speech-emotion -w
```

---

## 2. Terraform Infrastructure Changes

If you're using Terraform to manage infrastructure, add these resources:

### Add CloudFront to Terraform

Create: `deployment/terraform/cloudfront.tf`

```hcl
# ACM Certificate (us-east-1 required for CloudFront)
resource "aws_acm_certificate" "ml_emotion" {
  provider          = aws.us-east-1  # CloudFront requires us-east-1
  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = [
    "www.${var.domain_name}"
  ]

  tags = {
    Name        = "ml-emotion-certificate"
    Project     = "ML-Speech-Emotion-Recognition"
    Environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

# DNS Validation for ACM
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.ml_emotion.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "ml_emotion" {
  provider                = aws.us-east-1
  certificate_arn         = aws_acm_certificate.ml_emotion.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "ml_emotion" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "ML Speech Emotion Recognition - ${var.environment}"
  default_root_object = ""
  price_class         = "PriceClass_100"
  aliases             = [var.domain_name, "www.${var.domain_name}"]

  origin {
    domain_name = data.kubernetes_ingress_v1.ml_emotion.status[0].load_balancer[0].ingress[0].hostname
    origin_id   = "ml-emotion-alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 60
      origin_keepalive_timeout = 60
    }

    connection_attempts = 3
    connection_timeout  = 10
  }

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "ml-emotion-alb"

    # Disable caching for dynamic app
    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"  # CachingDisabled
    origin_request_policy_id = "216adef6-5c7f-47e4-b989-5492eafa07d3"  # AllViewer

    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.ml_emotion.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name        = "ml-emotion-distribution"
    Project     = "ML-Speech-Emotion-Recognition"
    Environment = var.environment
  }

  depends_on = [aws_acm_certificate_validation.ml_emotion]
}

# Route 53 Records
data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

resource "aws_route53_record" "root" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.ml_emotion.domain_name
    zone_id                = aws_cloudfront_distribution.ml_emotion.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.ml_emotion.domain_name
    zone_id                = aws_cloudfront_distribution.ml_emotion.hosted_zone_id
    evaluate_target_health = false
  }
}

# Outputs
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.ml_emotion.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.ml_emotion.domain_name
}

output "website_url" {
  description = "Website URL"
  value       = "https://${var.domain_name}"
}
```

### Update Variables

Add to `deployment/terraform/variables.tf`:

```hcl
variable "domain_name" {
  description = "Custom domain name for the application"
  type        = string
  default     = "ml-emotion.com"
}
```

### Update Provider Configuration

Add `aws.us-east-1` provider for CloudFront:

```hcl
# deployment/terraform/providers.tf
provider "aws" {
  region = var.aws_region
}

# CloudFront requires certificates in us-east-1
provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"
}
```

### Apply Terraform Changes

```bash
cd deployment/terraform

# Initialize new providers
terraform init

# Plan changes
terraform plan -var="domain_name=ml-emotion.com"

# Apply (use existing resources, don't recreate)
terraform import aws_acm_certificate.ml_emotion arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT_ID
terraform import aws_cloudfront_distribution.ml_emotion DISTRIBUTION_ID

# Or let Terraform manage going forward
terraform apply -var="domain_name=ml-emotion.com"
```

---

## 3. CI/CD Pipeline Changes

### Add CloudFront Cache Invalidation

After deploying new code, invalidate CloudFront cache so users see latest version.

#### GitHub Actions Example

File: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Production

on:
  push:
    branches:
      - main

env:
  AWS_REGION: us-east-1
  CLOUDFRONT_DISTRIBUTION_ID: ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Build and Push Docker Images
        run: |
          # Build backend
          docker build -f deployment/docker/backend/Dockerfile -t sagerstack/ml-speech-emotion-backend:latest .
          docker push sagerstack/ml-speech-emotion-backend:latest

          # Build streamlit
          docker build -f deployment/docker/streamlit/Dockerfile -t sagerstack/ml-speech-emotion-streamlit:latest .
          docker push sagerstack/ml-speech-emotion-streamlit:latest

      - name: Update EKS Deployments
        run: |
          aws eks update-kubeconfig --name ml-emotion-cluster --region $AWS_REGION

          kubectl rollout restart deployment/backend -n ml-speech-emotion
          kubectl rollout restart deployment/streamlit -n ml-speech-emotion

          kubectl rollout status deployment/backend -n ml-speech-emotion --timeout=5m
          kubectl rollout status deployment/streamlit -n ml-speech-emotion --timeout=5m

      - name: Invalidate CloudFront Cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"

      - name: Wait for Cache Invalidation
        run: |
          INVALIDATION_ID=$(aws cloudfront list-invalidations \
            --distribution-id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --query 'InvalidationList.Items[0].Id' \
            --output text)

          aws cloudfront wait invalidation-completed \
            --distribution-id ${{ env.CLOUDFRONT_DISTRIBUTION_ID }} \
            --id $INVALIDATION_ID

      - name: Verify Deployment
        run: |
          curl -f https://ml-emotion.com/health || exit 1
```

#### Add GitHub Secret

```bash
# Get your CloudFront distribution ID
DISTRIBUTION_ID=$(cat cloudfront-setup-config.txt | grep DISTRIBUTION_ID | cut -d'"' -f2)

# Add to GitHub Secrets
# Go to: GitHub Repo → Settings → Secrets → Actions
# Name: CLOUDFRONT_DISTRIBUTION_ID
# Value: Your distribution ID
```

#### GitLab CI Example

File: `.gitlab-ci.yml`

```yaml
deploy:
  stage: deploy
  image: amazon/aws-cli
  script:
    - aws eks update-kubeconfig --name ml-emotion-cluster --region $AWS_REGION
    - kubectl rollout restart deployment/backend -n ml-speech-emotion
    - kubectl rollout restart deployment/streamlit -n ml-speech-emotion
    - kubectl rollout status deployment/backend -n ml-speech-emotion --timeout=5m
    - kubectl rollout status deployment/streamlit -n ml-speech-emotion --timeout=5m

    # Invalidate CloudFront cache
    - |
      aws cloudfront create-invalidation \
        --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
        --paths "/*"
  only:
    - main
```

---

## 4. Application Environment Variables

### Update Backend Configuration

File: `deployment/k8s/prod/backend-deployment.yaml`

Add environment variables for custom domain:

```yaml
env:
  # Existing vars...
  - name: ALLOWED_ORIGINS
    value: "https://ml-emotion.com,https://www.ml-emotion.com"
  - name: APP_URL
    value: "https://ml-emotion.com"
```

### Update Frontend Configuration

File: `deployment/k8s/prod/streamlit-deployment.yaml`

```yaml
env:
  # Update backend URL if needed
  - name: ML_APP_BASE_URL
    value: "http://backend:8000"  # Internal communication stays the same
  - name: PUBLIC_URL
    value: "https://ml-emotion.com"
```

### Update ConfigMap

File: `deployment/k8s/prod/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: ml-speech-emotion
data:
  APP_URL: "https://ml-emotion.com"
  ALLOWED_ORIGINS: "https://ml-emotion.com,https://www.ml-emotion.com"
  # Other configs...
```

Apply:
```bash
kubectl apply -f deployment/k8s/prod/configmap.yaml
kubectl rollout restart deployment/backend -n ml-speech-emotion
kubectl rollout restart deployment/streamlit -n ml-speech-emotion
```

---

## 5. Update Documentation and README

### Update README.md

```markdown
# ML Speech Emotion Recognition

🌐 **Live Demo**: https://ml-emotion.com

## Access

- Production: https://ml-emotion.com
- API Docs: https://ml-emotion.com/docs
- Health Check: https://ml-emotion.com/health
```

### Update API Documentation

Update any API docs, Swagger/OpenAPI specs with new base URL:

```yaml
# openapi.yaml
servers:
  - url: https://ml-emotion.com/v2
    description: Production API
```

---

## 6. Monitoring and Alerts

### Add CloudFront Metrics to Monitoring

```bash
# CloudWatch Dashboard
# Add CloudFront metrics:
# - Requests
# - BytesDownloaded
# - 4xxErrorRate
# - 5xxErrorRate
# - TotalErrorRate
```

### Update Health Checks

Update any external monitoring to use new HTTPS endpoints:

```bash
# Pingdom, UptimeRobot, etc.
# Change from: http://ALB-DNS
# To: https://ml-emotion.com
```

---

## 7. Security Updates

### Update CORS Configuration

Backend API should allow requests from custom domain:

```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "https://ml-emotion.com",
    "https://www.ml-emotion.com",
    "http://localhost:8501",  # For local dev
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Update CSP Headers (if applicable)

If you're using Content Security Policy headers:

```python
# Allow resources from CloudFront
csp_policy = "default-src 'self' https://ml-emotion.com https://*.cloudfront.net"
```

---

## Testing Checklist

After making all changes:

### 1. Test HTTP → HTTPS Redirect

```bash
curl -I http://ml-emotion.com
# Should return 301/302 redirect to https://
```

### 2. Test HTTPS Access

```bash
curl -I https://ml-emotion.com
# Should return HTTP/2 200
# via: CloudFront
```

### 3. Test All Features

- [ ] File upload works
- [ ] Live audio recording works
- [ ] streamlit-antd-components load
- [ ] Backend API endpoints work
- [ ] Metrics endpoint accessible

### 4. Test from Different Locations

```bash
# Use online tools to test from different geographic locations
# https://www.whatsmydns.net/
# https://tools.keycdn.com/performance
```

### 5. Test After Deployment

```bash
# Deploy a change
kubectl set image deployment/streamlit streamlit=sagerstack/ml-speech-emotion-streamlit:new-tag -n ml-speech-emotion

# Invalidate cache
aws cloudfront create-invalidation --distribution-id DIST_ID --paths "/*"

# Verify new version is live
curl https://ml-emotion.com
```

---

## Rollback Plan

If something breaks:

### Quick Rollback - Point DNS Back to ALB

```bash
# Get ALB DNS
ALB_DNS=$(kubectl get ingress ml-emotion-ingress -n ml-speech-emotion -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Update Route 53 to point directly to ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "ml-emotion.com",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "'$ALB_DNS'"}]
      }
    }]
  }'
```

### Full Rollback

```bash
# 1. Remove CloudFront distribution
aws cloudfront delete-distribution --id DIST_ID --if-match ETAG

# 2. Revert ingress to HTTPS
kubectl apply -f deployment/k8s/prod/ingress.yaml.backup

# 3. Update DNS back to ALB
```

---

## Summary of Changes

| Component | Change Required | Impact |
|-----------|----------------|---------|
| **ALB Ingress** | Remove HTTPS, keep HTTP only | Medium - requires apply |
| **Terraform** | Add CloudFront resources | High - for IaC consistency |
| **CI/CD** | Add cache invalidation | Medium - improves deployments |
| **Environment Vars** | Update domain URLs | Low - optional |
| **Documentation** | Update URLs | Low - for clarity |
| **Monitoring** | Add CloudFront metrics | Low - recommended |

---

## Quick Deployment Checklist

- [ ] Update and apply ingress.yaml (HTTP only)
- [ ] Add CloudFront to Terraform (if using Terraform)
- [ ] Update CI/CD pipeline with cache invalidation
- [ ] Update environment variables with custom domain
- [ ] Update CORS configuration in backend
- [ ] Update documentation with new URLs
- [ ] Test all functionality
- [ ] Update monitoring dashboards
- [ ] Document rollback procedure

---

## Support

If issues arise:

1. Check CloudFront distribution status
2. Verify DNS resolution
3. Check ALB target group health
4. Review CloudFront logs
5. Test ALB directly to isolate issue

For questions, see:
- `docs/domain-purchase-cloudfront-setup.md`
- `HTTPS-SETUP-CHECKLIST.md`
