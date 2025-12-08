# HTTPS + Authentication + Grafana Integration Plan

## Overview

This plan adds:
1. **HTTPS** via AWS Certificate Manager (ACM) + ALB
2. **Authentication** via AWS Cognito (ALB-integrated OAuth2)
3. **Grafana access** via `/grafana` route behind same authentication

---

## Architecture

```
                                    ┌─────────────────────────────────┐
                                    │   Route53 DNS (Optional)        │
                                    │   ml-emotion.yourdomain.com     │
                                    └──────────────┬──────────────────┘
                                                   │
                                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     AWS Application Load Balancer (ALB)                   │
│  - HTTPS Listener (443) with ACM Certificate                             │
│  - Cognito Authentication (OAuth2)                                        │
│  - Redirect HTTP (80) → HTTPS (443)                                       │
├──────────────────────────────────────────────────────────────────────────┤
│  Routing Rules:                                                           │
│    /              → Streamlit (ml-speech-emotion namespace)               │
│    /api/*         → Backend FastAPI (ml-speech-emotion namespace)         │
│    /grafana/*     → Grafana (monitoring namespace)                        │
│    /prometheus/*  → Prometheus (monitoring namespace) - Optional          │
└──────────────────┬───────────────────────────────────────┬───────────────┘
                   │                                        │
                   ▼                                        ▼
       ┌───────────────────────┐             ┌─────────────────────────┐
       │  K8s Services          │             │  K8s Services           │
       │  (ml-speech-emotion)   │             │  (monitoring)           │
       ├───────────────────────┤             ├─────────────────────────┤
       │  - backend:8000        │             │  - grafana:3000         │
       │  - streamlit:8501      │             │  - prometheus:9090      │
       └───────────────────────┘             └─────────────────────────┘
```

---

## Implementation Plan

### Phase 1: HTTPS Setup (ACM + ALB)

#### Step 1.1: Create ACM Certificate

**Option A: Use Route53 Domain**
```bash
# If you have a domain in Route53
aws acm request-certificate \
  --domain-name ml-emotion.yourdomain.com \
  --validation-method DNS \
  --region us-east-1

# Get certificate ARN
CERT_ARN=$(aws acm list-certificates \
  --query 'CertificateSummaryList[?DomainName==`ml-emotion.yourdomain.com`].CertificateArn' \
  --output text)
```

**Option B: Use ALB DNS (No custom domain needed)**
```bash
# Request certificate for ALB DNS name
# You'll need to validate via email or DNS
aws acm request-certificate \
  --domain-name "*.us-east-1.elb.amazonaws.com" \
  --validation-method DNS \
  --region us-east-1
```

**Option C: Self-Signed Certificate (Dev/Testing Only)**
```bash
# Not recommended for production
# ALB doesn't support self-signed certs - use ACM
```

#### Step 1.2: Update Ingress for HTTPS

Update `deployment/k8s/prod/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ml-emotion-ingress
  namespace: ml-speech-emotion
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip

    # HTTPS Configuration
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01

    # Redirect HTTP to HTTPS
    alb.ingress.kubernetes.io/ssl-redirect: "443"

    # Health check
    alb.ingress.kubernetes.io/healthcheck-path: /health
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: "30"
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: "5"
    alb.ingress.kubernetes.io/healthy-threshold-count: "2"
    alb.ingress.kubernetes.io/unhealthy-threshold-count: "3"

    # Tags
    alb.ingress.kubernetes.io/tags: Environment=production,Project=ml-speech-emotion

spec:
  rules:
    - http:
        paths:
          # Streamlit frontend
          - path: /
            pathType: Prefix
            backend:
              service:
                name: streamlit
                port:
                  number: 8501

          # Backend API
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000

          # Grafana (monitoring namespace)
          - path: /grafana
            pathType: Prefix
            backend:
              service:
                name: grafana
                port:
                  number: 3000

          # Prometheus (optional)
          - path: /prometheus
            pathType: Prefix
            backend:
                service:
                  name: prometheus
                  port:
                    number: 9090
```

**Issue with cross-namespace routing**: The above won't work directly because Grafana is in `monitoring` namespace but Ingress is in `ml-speech-emotion`.

**Solution**: Use ExternalName service or update Ingress in monitoring namespace.

---

### Phase 2: AWS Cognito Authentication

#### Step 2.1: Create Cognito User Pool (Terraform)

Add to `deployment/terraform/cognito.tf`:

```hcl
# Cognito User Pool for authentication
resource "aws_cognito_user_pool" "ml_emotion_users" {
  name = "${local.project_name}-${local.environment}-users"

  # Password policy
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = false
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Auto-verify email
  auto_verified_attributes = ["email"]

  # User attributes
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = false
  }

  tags = local.tags
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "ml_emotion_auth" {
  domain       = "${local.project_name}-${local.environment}-auth"
  user_pool_id = aws_cognito_user_pool.ml_emotion_users.id
}

# Cognito User Pool Client (for ALB)
resource "aws_cognito_user_pool_client" "alb_client" {
  name         = "${local.project_name}-${local.environment}-alb"
  user_pool_id = aws_cognito_user_pool.ml_emotion_users.id

  # OAuth settings
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  allowed_oauth_flows_user_pool_client = true

  # Callback URLs (update with actual ALB DNS)
  callback_urls = [
    "https://${var.alb_dns_name}/oauth2/idpresponse"
  ]

  # Logout URLs
  logout_urls = [
    "https://${var.alb_dns_name}/"
  ]

  # Token validity
  access_token_validity  = 60  # minutes
  id_token_validity      = 60  # minutes
  refresh_token_validity = 30  # days

  # Prevent secret (ALB doesn't need it)
  generate_secret = true

  supported_identity_providers = ["COGNITO"]
}

# Outputs
output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.ml_emotion_users.id
}

output "cognito_user_pool_arn" {
  value = aws_cognito_user_pool.ml_emotion_users.arn
}

output "cognito_user_pool_domain" {
  value = aws_cognito_user_pool_domain.ml_emotion_auth.domain
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.alb_client.id
}

output "cognito_client_secret" {
  value     = aws_cognito_user_pool_client.alb_client.client_secret
  sensitive = true
}
```

#### Step 2.2: Update Ingress with Cognito Authentication

Update `deployment/k8s/prod/ingress.yaml`:

```yaml
metadata:
  annotations:
    # ... existing annotations ...

    # Cognito Authentication
    alb.ingress.kubernetes.io/auth-type: cognito
    alb.ingress.kubernetes.io/auth-idp-cognito: |
      {
        "userPoolArn": "arn:aws:cognito-idp:us-east-1:ACCOUNT_ID:userpool/USER_POOL_ID",
        "userPoolClientId": "CLIENT_ID",
        "userPoolDomain": "ml-speech-emotion-prod-auth.auth.us-east-1.amazoncognito.com"
      }

    # Session cookie settings
    alb.ingress.kubernetes.io/auth-session-cookie: AWSELBAuthSessionCookie
    alb.ingress.kubernetes.io/auth-session-timeout: "3600"  # 1 hour

    # On unauthenticated request
    alb.ingress.kubernetes.io/auth-on-unauthenticated-request: authenticate
```

#### Step 2.3: Create Initial Admin User

```bash
# Create admin user
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com \
  --temporary-password "TempPassword123!" \
  --message-action SUPPRESS \
  --region us-east-1

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_XXXXXXXXX \
  --username admin@example.com \
  --password "YourSecurePassword123!" \
  --permanent \
  --region us-east-1
```

---

### Phase 3: Grafana Integration

#### Step 3.1: Configure Grafana for Subpath

Update `deployment/k8s/prod/monitoring-stack.yaml` - Grafana deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
spec:
  template:
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:10.2.0
        env:
          # Serve Grafana from /grafana subpath
          - name: GF_SERVER_ROOT_URL
            value: "https://YOUR_ALB_DNS/grafana"
          - name: GF_SERVER_SERVE_FROM_SUB_PATH
            value: "true"

          # Disable anonymous access (use ALB auth instead)
          - name: GF_AUTH_ANONYMOUS_ENABLED
            value: "false"

          # Optional: Disable Grafana login (rely on ALB auth)
          - name: GF_AUTH_DISABLE_LOGIN_FORM
            value: "true"
          - name: GF_AUTH_DISABLE_SIGNOUT_MENU
            value: "true"

          # Auto-assign viewer role to authenticated users
          - name: GF_AUTH_PROXY_ENABLED
            value: "true"
          - name: GF_AUTH_PROXY_HEADER_NAME
            value: "X-Amzn-Oidc-Data"
          - name: GF_AUTH_PROXY_HEADER_PROPERTY
            value: "email"
          - name: GF_AUTH_PROXY_AUTO_SIGN_UP
            value: "true"
          - name: GF_USERS_AUTO_ASSIGN_ORG_ROLE
            value: "Viewer"  # or "Editor" or "Admin"

          # Existing config...
          - name: GF_SECURITY_ADMIN_PASSWORD
            value: "admin"
```

#### Step 3.2: Create Cross-Namespace Service

Since Ingress in `ml-speech-emotion` namespace needs to route to Grafana in `monitoring` namespace:

**Option A: ExternalName Service** (Recommended)

Create `deployment/k8s/prod/grafana-external-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grafana-external
  namespace: ml-speech-emotion
spec:
  type: ExternalName
  externalName: grafana.monitoring.svc.cluster.local
  ports:
    - port: 3000
      targetPort: 3000
      protocol: TCP
```

Then update Ingress to use `grafana-external` service.

**Option B: Create Ingress in Monitoring Namespace**

Create `deployment/k8s/prod/monitoring-ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: monitoring-ingress
  namespace: monitoring
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/group.name: ml-emotion-shared
    # ... same auth annotations as main ingress ...
spec:
  rules:
    - http:
        paths:
          - path: /grafana
            pathType: Prefix
            backend:
              service:
                name: grafana
                port:
                  number: 3000
```

**Note**: Use `alb.ingress.kubernetes.io/group.name` to merge into same ALB as main ingress.

#### Step 3.3: Update Ingress Routing

Final `deployment/k8s/prod/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ml-emotion-ingress
  namespace: ml-speech-emotion
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/group.name: ml-emotion-shared  # Merge with monitoring ingress

    # HTTPS
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: ${CERT_ARN}
    alb.ingress.kubernetes.io/ssl-redirect: "443"

    # Cognito Auth
    alb.ingress.kubernetes.io/auth-type: cognito
    alb.ingress.kubernetes.io/auth-idp-cognito: |
      {
        "userPoolArn": "${COGNITO_USER_POOL_ARN}",
        "userPoolClientId": "${COGNITO_CLIENT_ID}",
        "userPoolDomain": "${COGNITO_DOMAIN}"
      }
    alb.ingress.kubernetes.io/auth-session-timeout: "3600"

spec:
  rules:
    - http:
        paths:
          # Streamlit (default)
          - path: /
            pathType: Prefix
            backend:
              service:
                name: streamlit
                port:
                  number: 8501

          # Backend API
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
```

And create `deployment/k8s/prod/monitoring-ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: monitoring-ingress
  namespace: monitoring
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/group.name: ml-emotion-shared  # SAME group name

    # No need to repeat auth config - will inherit from group

spec:
  rules:
    - http:
        paths:
          # Grafana
          - path: /grafana
            pathType: Prefix
            backend:
              service:
                name: grafana
                port:
                  number: 3000
```

---

## Deployment Steps

### 1. Apply Terraform (Cognito + ACM)

```bash
cd deployment/terraform

# Add Cognito variables to terraform.tfvars
echo 'alb_dns_name = "YOUR_ALB_DNS"' >> terraform.tfvars

terraform plan
terraform apply

# Get outputs
COGNITO_USER_POOL_ARN=$(terraform output -raw cognito_user_pool_arn)
COGNITO_CLIENT_ID=$(terraform output -raw cognito_client_id)
COGNITO_DOMAIN=$(terraform output -raw cognito_user_pool_domain)
CERT_ARN=$(terraform output -raw acm_certificate_arn)
```

### 2. Update Kubernetes Manifests

```bash
# Update ingress with Cognito/ACM values
cd deployment/k8s/prod

# Option 1: Manual edit
vim ingress.yaml
vim monitoring-ingress.yaml
vim monitoring-stack.yaml

# Option 2: Use kustomize with env substitution
cat > kustomization.yaml <<EOF
resources:
  - namespace.yaml
  - backend-deployment.yaml
  - streamlit-deployment.yaml
  - ingress.yaml
  - monitoring-ingress.yaml
  - monitoring-stack.yaml

configMapGenerator:
  - name: alb-config
    literals:
      - COGNITO_USER_POOL_ARN=${COGNITO_USER_POOL_ARN}
      - COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID}
      - COGNITO_DOMAIN=${COGNITO_DOMAIN}
      - CERT_ARN=${CERT_ARN}
EOF
```

### 3. Deploy to EKS

```bash
# Update kubeconfig
aws eks update-kubeconfig --name ml-speech-emotion-prod-eks --region us-east-1

# Apply manifests
kubectl apply -f deployment/k8s/prod/ingress.yaml
kubectl apply -f deployment/k8s/prod/monitoring-ingress.yaml
kubectl apply -f deployment/k8s/prod/monitoring-stack.yaml

# Check ALB creation
kubectl get ingress -n ml-speech-emotion
kubectl get ingress -n monitoring

# Get ALB DNS (will be same for both due to group.name)
ALB_DNS=$(kubectl get ingress ml-emotion-ingress -n ml-speech-emotion \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Application URL: https://$ALB_DNS"
echo "Grafana URL: https://$ALB_DNS/grafana"
```

### 4. Create Admin User

```bash
# Get Cognito User Pool ID
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 10 \
  --query "UserPools[?Name=='ml-speech-emotion-prod-users'].Id" \
  --output text)

# Create admin user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com \
  --temporary-password "TempPassword123!" \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --password "SecurePassword123!" \
  --permanent
```

### 5. Test Authentication Flow

```bash
# 1. Visit application
open "https://$ALB_DNS"

# Expected flow:
# a. Redirected to Cognito login page
# b. Enter credentials (admin@example.com / SecurePassword123!)
# c. Redirected back to Streamlit app
# d. Session cookie set (valid for 1 hour)

# 2. Visit Grafana
open "https://$ALB_DNS/grafana"

# Expected:
# a. Already authenticated (same ALB session)
# b. Grafana loads with auto-login via auth proxy
# c. User has Viewer role by default
```

---

## Cost Considerations

### Additional Costs

1. **ACM Certificate**: **FREE**
2. **Cognito User Pool**:
   - First 50,000 MAUs: **FREE**
   - After: $0.0055 per MAU
3. **ALB HTTPS Listener**: Same ALB, no extra cost
4. **Data Transfer**: HTTPS has minimal overhead

**Total additional cost**: ~$0 for small teams (<50 users)

---

## Security Considerations

### 1. Session Management
- Session timeout: 1 hour (configurable)
- Session cookie: HTTPOnly, Secure flags
- Session stored in ALB (not in app)

### 2. User Management
- Cognito manages users (no app-level user DB)
- Email verification required
- Password policy enforced
- MFA optional (can enable)

### 3. Grafana Security
- Disable Grafana login form (rely on ALB auth)
- Use auth proxy for automatic user creation
- Assign read-only "Viewer" role by default
- Admins can be promoted manually in Grafana

### 4. Network Security
- All traffic encrypted via HTTPS
- ALB handles SSL termination
- Internal services communicate over HTTP (within VPC)

---

## Alternative: Simpler Approach (No Cognito)

If you want to avoid Cognito complexity:

### Option 1: Basic Auth via ALB

```yaml
# Ingress annotation
alb.ingress.kubernetes.io/auth-type: "fixed-response"
# Not supported by ALB - need to use nginx ingress or OAuth2 Proxy
```

### Option 2: OAuth2 Proxy Sidecar

Deploy OAuth2 Proxy as a separate service:

```yaml
# oauth2-proxy deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oauth2-proxy
  namespace: ml-speech-emotion
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: oauth2-proxy
        image: quay.io/oauth2-proxy/oauth2-proxy:v7.5.0
        args:
          - --provider=google
          - --email-domain=*
          - --upstream=http://streamlit:8501
          - --http-address=0.0.0.0:4180
          - --cookie-secret=RANDOM_SECRET
          - --client-id=GOOGLE_CLIENT_ID
          - --client-secret=GOOGLE_CLIENT_SECRET
```

Then route Ingress to OAuth2 Proxy instead of Streamlit directly.

---

## Next Steps

1. **Choose authentication method**:
   - Cognito (recommended for AWS)
   - OAuth2 Proxy (for Google/GitHub OAuth)
   - Custom auth in app

2. **Request ACM certificate**:
   - With custom domain, or
   - Use ALB DNS directly

3. **Apply Terraform changes**:
   - Add Cognito resources
   - Output values for K8s

4. **Update Kubernetes manifests**:
   - Ingress with HTTPS + auth
   - Grafana with subpath config
   - Monitoring ingress

5. **Test end-to-end**:
   - Login flow
   - Grafana access
   - Session persistence

Would you like me to implement any specific approach?
