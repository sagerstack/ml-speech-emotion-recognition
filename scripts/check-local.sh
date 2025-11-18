#!/bin/bash

# 🔍 ML Speech Emotion Recognition - Local Development Status Check Script
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

# Function to check if a service is running on a port
check_service_port() {
    local port=$1
    local service_name=$2
    local url=$3

    echo -n "  $service_name (port $port): "

    # Check if port is in use
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        # Test HTTP endpoint if provided
        if [ -n "$url" ]; then
            if curl -s --max-time 5 "$url" >/dev/null 2>&1; then
                echo -e "${GREEN}✓ Running${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠ Port in use but not responding${NC}"
                return 1
            fi
        else
            echo -e "${GREEN}✓ Running${NC}"
            return 0
        fi
    else
        echo -e "${RED}✗ Stopped${NC}"
        return 1
    fi
}

# Function to check process by name
check_process() {
    local process_name=$1
    local display_name=$2

    echo -n "  $display_name: "

    if pgrep -f "$process_name" >/dev/null 2>&1; then
        local count=$(pgrep -f "$process_name" | wc -l)
        echo -e "${GREEN}✓ Running ($count processes)${NC}"
        return 0
    else
        echo -e "${RED}✗ Stopped${NC}"
        return 1
    fi
}

# Function to test API endpoint
test_api_endpoint() {
    local url=$1
    local service_name=$2

    echo -n "  Testing $service_name API: "

    if curl -s --max-time 10 "$url" >/dev/null 2>&1; then
        local response_time=$(curl -o /dev/null -s -w '%{time_total}' --max-time 10 "$url" 2>/dev/null || echo "0")
        if (( $(echo "$response_time > 0" | bc -l) )); then
            echo -e "${GREEN}✓ OK (${response_time}s)${NC}"
        else
            echo -e "${GREEN}✓ OK${NC}"
        fi
        return 0
    else
        echo -e "${RED}✗ Failed${NC}"
        return 1
    fi
}

# Function to show system resources
show_system_resources() {
    print_status "System Resources:"

    # CPU usage
    if command -v top >/dev/null 2>&1; then
        local cpu_usage=$(top -l 1 -n 0 | grep "CPU usage" | awk '{print $3}' | sed 's/%//' 2>/dev/null || echo "N/A")
        echo "  CPU Usage: ${cpu_usage}%"
    fi

    # Memory usage
    if command -v free >/dev/null 2>&1; then
        local mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}' 2>/dev/null || echo "N/A")
    elif command -v vm_stat >/dev/null 2>&1; then
        # macOS
        local page_size=$(vm_stat | head -1 | sed 's/.*page size of \([0-9]*\).*/\1/')
        local free_pages=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
        local active_pages=$(vm_stat | grep "Pages active" | awk '{print $3}' | sed 's/\.//')
        local inactive_pages=$(vm_stat | grep "Pages inactive" | awk '{print $3}' | sed 's/\.//')
        local wired_pages=$(vm_stat | grep "Pages wired down" | awk '{print $4}' | sed 's/\.//')
        local total_pages=$((free_pages + active_pages + inactive_pages + wired_pages))
        local used_pages=$((active_pages + inactive_pages + wired_pages))
        local mem_usage=$(echo "scale=1; $used_pages * 100 / $total_pages" | bc -l 2>/dev/null || echo "N/A")
    else
        local mem_usage="N/A"
    fi
    echo "  Memory Usage: ${mem_usage}%"

    # Disk usage
    if command -v df >/dev/null 2>&1; then
        local disk_usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//' 2>/dev/null || echo "N/A")
        echo "  Disk Usage: ${disk_usage}%"
    fi
}

# Main script starts here
print_status "🔍 ML Speech Emotion Recognition - Local Development Status"
echo "================================================================"

# Check if we're in the right directory
if [ ! -f "backend/pyproject.toml" ] || [ ! -f "frontend/streamlit_app/app.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check dependency versions
print_status "Dependency Versions:"
echo "  Python: $(python3 --version 2>/dev/null || python --version 2>/dev/null || echo 'Not found')"
echo "  Poetry: $(poetry --version 2>/dev/null || echo 'Not found')"
echo "  Node.js: $(node --version 2>/dev/null || echo 'Not found')"
echo "  npm: $(npm --version 2>/dev/null || echo 'Not found')"
echo ""

# Check service ports
print_status "Service Status:"
check_service_port 8000 "Backend API" "http://localhost:8000/health"
check_service_port 8501 "Streamlit App" "http://localhost:8501/_stcore/health"

# Note: React is now integrated into Streamlit
echo "  React Dashboard: ${YELLOW}ℹ️ Integrated into Streamlit app${NC}"
echo ""

# Check process status
print_status "Process Status:"
check_process "uvicorn.*main:app" "FastAPI Backend"
check_process "streamlit run" "Streamlit"
# Check for old React process (should not be running)
if pgrep -f "react-scripts start" >/dev/null 2>&1; then
    echo -e "  React Dev Server: ${YELLOW}⚠ Running (should be stopped - now integrated)${NC}"
else
    echo "  React Dev Server: ${GREEN}✓ Stopped (correctly integrated)${NC}"
fi
echo ""

# Test API endpoints if services are running
if check_service_port 8000 "" ""; then
    print_status "API Endpoint Tests:"
    test_api_endpoint "http://localhost:8000/health" "Backend Health"
    test_api_endpoint "http://localhost:8000" "Backend Root"
    echo ""
fi

if check_service_port 8501 "" ""; then
    print_status "Streamlit Endpoint Tests:"
    test_api_endpoint "http://localhost:8501/_stcore/health" "Streamlit Health"
    test_api_endpoint "http://localhost:8501" "Streamlit Root"
    echo ""
fi

# Show saved PIDs if available
if [ -f ".local_pids.txt" ]; then
    print_status "Saved Process IDs:"
    cat .local_pids.txt | while read line; do
        if [[ $line =~ ^[A-Z_]+_PID= ]]; then
            local service_name=$(echo "$line" | cut -d'=' -f1 | sed 's/_PID$//')
            local pid=$(echo "$line" | cut -d'=' -f2)
            echo -n "  $service_name: $pid - "
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${GREEN}Running${NC}"
            else
                echo -e "${RED}Not running${NC}"
            fi
        fi
    done
    echo ""
fi

# Show system resources
show_system_resources
echo ""

# Show access URLs
print_status "Access URLs:"
echo "  🎭 ML Interface: http://localhost:8501"
echo "  📊 Dashboard: http://localhost:8501 (Dashboard tab)"
echo "  ⚙️ Settings: http://localhost:8501 (Settings tab)"
echo "  🔗 API Docs: http://localhost:8000/docs"

# Overall status summary
echo ""
echo "================================================================"

# Count running services
running_services=0
total_services=2  # Backend + Streamlit (React is integrated)

if check_service_port 8000 "" ""; then
    ((running_services++))
fi

if check_service_port 8501 "" ""; then
    ((running_services++))
fi

echo -n "Overall Status: "
if [ $running_services -eq $total_services ]; then
    echo -e "${GREEN}✓ All services running${NC}"
    echo ""
    print_success "🎉 Your local development environment is fully operational!"
elif [ $running_services -gt 0 ]; then
    echo -e "${YELLOW}⚠ Partially running ($running_services/$total_services services)${NC}"
    echo ""
    print_warning "Some services may need attention. Check the details above."
else
    echo -e "${RED}✗ All services stopped${NC}"
    echo ""
    print_error "No services are currently running."
    echo "To start services, run: ./scripts/start-local.sh"
fi

echo ""
print_status "For management commands:"
echo "  Start services: ./scripts/start-local.sh"
echo "  Stop services:  ./scripts/stop-local.sh"
echo "  Check status:   ./scripts/check-local.sh"
echo ""