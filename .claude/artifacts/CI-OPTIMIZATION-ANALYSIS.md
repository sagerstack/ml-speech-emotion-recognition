# CI Docker Image Build Optimization Analysis

## Executive Summary

Currently, the CI workflow rebuilds and pushes **all 3 Docker images** (Backend, Streamlit, SageMaker) on **every push to main**, regardless of whether the relevant code has changed. This results in:

- **Wasted CI minutes**: ~8-12 minutes per run
- **Unnecessary ECR storage costs**: ~$0.10/GB/month for duplicate images
- **Slower deployments**: CD waits for all images even if only one changed
- **ECR bandwidth costs**: Pushing unchanged 500MB+ images repeatedly

## Current State Analysis

### Image Dependencies

#### 1. Backend Image (`ml-speech-emotion-backend`)
**Size:** ~800MB
**Build Time:** ~3-4 minutes
**Triggers rebuild when these files change:**
```
backend/
├── app/                    # Application code
├── models/                 # ML model files (500MB+)
├── pyproject.toml          # Dependencies
├── poetry.lock             # Locked versions
└── .env.example

deployment/docker/backend/Dockerfile
```

#### 2. Streamlit Image (`ml-speech-emotion-streamlit`)
**Size:** ~600MB
**Build Time:** ~2-3 minutes
**Triggers rebuild when these files change:**
```
frontend/streamlit_app/
├── src/                    # Application code
├── requirements.txt        # Dependencies
├── .streamlit/config.toml  # Configuration
└── docs/

deployment/docker/streamlit/Dockerfile
```

#### 3. SageMaker Container (`ml-speech-emotion-sklearn`)
**Size:** ~400MB
**Build Time:** ~2-3 minutes
**Triggers rebuild when these files change:**
```
deployment/sagemaker/container/
├── Dockerfile              # Container definition
├── serve                   # Entrypoint script
├── nginx.conf              # Web server config
└── wsgi.py                 # WSGI application
```

### Current CI Workflow Issues

```yaml
# Current workflow always rebuilds all images:
build-docker-images:
  needs: [tests, terraform-format]
  steps:
    - Build backend     # Always runs (3-4 min)
    - Build streamlit   # Always runs (2-3 min)

push-to-ecr:
  needs: [build-docker-images]
  steps:
    - Build & push backend      # Always runs (4-5 min)
    - Build & push streamlit    # Always runs (3-4 min)
    - Build & push sagemaker    # Always runs (3-4 min)
```

**Total wasted time per run:** 15-20 minutes if no code changes
**ECR storage waste:** 1.8GB x N duplicate pushes

---

## Optimization Approaches

### Approach 1: Path-Based Change Detection (Recommended)

**Concept:** Use `paths-filter` action to detect which directories changed, skip builds for unchanged components.

**Implementation:**

```yaml
jobs:
  # Step 1: Detect what changed
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      streamlit: ${{ steps.filter.outputs.streamlit }}
      sagemaker: ${{ steps.filter.outputs.sagemaker }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Detect file changes
        uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            backend:
              - 'backend/**'
              - 'deployment/docker/backend/**'
            streamlit:
              - 'frontend/streamlit_app/**'
              - 'deployment/docker/streamlit/**'
            sagemaker:
              - 'deployment/sagemaker/container/**'

  # Step 2: Build only changed images (CI test builds)
  build-docker-images:
    runs-on: ubuntu-latest
    needs: [tests, terraform-format, detect-changes]
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build backend Docker image
        if: needs.detect-changes.outputs.backend == 'true'
        run: |
          docker build \
            -f deployment/docker/backend/Dockerfile \
            -t backend:ci-test \
            --load \
            .

      - name: Build Streamlit Docker image
        if: needs.detect-changes.outputs.streamlit == 'true'
        run: |
          docker build \
            -f deployment/docker/streamlit/Dockerfile \
            -t streamlit:ci-test \
            --load \
            .

  # Step 3: Push only changed images to ECR
  push-to-ecr:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    needs: [build-docker-images, detect-changes]
    permissions:
      id-token: write
      contents: read
    env:
      AWS_REGION: us-east-1
      BACKEND_REPO_NAME: ml-speech-emotion-backend
      STREAMLIT_REPO_NAME: ml-speech-emotion-streamlit

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Configure AWS credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-region: ${{ env.AWS_REGION }}
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}

      - name: Log in to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Compute image URIs and tags
        id: image-meta
        run: |
          ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
          BACKEND_IMAGE="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${BACKEND_REPO_NAME}"
          STREAMLIT_IMAGE="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${STREAMLIT_REPO_NAME}"

          echo "BACKEND_IMAGE=${BACKEND_IMAGE}" >> $GITHUB_ENV
          echo "STREAMLIT_IMAGE=${STREAMLIT_IMAGE}" >> $GITHUB_ENV

          TAG="${GITHUB_SHA:0:7}"
          echo "IMAGE_TAG=${TAG}" >> $GITHUB_ENV
          echo "Building images with tag: ${TAG}"

      - name: Build and push backend image to ECR
        if: needs.detect-changes.outputs.backend == 'true'
        run: |
          echo "🔨 Backend code changed - rebuilding image..."
          docker build \
            -f deployment/docker/backend/Dockerfile \
            -t "${BACKEND_IMAGE}:${IMAGE_TAG}" \
            -t "${BACKEND_IMAGE}:latest" \
            --load \
            .

          docker push "${BACKEND_IMAGE}:${IMAGE_TAG}"
          docker push "${BACKEND_IMAGE}:latest"

      - name: Skip backend build
        if: needs.detect-changes.outputs.backend == 'false'
        run: |
          echo "✓ Backend code unchanged - skipping build"
          echo "Using existing image: ${BACKEND_IMAGE}:latest"

      - name: Build and push Streamlit image to ECR
        if: needs.detect-changes.outputs.streamlit == 'true'
        run: |
          echo "🔨 Streamlit code changed - rebuilding image..."
          docker build \
            -f deployment/docker/streamlit/Dockerfile \
            -t "${STREAMLIT_IMAGE}:${IMAGE_TAG}" \
            -t "${STREAMLIT_IMAGE}:latest" \
            --load \
            .

          docker push "${STREAMLIT_IMAGE}:${IMAGE_TAG}"
          docker push "${STREAMLIT_IMAGE}:latest"

      - name: Skip streamlit build
        if: needs.detect-changes.outputs.streamlit == 'false'
        run: |
          echo "✓ Streamlit code unchanged - skipping build"
          echo "Using existing image: ${STREAMLIT_IMAGE}:latest"

      - name: Build and push SageMaker container to ECR
        if: needs.detect-changes.outputs.sagemaker == 'true'
        run: |
          echo "🔨 SageMaker container changed - rebuilding image..."

          ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
          SAGEMAKER_REPO_NAME="ml-speech-emotion-sklearn"
          SAGEMAKER_IMAGE="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${SAGEMAKER_REPO_NAME}"
          SKLEARN_VERSION="1.7.2"
          PYTHON_VERSION="py310"
          SAGEMAKER_TAG="${SKLEARN_VERSION}-${PYTHON_VERSION}"

          # Check if ECR repository exists, create if not
          if ! aws ecr describe-repositories \
            --repository-names "${SAGEMAKER_REPO_NAME}" \
            --region "${AWS_REGION}" >/dev/null 2>&1; then

            aws ecr create-repository \
              --repository-name "${SAGEMAKER_REPO_NAME}" \
              --region "${AWS_REGION}" \
              --image-scanning-configuration scanOnPush=true \
              --encryption-configuration encryptionType=AES256

            aws ecr put-lifecycle-policy \
              --repository-name "${SAGEMAKER_REPO_NAME}" \
              --region "${AWS_REGION}" \
              --lifecycle-policy-text '{
                "rules": [{
                  "rulePriority": 1,
                  "description": "Keep last 5 images",
                  "selection": {
                    "tagStatus": "any",
                    "countType": "imageCountMoreThan",
                    "countNumber": 5
                  },
                  "action": {"type": "expire"}
                }]
              }'
          fi

          docker build \
            -f deployment/sagemaker/container/Dockerfile \
            -t "${SAGEMAKER_IMAGE}:${SAGEMAKER_TAG}" \
            -t "${SAGEMAKER_IMAGE}:latest" \
            --load \
            deployment/sagemaker/container/

          docker push "${SAGEMAKER_IMAGE}:${SAGEMAKER_TAG}"
          docker push "${SAGEMAKER_IMAGE}:latest"

      - name: Skip SageMaker build
        if: needs.detect-changes.outputs.sagemaker == 'false'
        run: |
          echo "✓ SageMaker container unchanged - skipping build"
          SAGEMAKER_IMAGE="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ml-speech-emotion-sklearn"
          echo "Using existing image: ${SAGEMAKER_IMAGE}:1.7.2-py310"

      - name: Output image status
        run: |
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "📦 Image Build Status"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

          if [ "${{ needs.detect-changes.outputs.backend }}" == "true" ]; then
            echo "Backend:   ${BACKEND_IMAGE}:${IMAGE_TAG} ✨ NEW"
          else
            echo "Backend:   ${BACKEND_IMAGE}:latest ♻️ REUSED"
          fi

          if [ "${{ needs.detect-changes.outputs.streamlit }}" == "true" ]; then
            echo "Streamlit: ${STREAMLIT_IMAGE}:${IMAGE_TAG} ✨ NEW"
          else
            echo "Streamlit: ${STREAMLIT_IMAGE}:latest ♻️ REUSED"
          fi

          ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
          SAGEMAKER_IMAGE="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/ml-speech-emotion-sklearn"

          if [ "${{ needs.detect-changes.outputs.sagemaker }}" == "true" ]; then
            echo "SageMaker: ${SAGEMAKER_IMAGE}:1.7.2-py310 ✨ NEW"
          else
            echo "SageMaker: ${SAGEMAKER_IMAGE}:1.7.2-py310 ♻️ REUSED"
          fi

          echo ""
```

**Pros:**
- ✅ Simple to implement and understand
- ✅ Works with all CI systems (GitHub Actions, GitLab, Jenkins)
- ✅ No external dependencies beyond a single action
- ✅ Clear visibility - shows which images were rebuilt vs reused
- ✅ Maintains same security model (OIDC, IAM roles)
- ✅ **Savings: 70-80% reduction in build time** for typical commits that touch 1-2 components
- ✅ **Saves ECR storage costs** by not pushing duplicate images

**Cons:**
- ⚠️ Path-based detection can miss indirect dependencies (e.g., shared utilities)
- ⚠️ First push to a new branch always builds all images
- ⚠️ If someone changes multiple components, saves nothing

**Best For:** Teams with modular codebases where changes are typically isolated to one component

---

### Approach 2: Content-Hash Based Detection

**Concept:** Calculate SHA256 hash of all files that affect each image, check if image with that hash exists in ECR.

**Implementation:**

```yaml
jobs:
  compute-image-hashes:
    runs-on: ubuntu-latest
    outputs:
      backend-hash: ${{ steps.backend.outputs.hash }}
      streamlit-hash: ${{ steps.streamlit.outputs.hash }}
      sagemaker-hash: ${{ steps.sagemaker.outputs.hash }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Compute backend hash
        id: backend
        run: |
          # Hash all files that affect backend image
          HASH=$(find backend/ deployment/docker/backend/ \
            -type f \
            \( -name "*.py" -o -name "*.toml" -o -name "*.lock" -o -name "Dockerfile" \) \
            -exec sha256sum {} \; | \
            sort | \
            sha256sum | \
            cut -d' ' -f1 | \
            cut -c1-12)
          echo "hash=${HASH}" >> $GITHUB_OUTPUT
          echo "Backend content hash: ${HASH}"

      - name: Compute streamlit hash
        id: streamlit
        run: |
          HASH=$(find frontend/streamlit_app/ deployment/docker/streamlit/ \
            -type f \
            \( -name "*.py" -o -name "*.txt" -o -name "*.toml" -o -name "Dockerfile" \) \
            -exec sha256sum {} \; | \
            sort | \
            sha256sum | \
            cut -d' ' -f1 | \
            cut -c1-12)
          echo "hash=${HASH}" >> $GITHUB_OUTPUT
          echo "Streamlit content hash: ${HASH}"

      - name: Compute sagemaker hash
        id: sagemaker
        run: |
          HASH=$(find deployment/sagemaker/container/ \
            -type f \
            -exec sha256sum {} \; | \
            sort | \
            sha256sum | \
            cut -d' ' -f1 | \
            cut -c1-12)
          echo "hash=${HASH}" >> $GITHUB_OUTPUT
          echo "SageMaker content hash: ${HASH}"

  check-existing-images:
    runs-on: ubuntu-latest
    needs: [compute-image-hashes]
    outputs:
      backend-exists: ${{ steps.check-backend.outputs.exists }}
      streamlit-exists: ${{ steps.check-streamlit.outputs.exists }}
      sagemaker-exists: ${{ steps.check-sagemaker.outputs.exists }}
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-region: us-east-1
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}

      - name: Check if backend image exists
        id: check-backend
        run: |
          HASH="${{ needs.compute-image-hashes.outputs.backend-hash }}"
          ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
          IMAGE="${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-backend"

          if aws ecr describe-images \
            --repository-name ml-speech-emotion-backend \
            --image-ids imageTag="${HASH}" \
            --region us-east-1 >/dev/null 2>&1; then
            echo "exists=true" >> $GITHUB_OUTPUT
            echo "✓ Backend image ${HASH} already exists in ECR"
          else
            echo "exists=false" >> $GITHUB_OUTPUT
            echo "✗ Backend image ${HASH} not found - needs rebuild"
          fi

      - name: Check if streamlit image exists
        id: check-streamlit
        run: |
          HASH="${{ needs.compute-image-hashes.outputs.streamlit-hash }}"
          ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
          IMAGE="${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-streamlit"

          if aws ecr describe-images \
            --repository-name ml-speech-emotion-streamlit \
            --image-ids imageTag="${HASH}" \
            --region us-east-1 >/dev/null 2>&1; then
            echo "exists=true" >> $GITHUB_OUTPUT
            echo "✓ Streamlit image ${HASH} already exists in ECR"
          else
            echo "exists=false" >> $GITHUB_OUTPUT
            echo "✗ Streamlit image ${HASH} not found - needs rebuild"
          fi

      - name: Check if sagemaker image exists
        id: check-sagemaker
        run: |
          HASH="${{ needs.compute-image-hashes.outputs.sagemaker-hash }}"
          ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
          IMAGE="${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/ml-speech-emotion-sklearn"

          if aws ecr describe-images \
            --repository-name ml-speech-emotion-sklearn \
            --image-ids imageTag="${HASH}" \
            --region us-east-1 >/dev/null 2>&1; then
            echo "exists=true" >> $GITHUB_OUTPUT
            echo "✓ SageMaker image ${HASH} already exists in ECR"
          else
            echo "exists=false" >> $GITHUB_OUTPUT
            echo "✗ SageMaker image ${HASH} not found - needs rebuild"
          fi

  push-to-ecr:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    needs: [compute-image-hashes, check-existing-images]
    steps:
      - name: Build and push backend image
        if: needs.check-existing-images.outputs.backend-exists == 'false'
        run: |
          HASH="${{ needs.compute-image-hashes.outputs.backend-hash }}"
          # Build and tag with hash + latest
          docker build \
            -f deployment/docker/backend/Dockerfile \
            -t "${BACKEND_IMAGE}:${HASH}" \
            -t "${BACKEND_IMAGE}:latest" \
            --load \
            .
          docker push "${BACKEND_IMAGE}:${HASH}"
          docker push "${BACKEND_IMAGE}:latest"

      - name: Reuse existing backend image
        if: needs.check-existing-images.outputs.backend-exists == 'true'
        run: |
          HASH="${{ needs.compute-image-hashes.outputs.backend-hash }}"
          # Just re-tag existing image as latest
          MANIFEST=$(aws ecr batch-get-image \
            --repository-name ml-speech-emotion-backend \
            --image-ids imageTag="${HASH}" \
            --query 'images[0].imageManifest' \
            --output text)

          aws ecr put-image \
            --repository-name ml-speech-emotion-backend \
            --image-tag latest \
            --image-manifest "${MANIFEST}"

          echo "✓ Re-tagged existing backend image ${HASH} as latest"
```

**Pros:**
- ✅ **Most accurate** - only rebuilds when actual content changes
- ✅ Works across branches - if feature branch has same code as main, reuses image
- ✅ Detects even whitespace/comment changes (can be pro or con)
- ✅ Historical images remain tagged by hash for rollbacks
- ✅ **Highest savings potential** - 85-90% reduction for non-code changes (docs, configs, etc.)

**Cons:**
- ❌ More complex to implement and maintain
- ❌ Requires ECR API calls before build (adds ~10-20 seconds)
- ❌ Hash calculation can be expensive for large repos
- ❌ Need careful file filtering to avoid false positives (e.g., exclude README.md)
- ❌ Re-tagging existing images requires more ECR permissions

**Best For:** Teams with strict cost optimization requirements, or large monorepos where builds are very expensive

---

### Approach 3: Docker Layer Caching with BuildKit

**Concept:** Use Docker BuildKit's advanced caching to avoid rebuilding unchanged layers.

**Implementation:**

```yaml
jobs:
  push-to-ecr:
    steps:
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push backend with cache
        uses: docker/build-push-action@v5
        with:
          context: .
          file: deployment/docker/backend/Dockerfile
          push: true
          tags: |
            ${{ env.BACKEND_IMAGE }}:${{ env.IMAGE_TAG }}
            ${{ env.BACKEND_IMAGE }}:latest
          cache-from: type=registry,ref=${{ env.BACKEND_IMAGE }}:buildcache
          cache-to: type=registry,ref=${{ env.BACKEND_IMAGE }}:buildcache,mode=max
```

**Pros:**
- ✅ Docker-native solution, works everywhere
- ✅ Granular layer caching - reuses unchanged layers even within a single image
- ✅ Easy to implement with GitHub Actions
- ✅ Works well with multi-stage builds

**Cons:**
- ❌ **Still pushes images to ECR every time** (just faster due to layer reuse)
- ❌ Cache storage costs in ECR (~same size as images)
- ❌ Doesn't skip build entirely, just speeds it up
- ❌ "buildcache" tags consume ECR storage quota

**Best For:** Use **in combination with Approach 1 or 2** for maximum efficiency

---

### Approach 4: Hybrid Strategy (Recommended for Production)

**Concept:** Combine path-based detection (fast, simple) with Docker layer caching (granular optimization).

**Implementation:**

```yaml
jobs:
  detect-changes:
    # ... same as Approach 1 ...

  push-to-ecr:
    steps:
      - name: Build and push backend image
        if: needs.detect-changes.outputs.backend == 'true'
        uses: docker/build-push-action@v5
        with:
          context: .
          file: deployment/docker/backend/Dockerfile
          push: true
          tags: |
            ${{ env.BACKEND_IMAGE }}:${{ env.IMAGE_TAG }}
            ${{ env.BACKEND_IMAGE }}:latest
          cache-from: type=registry,ref=${{ env.BACKEND_IMAGE }}:buildcache
          cache-to: type=registry,ref=${{ env.BACKEND_IMAGE }}:buildcache,mode=max

      - name: Skip backend build
        if: needs.detect-changes.outputs.backend == 'false'
        run: echo "✓ Backend unchanged - skipping build entirely"
```

**Benefits:**
- ✅ Skip entire build when component unchanged (Approach 1)
- ✅ Fast layer reuse when component changed (Approach 3)
- ✅ Best of both worlds
- ✅ **Expected savings: 75-85% reduction** in build time and ECR operations

---

## Cost-Benefit Analysis

### Current State Costs (Monthly)

Assuming 50 commits/month to main branch:

| Resource | Calculation | Monthly Cost |
|----------|-------------|--------------|
| GitHub Actions minutes | 50 runs × 20 min × $0.008/min | $8.00 |
| ECR storage (3 repos) | 1.8GB × 50 versions × $0.10/GB | $9.00 |
| ECR data transfer | 1.8GB × 50 pushes × $0.09/GB | $8.10 |
| **Total** | | **$25.10** |

### With Approach 1 (Path-Based) - Assumes 30% of commits touch each component

| Resource | Calculation | Monthly Cost | Savings |
|----------|-------------|--------------|---------|
| GitHub Actions minutes | 50 runs × 6 min × $0.008/min | $2.40 | **-$5.60 (70%)** |
| ECR storage | 1.8GB × 15 versions × $0.10/GB | $2.70 | **-$6.30 (70%)** |
| ECR data transfer | 1.8GB × 15 pushes × $0.09/GB | $2.43 | **-$5.67 (70%)** |
| **Total** | | **$7.53** | **-$17.57 (70%)** |

### With Approach 2 (Content Hash) - Assumes 20% actual code changes

| Resource | Calculation | Monthly Cost | Savings |
|----------|-------------|--------------|---------|
| GitHub Actions minutes | 50 runs × 4 min × $0.008/min | $1.60 | **-$6.40 (80%)** |
| ECR storage | 1.8GB × 10 versions × $0.10/GB | $1.80 | **-$7.20 (80%)** |
| ECR data transfer | 1.8GB × 10 pushes × $0.09/GB | $1.62 | **-$6.48 (80%)** |
| **Total** | | **$5.02** | **-$20.08 (80%)** |

### Annual Savings Projection

- **Approach 1:** $210.84/year
- **Approach 2:** $240.96/year
- **Approach 4 (Hybrid):** ~$250/year

---

## Recommendation Matrix

| Scenario | Recommended Approach | Rationale |
|----------|---------------------|-----------|
| **Current project (small team, rapid iteration)** | **Approach 1** (Path-based) | Simple, 70% savings, easy to maintain |
| **Production at scale (>100 commits/month)** | **Approach 4** (Hybrid) | Maximum savings with layer caching |
| **Cost-critical environment** | **Approach 2** (Content-hash) | Highest accuracy, 80%+ savings |
| **Quick win (minimal changes)** | **Approach 3** (Layer caching only) | Just add 3 lines to existing workflow |

---

## Implementation Checklist

### For Approach 1 (Recommended)

- [ ] Add `dorny/paths-filter@v3` action to workflow
- [ ] Define path filters for each component
- [ ] Add `detect-changes` job as dependency
- [ ] Add `if: needs.detect-changes.outputs.X == 'true'` conditionals to each build step
- [ ] Add skip messages for unchanged components
- [ ] Update output step to show ✨ NEW vs ♻️ REUSED status
- [ ] Test with commits that change each component individually
- [ ] Test with commits that change multiple components
- [ ] Test with commits that change only docs/terraform (should skip all builds)
- [ ] Monitor savings in Actions usage reports

### Testing Strategy

```bash
# Test 1: Change only backend code
git checkout -b test/backend-only
echo "# comment" >> backend/app/main.py
git add . && git commit -m "test: backend change"
git push

# Expected: Only backend image builds, others show "♻️ REUSED"

# Test 2: Change only streamlit code
git checkout -b test/streamlit-only
echo "# comment" >> frontend/streamlit_app/src/ml-app.py
git add . && git commit -m "test: streamlit change"
git push

# Expected: Only streamlit image builds, others show "♻️ REUSED"

# Test 3: Change only documentation
git checkout -b test/docs-only
echo "# update" >> README.md
git add . && git commit -m "docs: update readme"
git push

# Expected: All images show "♻️ REUSED", total build time <1min
```

---

## Edge Cases to Handle

### 1. Shared Dependencies

**Problem:** What if `backend/app/utils.py` is used by both backend and streamlit?

**Solution:** Add it to both filters:
```yaml
filters: |
  backend:
    - 'backend/**'
    - 'deployment/docker/backend/**'
  streamlit:
    - 'frontend/streamlit_app/**'
    - 'deployment/docker/streamlit/**'
    - 'backend/app/utils.py'  # Shared file
```

### 2. Force Rebuild

**Problem:** How to force rebuild all images even if unchanged?

**Solution:** Add workflow input parameter:
```yaml
on:
  workflow_dispatch:
    inputs:
      force_rebuild:
        description: 'Force rebuild all images'
        required: false
        default: 'false'
        type: choice
        options:
          - 'true'
          - 'false'

# Then in conditions:
if: |
  needs.detect-changes.outputs.backend == 'true' ||
  github.event.inputs.force_rebuild == 'true'
```

### 3. First Build on New Branch

**Problem:** First push to new branch has no base to compare against - builds everything.

**Solution:** This is expected and correct behavior. Use `base` parameter in paths-filter:
```yaml
- uses: dorny/paths-filter@v3
  with:
    base: main  # Always compare against main, not previous commit
```

### 4. Large Model Files

**Problem:** Backend image contains 500MB+ of model files that rarely change.

**Solution:** Consider moving models to S3 and downloading at runtime, or use multi-stage build with model-specific caching layer.

---

## Metrics to Track

After implementation, monitor these metrics in GitHub Actions and AWS:

### GitHub Actions Metrics
- **Total workflow duration** (target: -70% for single-component changes)
- **Billable minutes per month** (target: reduce from ~1000min to ~300min)
- **Cache hit rate** (if using layer caching)

### AWS ECR Metrics
- **Storage usage per repository** (target: -70% growth rate)
- **Number of image pushes per month** (target: -70% for unchanged components)
- **Data transfer out** (should decrease proportionally)

### Dashboards

Add CloudWatch dashboard or similar to track:
```
- ECR repository size over time (should flatten)
- Number of image pushes per day (should decrease)
- Average CI workflow duration (should decrease)
- Cost trends (Actions + ECR should decrease)
```

---

## Migration Path

### Phase 1: Validation (Week 1)
1. Implement Approach 1 on feature branch
2. Run parallel builds (old + new) to compare
3. Validate that skipped builds don't break deployments
4. Measure time savings on test runs

### Phase 2: Rollout (Week 2)
1. Merge to main after validation
2. Monitor for issues
3. Educate team on new behavior (why some builds show "REUSED")
4. Document force-rebuild procedure

### Phase 3: Optimization (Week 3-4)
1. Add layer caching (Approach 3) on top
2. Fine-tune path filters based on real-world usage
3. Add metrics dashboard
4. Calculate actual cost savings

### Phase 4: Advanced (Optional)
1. Consider Approach 2 (content-hash) if cost savings justify complexity
2. Implement automatic cache cleanup policies
3. Add image vulnerability scanning on changed images only

---

## Conclusion

**Recommended Implementation: Approach 1 (Path-Based Change Detection)**

This provides the best balance of:
- **Simplicity** (easy to implement and maintain)
- **Effectiveness** (70-80% time/cost savings)
- **Safety** (clear visibility into what's being built vs reused)
- **Flexibility** (easy to add force-rebuild option)

The implementation can be completed in ~2-3 hours and will pay for itself within the first month through reduced GitHub Actions and ECR costs.

For future optimization, layer caching (Approach 3) can be added on top with minimal additional effort, bringing total savings to 80-85%.
