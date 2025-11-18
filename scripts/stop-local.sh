#!/bin/bash

# 🛑 ML Speech Emotion Recognition - Local Development Stop Script
# Strategy 1: Local Execution (Native Development)

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

# Function to stop process by PID
stop_process() {
    local pid=$1
    local name=$2

    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        print_status "Stopping $name (PID: $pid)..."
        kill "$pid" 2>/dev/null || true

        # Wait for process to stop
        local count=0
        while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
            sleep 1
            ((count++))
        done

        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            print_warning "Force stopping $name..."
            kill -9 "$pid" 2>/dev/null || true
        fi

        print_success "$name stopped"
    else
        print_warning "$name was not running or PID not found"
    fi
}

# Function to stop processes by port
stop_by_port() {
    local port=$1
    local name=$2

    local pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        print_status "Stopping $name processes on port $port..."
        echo "$pids" | xargs kill 2>/dev/null || true
        sleep 2

        # Force kill if still running
        pids=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pids" ]; then
            print_warning "Force stopping $name on port $port..."
            echo "$pids" | xargs kill -9 2>/dev/null || true
        fi

        print_success "$name stopped on port $port"
    else
        print_warning "No $name processes found on port $port"
    fi
}

# Function to stop by process name
stop_by_name() {
    local name=$1
    local process_name=$2

    local pids=$(pgrep -f "$process_name" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        print_status "Stopping $name processes..."
        echo "$pids" | xargs kill 2>/dev/null || true
        sleep 2

        # Force kill if still running
        pids=$(pgrep -f "$process_name" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            print_warning "Force stopping $name processes..."
            echo "$pids" | xargs kill -9 2>/dev/null || true
        fi

        print_success "$name processes stopped"
    else
        print_warning "No $name processes found"
    fi
}

# Main script starts here
print_status "🛑 Stopping ML Speech Emotion Recognition - Local Development"
echo "================================================================"

# Check if we're in the right directory
if [ ! -f "backend/pyproject.toml" ] || [ ! -f "frontend/streamlit_app/app.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Method 1: Stop using saved PIDs
if [ -f ".local_pids.txt" ]; then
    print_status "Found PID file, stopping services using saved PIDs..."

    # Source the PID file
    source .local_pids.txt

    # Stop services
    stop_process "$BACKEND_PID" "Backend API"
    stop_process "$STREAMLIT_PID" "Streamlit App"

    # Remove PID file
    rm -f .local_pids.txt
else
    print_warning "No PID file found, stopping by port and process name..."

    # Method 2: Stop by port
    stop_by_port 8000 "Backend API"
    stop_by_port 8501 "Streamlit App"
    stop_by_port 3000 "React Dashboard"

    # Method 3: Stop by process name (backup method)
    stop_by_name "FastAPI" "uvicorn.*main:app"
    stop_by_name "Streamlit" "streamlit run"
    stop_by_name "React" "npm start"
    stop_by_name "React" "react-scripts start"
fi

# Additional cleanup
print_status "Performing additional cleanup..."

# Kill any remaining Python processes that might be related
python_pids=$(pgrep -f "ml.*speech.*emotion" 2>/dev/null || true)
if [ -n "$python_pids" ]; then
    print_status "Cleaning up remaining Python processes..."
    echo "$python_pids" | xargs kill -9 2>/dev/null || true
fi

# Clean up any temporary files
print_status "Cleaning up temporary files..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Verify all ports are free
print_status "Verifying all ports are free..."
PORTS=(8000 8501 3000)
all_free=true

for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port $port is still in use"
        all_free=false
    fi
done

if [ "$all_free" = true ]; then
    print_success "All ports are now free"
else
    print_warning "Some ports may still be in use. You may need to restart your terminal."
fi

echo "================================================================"
print_success "🎉 All services stopped successfully!"
echo ""
print_status "Local development environment has been cleaned up."
echo "To start services again, run: ./scripts/start-local.sh"
echo ""