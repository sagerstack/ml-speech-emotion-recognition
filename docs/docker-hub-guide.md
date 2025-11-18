# 🐳 Docker Hub Deployment Guide

This guide covers building and pushing Docker images to Docker Hub using the `sagerstack` repository.

## 📋 Prerequisites

### Docker Hub Account
- **Docker Hub Account**: Create account at https://hub.docker.com
- **Repository Names**: Images will be pushed to:
  - `sagerstack/ml-emotion-backend`
  - `sagerstack/ml-emotion-frontend`
  - `sagerstack/ml-emotion-streamlit`

### Local Setup
- **Docker Desktop**: Installed and running
- **Project Code**: Complete ML Speech Emotion Recognition project
- **Build Script**: `deployment/docker/build.sh` script

## 🔐 Docker Hub Authentication

### Method 1: Docker Login (Recommended)
```bash
# Login to Docker Hub
docker login

# Enter your Docker Hub username and password when prompted
# Username: sagerstack
# Password: your-docker-hub-password
```

### Method 2: Personal Access Token
```bash
# Create Personal Access Token in Docker Hub settings
# Use token instead of password
docker login --username sagerstack
# Password: your-personal-access-token
```

### Verify Login
```bash
# Check if you're logged in
docker info | grep Username
# Should show: Username: sagerstack
```

## 🏗️ Building and Pushing Images

### Build Script Usage
```bash
# Navigate to project root
cd /path/to/ml-speech-emotion-recognition

# Build all images (local only)
./deployment/docker/build.sh all latest

# Build specific service
./deployment/docker/build.sh backend latest

# Build with custom tag
./deployment/docker/build.sh all v1.0.0

# Build and push to Docker Hub
PUSH=true ./deployment/docker/build.sh all latest

# Build specific service and push
PUSH=true ./deployment/docker/build.sh backend v1.0.0
```

### Environment Variables
```bash
# Custom registry (default: sagerstack)
export REGISTRY=myusername

# Push after build
export PUSH=true

# Custom tag
export TAG=v1.2.3

# Then run build
./deployment/docker/build.sh all
```

## 📋 Repository Structure

### Expected Repository Names
```
sagerstack/
├── ml-emotion-backend/
│   ├── latest
│   ├── v1.0.0
│   └── dev
├── ml-emotion-frontend/
│   ├── latest
│   ├── v1.0.0
│   └── dev
└── ml-emotion-streamlit/
    ├── latest
    ├── v1.0.0
    └── dev
```

### Image Naming Convention
- **Development**: `sagerstack/ml-emotion-{service}:dev`
- **Staging**: `sagerstack/ml-emotion-{service}:staging`
- **Production**: `sagerstack/ml-emotion-{service}:v{major}.{minor}.{patch}`

## 🚀 Build and Push Workflow

### 1. Development Workflow
```bash
# Build and push development images
PUSH=true ./deployment/docker/build.sh all dev

# Tag with git commit hash for tracking
COMMIT_HASH=$(git rev-parse --short HEAD)
PUSH=true ./deployment/docker/build.sh backend dev-${COMMIT_HASH}
```

### 2. Production Release Workflow
```bash
# Get current version from pyproject.toml
VERSION=$(grep "^version" backend/pyproject.toml | cut -d'"' -f2)

# Build and push production images
PUSH=true ./deployment/docker/build.sh all v${VERSION}

# Verify images pushed
docker pull sagerstack/ml-emotion-backend:v${VERSION}
docker pull sagerstack/ml-emotion-frontend:v${VERSION}
docker pull sagerstack/ml-emotion-streamlit:v${VERSION}
```

### 3. Incremental Updates
```bash
# Update single service
PUSH=true ./deployment/docker/build.sh backend latest

# Update only frontend
PUSH=true ./deployment/docker/build.sh frontend v1.1.0

# Update only streamlit
PUSH=true ./deployment/docker/build.sh streamlit latest
```

## 🧪 Testing Before Push

### Local Testing
```bash
# Build locally first
./deployment/docker/build.sh backend latest

# Test the image locally
docker run -p 8000:8000 sagerstack/ml-emotion-backend:latest

# Test health endpoint
curl http://localhost:8000/health
```

### Multi-Architecture Builds (Advanced)
```bash
# Enable experimental features for buildx
export DOCKER_CLI_EXPERIMENTAL=enabled

# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t sagerstack/ml-emotion-backend:latest \
  -f deployment/docker/backend/Dockerfile .
```

## 🔄 Automation Scripts

### Build and Push Script
Create `scripts/push-to-docker-hub.sh`:
```bash
#!/bin/bash

set -e

# Configuration
SERVICE=${1:-all}
TAG=${2:-latest}
PUSH=${PUSH:-true}
REGISTRY=${REGISTRY:-sagerstack}

echo "🐳 Building and pushing Docker images to Docker Hub"
echo "Service: $SERVICE"
echo "Tag: $TAG"
echo "Registry: $REGISTRY"
echo "Push: $PUSH"
echo ""

# Execute build script
PUSH=$PUSH ./deployment/docker/build.sh $SERVICE $TAG

echo ""
echo "✅ Docker Hub deployment completed!"
echo ""
echo "📋 Available images:"
echo "- sagerstack/ml-emotion-backend:$TAG"
echo "- sagerstack/ml-emotion-frontend:$TAG"
echo "- sagerstack/ml-emotion-streamlit:$TAG"
echo ""
echo "🔗 Docker Hub: https://hub.docker.com/u/sagerstack"
```

### Release Script
Create `scripts/release.sh`:
```bash
#!/bin/bash

set -e

VERSION=$1
if [ -z "$VERSION" ]; then
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 1.0.0"
    exit 1
fi

echo "🚀 Releasing version $VERSION"

# Check if git is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Git working directory is not clean"
    exit 1
fi

# Create release tag
git tag -a "v$VERSION" -m "Release version $VERSION"

# Build and push images
PUSH=true ./deployment/docker/build.sh all "v$VERSION"

# Push git tag
git push origin "v$VERSION"

echo "✅ Release $VERSION completed!"
```

## 📊 Monitoring and Validation

### Verify Images in Docker Hub
```bash
# List pulled images
docker images | grep sagerstack

# Pull and test specific image
docker pull sagerstack/ml-emotion-backend:latest
docker run --rm sagerstack/ml-emotion-backend:latest python --version

# Check image sizes
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep sagerstack
```

### Clean Up Local Images
```bash
# Remove old local images
docker image prune -f

# Remove specific images
docker rmi sagerstack/ml-emotion-backend:old-tag
docker rmi $(docker images "sagerstack/*" -q)
```

## 🔒 Security Best Practices

### 1. Use Personal Access Tokens
```bash
# Generate token in Docker Hub settings
# Use token instead of password for CI/CD
docker login --username sagerstack --password-stdin < token.txt
```

### 2. Repository Privacy
```bash
# Keep repositories public for now
# Consider private repositories for production
# Private repositories require Docker Hub Pro/Team plan
```

### 3. Image Scanning
```bash
# Use Docker Scout for security scanning
docker scout cves sagerstack/ml-emotion-backend:latest

# Or use third-party scanning
trivy image sagerstack/ml-emotion-backend:latest
```

## 🐛 Troubleshooting

### Common Issues

#### Login Issues
```bash
# Clear Docker credentials
rm ~/.docker/config.json

# Re-login
docker login

# Check login status
docker info | grep Username
```

#### Push Failures
```bash
# Check if image exists locally
docker images | grep sagerstack

# Re-tag if needed
docker tag ml-emotion-backend:latest sagerstack/ml-emotion-backend:latest

# Check network connectivity
ping hub.docker.com
```

#### Permission Denied
```bash
# Check repository permissions
# Ensure you have push access to sagerstack organization

# Verify username
docker info | grep Username
# Should show: Username: sagerstack
```

#### Build Failures
```bash
# Check build logs
./deployment/docker/build.sh backend latest 2>&1 | tee build.log

# Debug specific Dockerfile
docker build -f deployment/docker/backend/Dockerfile .

# Check disk space
df -h
docker system df
```

## 📋 Checklist Before Production

### Pre-Release Checklist
- [ ] Docker Hub login successful
- [ ] All images build locally without errors
- [ ] Health checks pass on all images
- [ ] Images tagged with correct version
- [ ] Repository names follow convention
- [ ] Image sizes are reasonable
- [ ] Security scan completed
- [ ] Documentation updated

### Release Checklist
- [ ] Git working directory clean
- [ ] Version tagged in git
- [ ] All images pushed to Docker Hub
- [ ] Images verified by pulling
- [ ] Release notes documented
- [ ] CI/CD pipeline tested
- [ ] Rollback plan documented

## 🔗 Integration

### Kubernetes Integration
```yaml
# Update Kubernetes manifests to use Docker Hub images
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  template:
    spec:
      containers:
      - name: backend
        image: sagerstack/ml-emotion-backend:latest  # Updated
        imagePullPolicy: Always
```

### Docker Compose Integration
```yaml
# Update docker-compose.yml for production
version: '3.8'
services:
  backend:
    image: sagerstack/ml-emotion-backend:latest  # Updated
    pull_policy: always
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Build and Push Docker Images
  run: |
    echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
    PUSH=true ./deployment/docker/build.sh all ${{ github.ref_name }}
```

## 🎯 Success Criteria

Your Docker Hub deployment is successful when:

✅ **Authentication**: Successfully logged into Docker Hub as `sagerstack`
✅ **Image Building**: All services build without errors
✅ **Image Pushing**: Images pushed to correct repositories
✅ **Verification**: Can pull and run images from Docker Hub
✅ **Tagging**: Consistent versioning across all images
✅ **Documentation**: Updated build scripts and documentation
✅ **Integration**: Kubernetes and Docker Compose updated to use Docker Hub images

## 🆘 Support

For Docker Hub related issues:
- **Docker Hub Documentation**: https://docs.docker.com/docker-hub/
- **Docker CLI Reference**: https://docs.docker.com/engine/reference/commandline/
- **Troubleshooting**: Check Docker Desktop logs and build output

Congratulations! You now have a complete Docker Hub deployment pipeline for the ML Speech Emotion Recognition application! 🐳🚀