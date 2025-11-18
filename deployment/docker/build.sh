#!/bin/bash

# Docker build script for ML Speech Emotion Recognition
# Usage: ./build.sh [service] [tag] [push]
# Services: backend, frontend, streamlit, all
# Tag: optional, defaults to latest
# Push: optional, set to 'true' to push to Docker Hub (PUSH=true ./build.sh backend latest)
# Examples:
#   ./build.sh all latest
#   ./build.sh backend v1.0.0
#   PUSH=true ./build.sh backend latest
#   REGISTRY=myuser ./build.sh all latest

set -e

# Default values
SERVICE=${1:-all}
TAG=${2:-latest}
REGISTRY=${REGISTRY:-sagerstack}
PUSH=${PUSH:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🐳 Building Docker images for ML Speech Emotion Recognition${NC}"
echo -e "${GREEN}==============================================${NC}"

# Function to build a service
build_service() {
    local service=$1
    local dockerfile_path=""
    local image_name=""

    echo -e "${YELLOW}Building ${service}...${NC}"

    case $service in
        "backend")
            dockerfile_path="deployment/docker/backend/Dockerfile"
            image_name="${REGISTRY}/ml-speech-emotion-recognition-backend:${TAG}"
            ;;
        "frontend")
            dockerfile_path="deployment/docker/frontend/Dockerfile"
            image_name="${REGISTRY}/ml-speech-emotion-recognition-frontend:${TAG}"
            ;;
        "streamlit")
            dockerfile_path="deployment/docker/streamlit/Dockerfile"
            image_name="${REGISTRY}/ml-speech-emotion-recognition-streamlit:${TAG}"
            ;;
        *)
            echo -e "${RED}Unknown service: ${service}${NC}"
            echo "Available services: backend, frontend, streamlit, all"
            exit 1
            ;;
    esac

    echo "Building ${image_name}..."
    docker build \
        -f ${dockerfile_path} \
        -t ${image_name} \
        .

    echo -e "${GREEN}✅ Successfully built ${image_name}${NC}"
}

# Build based on service parameter
case $SERVICE in
    "all")
        echo -e "${YELLOW}Building all services...${NC}"
        build_service "backend"
        build_service "streamlit"
        build_service "frontend"

        # Show built images
        echo -e "${GREEN}📋 Built images:${NC}"
        docker images | grep ml-emotion-recognition | head -10
        ;;
    "backend"|"frontend"|"streamlit")
        build_service "$SERVICE"
        ;;
    *)
        echo -e "${RED}Invalid service: ${SERVICE}${NC}"
        echo "Usage: $0 [backend|frontend|streamlit|all] [tag]"
        echo "Example: $0 all v1.0.0"
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 Build completed successfully!${NC}"

# Tag images with additional tags if provided
if [ "$TAG" != "latest" ]; then
    echo -e "${YELLOW}Tagging images with 'latest' as well...${NC}"
    case $SERVICE in
        "all")
            docker tag ${REGISTRY}/ml-emotion-backend:${TAG} ${REGISTRY}/ml-emotion-backend:latest
            docker tag ${REGISTRY}/ml-emotion-streamlit:${TAG} ${REGISTRY}/ml-emotion-streamlit:latest
            docker tag ${REGISTRY}/ml-emotion-frontend:${TAG} ${REGISTRY}/ml-emotion-frontend:latest
            ;;
        "backend")
            docker tag ${REGISTRY}/ml-emotion-backend:${TAG} ${REGISTRY}/ml-emotion-backend:latest
            ;;
        "frontend")
            docker tag ${REGISTRY}/ml-emotion-frontend:${TAG} ${REGISTRY}/ml-emotion-frontend:latest
            ;;
        "streamlit")
            docker tag ${REGISTRY}/ml-emotion-streamlit:${TAG} ${REGISTRY}/ml-emotion-streamlit:latest
            ;;
    esac
fi

# Push images to Docker Hub if requested
if [ "$PUSH" = "true" ]; then
    echo -e "${YELLOW}📤 Pushing images to Docker Hub...${NC}"

    push_image() {
        local service=$1
        local image_name="${REGISTRY}/${service}:${TAG}"

        echo "Pushing ${image_name}..."
        docker push ${image_name}
        echo -e "${GREEN}✅ Successfully pushed ${image_name}${NC}"
    }

    case $SERVICE in
        "all")
            push_image "ml-emotion-backend"
            push_image "ml-emotion-streamlit"
            push_image "ml-emotion-frontend"
            ;;
        "backend")
            push_image "ml-emotion-backend"
            ;;
        "frontend")
            push_image "ml-emotion-frontend"
            ;;
        "streamlit")
            push_image "ml-emotion-streamlit"
            ;;
        *)
            echo -e "${RED}Unknown service: ${SERVICE}${NC}"
            exit 1
            ;;
    esac
fi

echo -e "${GREEN}🚀 Ready for deployment!${NC}"