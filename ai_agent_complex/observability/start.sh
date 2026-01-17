#!/bin/bash
# Quick start script for AI Agent Observability Stack
#
# This script:
# 1. Validates prerequisites
# 2. Starts Prometheus and Grafana
# 3. Waits for services to be ready
# 4. Displays access information

set -e

echo "🚀 Starting AI Agent Observability Stack..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi

# Check if backend is running (optional warning)
if ! curl -s http://localhost:8000/metrics > /dev/null 2>&1; then
    echo "⚠️  Warning: Backend not running on http://localhost:8000"
    echo "   Metrics endpoint will not be available until backend starts"
    echo ""
fi

# Start services
echo "📦 Starting Prometheus and Grafana..."
docker-compose up -d

# Wait for services
echo ""
echo "⏳ Waiting for services to be ready..."

# Wait for Prometheus
echo -n "   Waiting for Prometheus..."
for i in {1..30}; do
    if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 1
done

# Wait for Grafana
echo -n "   Waiting for Grafana..."
for i in {1..30}; do
    if curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
        echo " ✅"
        break
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "✅ Observability stack is ready!"
echo ""
echo "📊 Access Points:"
echo "   Grafana:    http://localhost:3001  (admin/admin)"
echo "   Prometheus: http://localhost:9090"
echo "   Metrics:    http://localhost:8000/metrics"
echo ""
echo "📈 Next Steps:"
echo "   1. Open Grafana: http://localhost:3001"
echo "   2. Login with admin/admin"
echo "   3. Navigate to Dashboards → AI Agent → AI Agent - Overview"
echo "   4. Generate some traffic to see metrics"
echo ""
echo "🛑 To stop: docker-compose down"
echo ""
