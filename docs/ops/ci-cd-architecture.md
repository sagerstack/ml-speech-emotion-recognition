# CI/CD Architecture

## Overview
This project implements a "build once, deploy many" CI/CD pipeline where Docker images are built and validated in CI, then deployed in CD without rebuilding.

## Pipeline Flow

### CI Pipeline (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` branch
- Pull requests to `main` branch

**Jobs (Run in Parallel):**

1. **tests** - Unit tests with pytest
2. **terraform-format** - Terraform formatting validation
3. **validate-docker-builds** - Docker build validation and container smoke tests

**Final Job (Only if All Gates Pass):**

4. **build-and-push**
   - **Depends on:** tests, terraform-format, validate-docker-builds
   - **OIDC authentication** (only after all gates pass)
   - **Builds** backend and streamlit Docker images
   - **Pushes to ECR** with appropriate tags:
     - **Pull Requests:** `pr-<number>` (e.g., `pr-42`)
     - **Main branch:** `<sha>` (first 7 chars) and `latest`

### CD Pipeline (`.github/workflows/cd.yml`)

**Triggers:**
- Push to `main` branch (after CI completes)
- Manual workflow dispatch

**Jobs:**

1. **deploy**
   - **Uses pre-built images** from ECR (no rebuild!)
   - **OIDC authentication**
   - **Pulls images** with SHA tag (e.g., `abc1234`)
   - **Deploys to EKS** using Kustomize
   - **Verifies rollout** and runs smoke tests

## Benefits

✅ **Build Once, Deploy Many** - Same image tested in CI and deployed in CD
✅ **Immutable Artifacts** - Images tagged by commit SHA, never rebuilt
✅ **Fast Deployments** - CD just pulls and deploys, no build time
✅ **Gates Block OIDC** - AWS credentials only granted after all tests pass
✅ **PR Validation** - PRs build and push test images to ECR
✅ **Traceability** - SHA tags link deployed images to exact commits
✅ **Easy Rollbacks** - Redeploy any previous SHA tag instantly

## Image Tagging Strategy

### Pull Requests
```
backend:pr-42
streamlit:pr-42
```
- Allows testing PR images independently
- Cleaned up by ECR lifecycle policy (keep last 10)

### Main Branch
```
backend:abc1234  (commit SHA)
backend:latest

streamlit:abc1234  (commit SHA)
streamlit:latest
```
- SHA tag for immutable deployment
- Latest tag for convenience

## ECR Storage Management

### Recommended Lifecycle Policy

To prevent unbounded storage costs, configure ECR lifecycle policies:

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 10 PR images",
      "selection": {
        "tagPrefixList": ["pr-"],
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Keep last 20 production images (SHA tags)",
      "selection": {
        "tagStatus": "tagged",
        "tagPrefixList": [""],
        "countType": "imageCountMoreThan",
        "countNumber": 20
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 3,
      "description": "Always keep latest tag",
      "selection": {
        "tagStatus": "tagged",
        "tagPrefixList": ["latest"]
      },
      "action": {
        "type": "keep"
      }
    }
  ]
}
```

**Apply with AWS CLI:**
```bash
# For backend repository
aws ecr put-lifecycle-policy \
  --repository-name ml-speech-emotion-backend \
  --lifecycle-policy-text file://ecr-lifecycle-policy.json

# For streamlit repository
aws ecr put-lifecycle-policy \
  --repository-name ml-speech-emotion-streamlit \
  --lifecycle-policy-text file://ecr-lifecycle-policy.json
```

**Estimated Cost with Lifecycle Policy:**
- Keep last 10 PR images + 20 production images
- ~30 images × 1.2 GB average = 36 GB stored
- Cost: 36 GB × $0.10/GB/month = **~$3.60/month**

## Workflow Dependencies

### For Main Branch Pushes:

```
Push to main
    │
    ▼
┌─────────────────────────────────────────┐
│  CI Workflow                            │
├─────────────────────────────────────────┤
│  1. Run tests (parallel)                │
│  2. Run terraform-format (parallel)     │
│  3. Validate docker builds (parallel)   │
│         │                                │
│    All pass?                            │
│         │                                │
│         ▼                                │
│  4. OIDC auth                           │
│  5. Build images                        │
│  6. Push to ECR                         │
│     - Tags: <sha>, latest               │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  CD Workflow                            │
├─────────────────────────────────────────┤
│  1. OIDC auth                           │
│  2. Pull pre-built images from ECR      │
│  3. Deploy to EKS with kustomize        │
│  4. Verify rollout                      │
│  5. Run smoke tests                     │
└─────────────────────────────────────────┘
```

### For Pull Requests:

```
PR created/updated
    │
    ▼
┌─────────────────────────────────────────┐
│  CI Workflow (Only)                     │
├─────────────────────────────────────────┤
│  1. Run tests                           │
│  2. Run terraform-format                │
│  3. Validate docker builds              │
│         │                                │
│    All pass?                            │
│         │                                │
│         ▼                                │
│  4. OIDC auth                           │
│  5. Build images                        │
│  6. Push to ECR with pr-<number> tag    │
│                                          │
│  ✅ PR can be merged if all pass        │
└─────────────────────────────────────────┘

(CD workflow does NOT run on PRs)
```

## Cost Implications

### CI Workflow
- **GitHub Actions minutes:** ~10-15 minutes per run
  - Free tier: 2,000 minutes/month (private repos)
  - Well within free tier for most usage

- **ECR Storage:** ~$1-4/month (with lifecycle policy)
- **ECR Data Transfer:**
  - Push: FREE
  - Pull (same region): FREE

### CD Workflow
- **GitHub Actions minutes:** ~5-8 minutes per deployment
- **No additional ECR costs** (images already built)

### Total Estimated Cost
- **~$3-5/month** for ECR storage (with lifecycle cleanup)
- **$0** for GitHub Actions (within free tier)

## Security Model

### OIDC Authentication
- **No long-lived AWS credentials** stored in GitHub
- **Temporary tokens** (valid for hours, not years)
- **Branch-scoped trust** - Only `main` branch can deploy to production
- **Repository-scoped trust** - Only this specific repo can assume the role

### Gate Enforcement
- All quality, security, and test gates must pass **before** OIDC authentication
- Failed gates = No AWS access = No deployment
- Images are validated before push to ECR

## Rollback Procedure

To rollback to a previous version:

```bash
# Find the commit SHA you want to rollback to
git log --oneline

# Update kustomization to use that SHA
cd deployment/k8s/prod
kustomize edit set image \
  sagerstack/ml-speech-emotion-backend=<ecr-url>:<old-sha> \
  sagerstack/ml-speech-emotion-streamlit=<ecr-url>:<old-sha>

# Apply
kubectl apply -k .

# Or trigger CD workflow manually with workflow_dispatch
```

## Future Enhancements

Potential additions to the pipeline:

- [ ] Code quality gates (ruff, black, mypy)
- [ ] Security scanning (bandit, pip-audit)
- [ ] Test coverage requirements (pytest-cov)
- [ ] Terraform security scanning (tfsec)
- [ ] Integration tests in CI against ECR images
- [ ] Automated rollback on failed smoke tests
- [ ] Slack/Discord notifications
- [ ] Performance benchmarking
- [ ] Container image scanning (Trivy, Grype)
