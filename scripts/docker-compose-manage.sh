#!/bin/bash

# 🐳 ML Speech Emotion Recognition - Docker Compose Management Script
# Strategy 2: Docker Execution (Containerized Development)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 {start|stop|restart|status|logs|clean}"
    echo ""
    echo "Commands:"
    echo "  start   - Start all services with Docker Compose"
    echo "  stop    - Stop all services"
    echo "  restart - Restart all services"
    echo "  status  - Show service status"
    echo "  logs    - Show logs for all services"
    echo "  clean   - Clean up containers and images"
    echo ""
    echo "Examples:"
    echo "  $0 start              # Start all services"
    echo "  $0 logs backend       # Show logs for backend only"
    echo "  $0 logs streamlit     # Show logs for streamlit only"
    echo "  $0 clean --volumes    # Clean everything including volumes"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop or Docker daemon."
        exit 1
    fi
}

# Function to check if we're in the right directory
check_directory() {
    if [ ! -f "deployment/docker/docker-compose.yml" ]; then
        print_error "Please run this script from the project root directory"
        exit 1
    fi
}

# Function to start services
start_services() {
    print_status "🐳 Starting services with Docker Compose..."

    # Build images if they don't exist
    if ! docker images | grep -q "sagerstack/ml-emotion"; then
        print_status "Building Docker images first..."
        cd deployment/docker
        ./build.sh all latest
        cd ../..
    fi

    cd deployment/docker
    docker-compose up -d

    print_success "Services started successfully!"

    # Show service URLs
    echo ""
    print_status "📊 Access URLs:"
    echo "  🎭 Streamlit App: http://localhost:8501"
    echo "  🔗 Backend API: http://localhost:8000"
    echo "  📋 API Docs: http://localhost:8000/docs"
    echo ""

    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10

    # Check service health
    check_service_health

    cd ../..
}

# Function to stop services
stop_services() {
    print_status "🛑 Stopping Docker Compose services..."

    cd deployment/docker
    docker-compose down
    cd ../..

    print_success "All services stopped"
}

# Function to restart services
restart_services() {
    print_status "🔄 Restarting services..."
    stop_services
    sleep 2
    start_services
}

# Function to check service health
check_service_health() {
    print_status "🔍 Checking service health..."

    # Check backend
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_success "✓ Backend API is healthy"
    else
        print_warning "⚠ Backend API not ready yet"
    fi

    # Check streamlit
    if curl -s http://localhost:8501/_stcore/health >/dev/null 2>&1; then
        print_success "✓ Streamlit app is healthy"
    else
        print_warning "⚠ Streamlit app not ready yet"
    fi
}

# Function to show service status
show_status() {
    print_status "📊 Docker Compose Service Status"
    echo "======================================"

    cd deployment/docker

    # Show containers
    echo "Containers:"
    docker-compose ps

    echo ""
    echo "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" || true

    cd ../..

    echo ""
    check_service_health
}

# Function to show logs
show_logs() {
    local service=$1

    cd deployment/docker

    if [ -n "$service" ]; then
        print_status "📋 Showing logs for service: $service"
        docker-compose logs -f "$service"
    else
        print_status "📋 Showing logs for all services"
        docker-compose logs -f
    fi

    cd ../..
}

# Function to clean up
clean_up() {
    local clean_volumes=$1

    print_status "🧹 Cleaning up Docker resources..."

    cd deployment/docker

    # Stop and remove containers
    docker-compose down -v

    if [ "$clean_volumes" = "--volumes" ]; then
        print_warning "Removing volumes (this will delete all data)..."
        docker-compose down -v --remove-orphans
        docker volume prune -f
    fi

    # Remove images
    print_status "Removing application images..."
    docker images | grep "sagerstack/ml-emotion" | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true

    # Clean up unused resources
    docker system prune -f

    cd ../..

    print_success "Docker cleanup completed"
}

# Main script logic
case "${1:-}" in
    start)
        check_docker
        check_directory
        start_services
        ;;
    stop)
        check_docker
        check_directory
        stop_services
        ;;
    restart)
        check_docker
        check_directory
        restart_services
        ;;
    status)
        check_docker
        check_directory
        show_status
        ;;
    logs)
        check_docker
        check_directory
        show_logs "$2"
        ;;
    clean)
        check_docker
        check_directory
        clean_up "$2"
        ;;
    *)
        show_usage
        exit 1
        ;;
esac