#!/bin/bash
# Stop all monitoring port-forwards

echo "🛑 Stopping all monitoring port-forwards..."
echo ""

# Find and kill all kubectl port-forward processes for monitoring namespace
pkill -f 'kubectl port-forward.*monitoring' && echo "✓ All monitoring port-forwards stopped" || echo "ℹ️  No monitoring port-forwards were running"
