#!/bin/bash
# Monitoring Dashboard Access Script
# Creates kubectl port-forwards for all monitoring services

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Starting Monitoring Dashboard Access"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if kubectl is configured
if ! kubectl get nodes &>/dev/null; then
    echo "❌ Error: kubectl is not configured or cannot connect to cluster"
    exit 1
fi

# Check if monitoring namespace exists
if ! kubectl get namespace monitoring &>/dev/null; then
    echo "❌ Error: monitoring namespace does not exist"
    exit 1
fi

# Function to start port-forward
start_port_forward() {
    local service=$1
    local port=$2
    local name=$3

    echo "🔗 Starting port-forward for ${name}..."
    kubectl port-forward -n monitoring svc/${service} ${port}:${port} > /dev/null 2>&1 &
    local pid=$!
    echo "   PID: ${pid}"
    sleep 1

    # Check if port-forward is still running
    if ps -p ${pid} > /dev/null 2>&1; then
        echo "   ✓ ${name} accessible at http://localhost:${port}"
    else
        echo "   ✗ Failed to start port-forward for ${name}"
    fi
    echo ""
}

# Start port-forwards
start_port_forward "grafana" "3000" "Grafana"
start_port_forward "prometheus" "9090" "Prometheus"
start_port_forward "loki" "3100" "Loki"
start_port_forward "tempo" "3200" "Tempo"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All monitoring services are now accessible!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Access URLs:"
echo ""
echo "   🔍 Grafana (Main Dashboard):"
echo "      → http://localhost:3000"
echo "      → Credentials: admin/admin"
echo ""
echo "   📈 Prometheus (Metrics):"
echo "      → http://localhost:9090"
echo ""
echo "   📋 Loki (Logs):"
echo "      → http://localhost:3100"
echo ""
echo "   🔗 Tempo (Distributed Tracing):"
echo "      → http://localhost:3200"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "ℹ️  Port-forwards are running in the background"
echo "   To stop them, run: pkill -f 'kubectl port-forward.*monitoring'"
echo ""
echo "   To view running port-forwards:"
echo "   ps aux | grep 'kubectl port-forward.*monitoring'"
echo ""
