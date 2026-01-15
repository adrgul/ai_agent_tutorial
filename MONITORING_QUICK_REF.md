# Monitoring Quick Reference Card

## 🎯 For Developers: How to Use the Monitoring System

### Basic Usage

#### 1. Instrument LLM Calls
```python
from observability.llm_instrumentation import instrumented_llm_call

response = await instrumented_llm_call(
    llm=your_llm,
    messages=messages,
    model="gpt-4o-mini",
    agent_execution_id="exec_123"  # optional
)
```

#### 2. Track State Snapshots
```python
from observability.state_tracker import get_state_tracker

tracker = get_state_tracker()

# Before execution
tracker.snapshot_before_execution("exec_123", initial_state)

# After node
tracker.snapshot_after_node("exec_123", "agent_decide", state)

# After completion
tracker.snapshot_after_completion("exec_123", final_state)
```

#### 3. Use Model Fallback
```python
from observability.llm_instrumentation import instrumented_llm_call_with_fallback

response = await instrumented_llm_call_with_fallback(
    primary_llm=gpt4_llm,
    fallback_llm=gpt3_llm,
    messages=messages,
    primary_model="gpt-4o",
    fallback_model="gpt-3.5-turbo",
    max_retries=2
)
```

#### 4. Record Tool Calls
```python
from observability.metrics import tool_invocation_count

tool_invocation_count.labels(tool="weather").inc()
```

---

## 📊 Key Metrics to Watch

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| `llm_cost_total_usd` | Track spending | > $100/day |
| `model_fallback_count` | Reliability issues | > 10/hour |
| `agent_execution_latency_seconds` | Performance | p95 > 30s |
| `tool_failure_count` | Integration health | rate > 0.1 |
| `max_retries_exceeded_count` | System stress | > 5/hour |

---

## 🔍 Quick Prometheus Queries

### Cost
```promql
# Hourly cost
increase(llm_cost_total_usd[1h])

# Cost by model
sum by (model) (llm_cost_total_usd)
```

### Performance
```promql
# Agent p95 latency
histogram_quantile(0.95, rate(agent_execution_latency_seconds_bucket[5m]))

# Slowest nodes
topk(5, rate(node_execution_latency_seconds_sum[5m]))
```

### Reliability
```promql
# Fallback rate
rate(model_fallback_count[5m])

# Error rate
rate(agent_error_count[5m])
```

---

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up --build

# View logs
docker-compose logs -f backend
docker-compose logs -f prometheus
docker-compose logs -f grafana

# Restart service
docker-compose restart grafana

# Stop all
docker-compose down
```

---

## 🌐 Service URLs

- **Backend API**: http://localhost:8001
- **Metrics**: http://localhost:8001/metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

---

## 🔧 Environment Variables

```bash
# Enable/disable metrics
ENABLE_METRICS=true

# Environment label
ENVIRONMENT=dev

# Tenant ID (optional)
TENANT_ID=default
```

---

## 📈 Dashboard Access

1. Open Grafana: http://localhost:3001
2. Login: admin/admin
3. Navigate to: Dashboards → AI Agent folder
4. Available dashboards:
   - LLM Dashboard
   - Agent Workflow Dashboard
   - RAG Dashboard
   - Cost Dashboard

---

## 🧪 Testing

```bash
# Verify setup
./verify-monitoring.sh

# Check metrics endpoint
curl http://localhost:8001/metrics

# Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=llm_cost_total_usd'
```

---

## 🚨 Troubleshooting

### Metrics not appearing?
1. Check `ENABLE_METRICS=true` in environment
2. Verify `/metrics` endpoint: `curl http://localhost:8001/metrics`
3. Check Prometheus targets: http://localhost:9090/targets

### Dashboards not loading?
1. Verify dashboard files exist in `observability/grafana/dashboards/`
2. Restart Grafana: `docker-compose restart grafana`
3. Check logs: `docker-compose logs grafana`

### High costs?
1. Check token usage: `increase(llm_inference_token_input_total[1h])`
2. Identify expensive models: `topk(3, llm_cost_total_usd)`
3. Review prompt sizes and frequency

---

## 📚 Full Documentation

- **Implementation Guide**: `observability/MONITORING_IMPLEMENTATION.md`
- **Summary**: `MONITORING_SUMMARY.md`
- **Code**: `backend/observability/`
