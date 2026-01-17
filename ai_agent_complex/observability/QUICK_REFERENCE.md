# AI Agent Observability - Quick Reference

## 🎯 Essential Commands

### Start Everything
```bash
# Backend
cd backend && uvicorn main:app --reload --port 8000

# Observability Stack
cd observability && ./start.sh
```

### Access URLs
- **Backend**: http://localhost:8000
- **Metrics**: http://localhost:8000/metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

### Stop Everything
```bash
cd observability && docker-compose down
```

## 📊 Key Metrics

| Metric | What It Measures | Use Case |
|--------|------------------|----------|
| `agent_requests_total` | Request count (success/error) | Track request volume, error rate |
| `agent_request_duration_seconds` | End-to-end latency | Monitor performance, SLA compliance |
| `agent_llm_tokens_total` | Token usage by model | Optimize prompts, track usage |
| `agent_llm_cost_usd_total` | Estimated LLM costs | Budget tracking, cost optimization |
| `agent_node_duration_seconds` | Node execution time | Find bottlenecks in workflow |
| `agent_tool_calls_total` | Tool usage (success/error) | Monitor external integrations |
| `agent_errors_total` | Error count by type | Debug failures, set alerts |

## 🔍 Useful PromQL Queries

### Performance
```promql
# 95th percentile latency (last 5 min)
histogram_quantile(0.95, sum(rate(agent_request_duration_seconds_bucket[5m])) by (le))

# Requests per second
rate(agent_requests_total[5m])

# Error rate percentage
sum(rate(agent_requests_total{status="error"}[5m])) 
/ 
sum(rate(agent_requests_total[5m])) * 100
```

### Costs
```promql
# Total cost (cumulative)
sum(agent_llm_cost_usd_total)

# Cost per hour
sum(rate(agent_llm_cost_usd_total[1h]) * 3600) by (model)

# Tokens per request
sum(rate(agent_llm_tokens_total[5m])) / sum(rate(agent_requests_total[5m]))
```

### Debugging
```promql
# Slowest node
topk(1, sum(rate(agent_node_duration_seconds_sum[5m])) by (node))

# Most called tool
topk(1, sum(rate(agent_tool_calls_total[5m])) by (tool))

# Error spike detection
delta(agent_errors_total[5m]) > 10
```

## 🏷️ Environment Variables

```bash
# Enable/disable metrics
ENABLE_METRICS=true

# Environment label
ENVIRONMENT=dev|staging|prod

# Tenant identifier
TENANT_ID=default

# App version
APP_VERSION=1.0.0
```

## 🔧 Common Tasks

### Add Custom Metric

1. **Define** in `backend/observability/metrics.py`:
```python
my_metric = Counter('agent_my_metric_total', 'Description', ['label1'])
```

2. **Record** in code:
```python
from observability.metrics import my_metric
my_metric.labels(label1="value").inc()
```

3. **Query** in Prometheus:
```promql
rate(agent_my_metric_total[5m])
```

### Debug Request Flow

1. Send request, note `request_id` from logs:
```
INFO - Processing message [request_id=req_abc123]
```

2. Grep all logs for that ID:
```bash
grep "req_abc123" logs/*.log
```

3. Trace entire request lifecycle

### Export Dashboard

1. Grafana → Dashboard → Settings (gear icon)
2. JSON Model → Copy
3. Save to `observability/grafana/dashboards/my-dashboard.json`
4. Commit to repo

## 🚨 Troubleshooting

### Metrics Not Showing

**Problem**: `/metrics` endpoint returns empty or old data

**Solutions**:
1. Check `ENABLE_METRICS=true` in environment
2. Restart backend
3. Send test request to generate metrics
4. Verify prometheus_client installed: `pip list | grep prometheus`

### Prometheus Target DOWN

**Problem**: Prometheus shows `ai-agent` target as DOWN

**Solutions**:
1. Check backend is running: `curl http://localhost:8000/metrics`
2. Check Docker network: `docker network inspect ai-agent-observability`
3. Check prometheus.yml has correct target: `backend:8000`
4. Restart Prometheus: `docker-compose restart prometheus`

### Grafana Dashboard Empty

**Problem**: All panels show "No data"

**Solutions**:
1. Check time range (should include present)
2. Verify datasource: Configuration → Data Sources → Test
3. Check query in Explore tab
4. Generate traffic: send test requests
5. Wait 15-30 seconds for scrape interval

### High Costs

**Problem**: LLM costs higher than expected

**Investigation**:
```promql
# Cost by model
sum(rate(agent_llm_cost_usd_total[1h]) * 3600) by (model)

# Tokens per request
sum(rate(agent_llm_tokens_total{direction="total"}[5m])) 
/ 
sum(rate(agent_requests_total[5m]))
```

**Actions**:
- Optimize prompts (reduce token count)
- Use cheaper models for simple tasks
- Add caching for repeated queries
- Set cost budgets/alerts

## 📚 Key Files

```
observability/
├── README.md                    # Full documentation
├── IMPLEMENTATION_SUMMARY.md     # What was built
├── CHECKLIST.md                  # Integration guide
├── QUICK_REFERENCE.md           # This file
├── docker-compose.yml            # Stack definition
├── prometheus.yml                # Prometheus config
└── grafana/
    ├── provisioning/             # Auto-config
    └── dashboards/               # Dashboard JSONs

backend/observability/
├── metrics.py                    # Metric definitions
├── correlation.py                # Request ID handling
├── config.py                     # Configuration
└── llm_instrumentation.py        # LLM wrappers
```

## 🎓 Learning Resources

- **Prometheus Docs**: https://prometheus.io/docs/
- **PromQL Guide**: https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Grafana Docs**: https://grafana.com/docs/
- **Dashboard Examples**: https://grafana.com/grafana/dashboards/

## ⚡ Quick Tests

### Test 1: Basic Metrics
```bash
curl http://localhost:8000/metrics | grep agent_requests_total
```
Expected: Counter exists

### Test 2: Send Request
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","message":"Hello"}'
```
Expected: 200 OK response

### Test 3: Verify Update
```bash
curl http://localhost:8000/metrics | grep agent_requests_total
```
Expected: Counter increased

### Test 4: Check Prometheus
```bash
curl "http://localhost:9090/api/v1/query?query=agent_requests_total"
```
Expected: JSON with metric data

### Test 5: View in Grafana
1. Open http://localhost:3001
2. Go to Explore
3. Query: `agent_requests_total`
4. Expected: Graph with data

## 🎯 SLOs (Example)

Set your own based on baseline:

- **Latency**: p95 < 3 seconds
- **Availability**: 99.9% success rate
- **Cost**: < $50/day on LLM calls
- **Error Rate**: < 1% of requests

Monitor these in Grafana and set alerts when thresholds are breached.

---

**Version**: 1.0 | **Date**: 2026-01-13 | **Author**: AI Agent Observability Implementation
