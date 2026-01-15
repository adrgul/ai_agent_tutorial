#!/bin/bash

# Monitoring Implementation Verification Script
# Verifies that all observability components are properly configured

echo "🔍 Monitoring Implementation Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS_COUNT++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL_COUNT++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "1. Checking observability modules..."
echo "-----------------------------------"

# Check metrics.py
if [ -f "backend/observability/metrics.py" ]; then
    check_pass "metrics.py exists"
    
    # Check for required metrics
    if grep -q "llm_inference_count" backend/observability/metrics.py; then
        check_pass "llm_inference_count metric defined"
    else
        check_fail "llm_inference_count metric not found"
    fi
    
    if grep -q "model_fallback_count" backend/observability/metrics.py; then
        check_pass "model_fallback_count metric defined"
    else
        check_fail "model_fallback_count metric not found"
    fi
    
    if grep -q "rag_chunk_retrieval_count" backend/observability/metrics.py; then
        check_pass "rag_chunk_retrieval_count metric defined"
    else
        check_fail "rag_chunk_retrieval_count metric not found"
    fi
else
    check_fail "metrics.py not found"
fi

# Check prompt_lineage.py
if [ -f "backend/observability/prompt_lineage.py" ]; then
    check_pass "prompt_lineage.py exists"
else
    check_fail "prompt_lineage.py not found"
fi

# Check state_tracker.py
if [ -f "backend/observability/state_tracker.py" ]; then
    check_pass "state_tracker.py exists"
else
    check_fail "state_tracker.py not found"
fi

# Check llm_instrumentation.py
if [ -f "backend/observability/llm_instrumentation.py" ]; then
    check_pass "llm_instrumentation.py exists"
    
    if grep -q "instrumented_llm_call_with_fallback" backend/observability/llm_instrumentation.py; then
        check_pass "Fallback instrumentation implemented"
    else
        check_fail "Fallback instrumentation not found"
    fi
else
    check_fail "llm_instrumentation.py not found"
fi

echo ""
echo "2. Checking Grafana dashboards..."
echo "---------------------------------"

# Check for 4 required dashboards
DASHBOARDS=(
    "observability/grafana/dashboards/llm_dashboard.json"
    "observability/grafana/dashboards/agent_workflow_dashboard.json"
    "observability/grafana/dashboards/rag_dashboard.json"
    "observability/grafana/dashboards/cost_dashboard.json"
)

for dashboard in "${DASHBOARDS[@]}"; do
    if [ -f "$dashboard" ]; then
        check_pass "$(basename $dashboard) exists"
    else
        check_fail "$(basename $dashboard) not found"
    fi
done

echo ""
echo "3. Checking Docker configuration..."
echo "-----------------------------------"

# Check docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    check_pass "docker-compose.yml exists"
    
    if grep -q "prometheus:" docker-compose.yml; then
        check_pass "Prometheus service configured"
    else
        check_fail "Prometheus service not found"
    fi
    
    if grep -q "grafana:" docker-compose.yml; then
        check_pass "Grafana service configured"
    else
        check_fail "Grafana service not found"
    fi
else
    check_fail "docker-compose.yml not found"
fi

# Check Prometheus config
if [ -f "observability/prometheus.yml" ]; then
    check_pass "prometheus.yml exists"
    
    if grep -q "ai-agent-backend:8000" observability/prometheus.yml; then
        check_pass "Backend scrape target configured"
    else
        check_fail "Backend scrape target not configured"
    fi
else
    check_fail "prometheus.yml not found"
fi

# Check Grafana provisioning
if [ -f "observability/grafana/provisioning/dashboards/dashboards.yml" ]; then
    check_pass "Grafana dashboard provisioning configured"
else
    check_fail "Grafana dashboard provisioning not configured"
fi

echo ""
echo "4. Checking documentation..."
echo "---------------------------"

if [ -f "observability/MONITORING_IMPLEMENTATION.md" ]; then
    check_pass "MONITORING_IMPLEMENTATION.md exists"
else
    check_fail "MONITORING_IMPLEMENTATION.md not found"
fi

if [ -f "docs/09_MONITORING_PROMPT.md" ]; then
    check_pass "Original specification exists"
else
    check_warn "Original specification not found"
fi

echo ""
echo "5. Checking requirements..."
echo "---------------------------"

if [ -f "backend/requirements.txt" ]; then
    check_pass "requirements.txt exists"
    
    if grep -q "prometheus" backend/requirements.txt; then
        check_pass "prometheus_client dependency listed"
    else
        check_fail "prometheus_client dependency not found"
    fi
else
    check_fail "requirements.txt not found"
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}${PASS_COUNT}${NC}"
echo -e "Failed: ${RED}${FAIL_COUNT}${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Start the services: docker-compose up --build"
    echo "2. Access Prometheus: http://localhost:9090"
    echo "3. Access Grafana: http://localhost:3001 (admin/admin)"
    echo "4. Check metrics endpoint: http://localhost:8001/metrics"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the output above.${NC}"
    exit 1
fi
