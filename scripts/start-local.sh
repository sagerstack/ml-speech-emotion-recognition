#!/bin/bash

# 🚀 ML Speech Emotion Recognition - Local Development Startup Script
# Strategy 1: Local Execution (Native Development)

set -e  # Exit on any error

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

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1

    print_status "Waiting for $service_name to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        print_status "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 2
        ((attempt++))
    done

    print_error "$service_name failed to start within $max_attempts attempts"
    return 1
}

# Main script starts here
print_status "🎭 Starting ML Speech Emotion Recognition - Local Development"
echo "================================================================"

# Check if we're in the right directory
if [ ! -f "backend/pyproject.toml" ] || [ ! -f "frontend/streamlit_app/app.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check for required dependencies
print_status "Checking dependencies..."

# Check Python
if ! command -v python3.11 &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3.11+ is required but not installed"
        exit 1
    else
        print_warning "Python 3.11 not found, using $(python3 --version)"
    fi
fi

# Check Poetry
if ! command -v poetry &> /dev/null; then
    print_error "Poetry is required but not installed"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js is required but not installed"
    exit 1
fi

# Check npm
if ! command -v npm &> /dev/null; then
    print_error "npm is required but not installed"
    exit 1
fi

print_success "All dependencies are available"

# Check if ports are available
print_status "Checking port availability..."

PORTS=(8000 8501 3000)
for port in "${PORTS[@]}"; do
    if check_port $port; then
        print_warning "Port $port is already in use. Attempting to free it..."
        # Find and kill process using the port
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
        if check_port $port; then
            print_error "Could not free port $port. Please stop the process using it manually."
            exit 1
        fi
    fi
done

print_success "All required ports are available"

# Start Backend API
print_status "🔧 Starting Backend API..."
cd backend

# Check if poetry environment exists
if ! poetry env info >/dev/null 2>&1; then
    print_status "Creating Poetry environment..."
    poetry install
fi

# Start backend in background
print_status "Starting FastAPI backend on port 8000..."
poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

cd ..
print_success "Backend API started (PID: $BACKEND_PID)"

# Wait for backend to be ready
wait_for_service "http://localhost:8000/health" "Backend API"

# Start Streamlit App
print_status "🎭 Starting Streamlit ML Interface..."
cd frontend/streamlit_app

# Install Streamlit dependencies if needed
if [ ! -d "venv" ] && [ ! -f ".venv/bin/activate" ]; then
    print_status "Installing Streamlit dependencies..."
    pip install -r requirements.txt 2>/dev/null || poetry run pip install -r requirements.txt
fi

# Start Streamlit in background
print_status "Starting Streamlit app on port 8501..."
# Try different methods to start Streamlit
if command -v poetry &> /dev/null && [ -f "../../backend/pyproject.toml" ]; then
    poetry run streamlit run app.py --server.headless=true --server.port=8501 &
else
    streamlit run app.py --server.headless=true --server.port=8501 &
fi
STREAMLIT_PID=$!

cd ../..
print_success "Streamlit app started (PID: $STREAMLIT_PID)"

# Wait for Streamlit to be ready
wait_for_service "http://localhost:8501/_stcore/health" "Streamlit app"

# Note: React dashboard is now integrated into Streamlit, so we don't start it separately
print_warning "React dashboard has been integrated into the Streamlit app"
print_status "Access all features via http://localhost:8501"

# Save PIDs to file for cleanup
cat > .local_pids.txt << EOF
BACKEND_PID=$BACKEND_PID
STREAMLIT_PID=$STREAMLIT_PID
EOF

echo "================================================================"
print_success "🎉 All services started successfully!"
echo ""
echo "📊 Access the application:"
echo "   🎭 ML Interface: http://localhost:8501"
echo "   📊 Dashboard: http://localhost:8501 (Dashboard tab)"
echo "   ⚙️ Settings: http://localhost:8501 (Settings tab)"
echo "   🔗 API Docs: http://localhost:8000/docs"
echo ""
echo "🛑 To stop all services, run: ./scripts/stop-local.sh"
echo "🔍 To check status, run: ./scripts/check-local.sh"
echo ""
print_status "Enjoy using the ML Speech Emotion Recognition application! 🚀"