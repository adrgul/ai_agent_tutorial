# AI Agent Observability

Production-grade monitoring and observability for the LangGraph-based AI agent, using Prometheus and Grafana.

## 📊 Overview

This observability stack provides comprehensive monitoring of:

- **Agent Performance**: Request rates, latencies (p50/p90/p95/p99), throughput
- **LLM Usage**: Token consumption, estimated costs, API latency by model
- **Workflow Execution**: Node-level execution times, bottleneck detection
- **Tool Usage**: Tool call rates, success/failure tracking, external API latency
- **Error Tracking**: Error rates by type and location for debugging

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Running AI Agent backend (see main `README.md`)
- OpenAI API key configured

### Start Observability Stack

```bash
cd observability
docker-compose up -d
```

This starts:
- **Prometheus** on http://localhost:9090
- **Grafana** on http://localhost:3001 (login: admin/admin)

### Access Dashboards

1. Open Grafana: http://localhost:3001
2. Login with `admin` / `admin` (change password on first login)
3. Navigate to "Dashboards" → "AI Agent" → "AI Agent - Overview"

### View Raw Metrics

- Agent metrics: http://localhost:8000/metrics
- Prometheus UI: http://localhost:9090

## 📈 Available Metrics

### Request Metrics

```promql
# Total requests by status
agent_requests_total{status="success|error", tenant="default", environment="dev"}

# Request latency histogram
agent_request_duration_seconds{tenant="default", environment="dev"}

# Example query: 95th percentile latency
histogram_quantile(0.95, sum(rate(agent_request_duration_seconds_bucket[5m])) by (le))
```

### LLM Metrics

```promql
# Token usage by model and direction
agent_llm_tokens_total{model="gpt-4-turbo-preview", direction="prompt|completion|total"}

# Estimated costs in USD
agent_llm_cost_usd_total{model="gpt-4-turbo-preview", tenant="default"}

# LLM API latency
agent_llm_call_duration_seconds{model="gpt-4-turbo-preview"}

# Example: Cost per hour
sum(rate(agent_llm_cost_usd_total[1h]) * 3600) by (model)
```

### Node Metrics

```promql
# Node execution count
agent_node_executions_total{node="agent_decide|agent_finalize|tool_execution"}

# Node execution time
agent_node_duration_seconds{node="agent_decide"}

# Example: Average execution time per node
sum(rate(agent_node_duration_seconds_sum[5m])) by (node) 
/ 
sum(rate(agent_node_executions_total[5m])) by (node)
```

### Tool Metrics

```promql
# Tool call count by status
agent_tool_calls_total{tool="weather|geocode|crypto_price", status="success|error"}

# Tool execution latency
agent_tool_duration_seconds{tool="weather"}

# Example: Tool error rate
sum(rate(agent_tool_calls_total{status="error"}[5m])) by (tool)
/
sum(rate(agent_tool_calls_total[5m])) by (tool)
```

### Error Metrics

```promql
# Errors by type and node
agent_errors_total{error_type="llm_error|tool_error|validation_error", node="agent_decide"}

# Example: Total error rate
sum(rate(agent_errors_total[5m]))
```

### RAG Metrics

```promql
# RAG retrieval count
agent_rag_retrievals_total{status="success|error"}

# Number of chunks retrieved
agent_rag_chunks_retrieved

# RAG latency
agent_rag_duration_seconds

# Example: Average chunks per query
sum(rate(agent_rag_chunks_retrieved_sum[5m]))
/
sum(rate(agent_rag_retrievals_total[5m]))
```

## 🔧 Configuration

### Environment Variables

Configure observability via environment variables:

```bash
# Enable/disable metrics collection
ENABLE_METRICS=true

# Deployment environment (affects labels)
ENVIRONMENT=dev  # dev|staging|prod

# Tenant identifier (for multi-tenant deployments)
TENANT_ID=default

# Application version (for tracking deployments)
APP_VERSION=1.0.0

# Request correlation
ENABLE_REQUEST_CORRELATION=true

# Logging
ENABLE_CORRELATED_LOGGING=true
LOG_LEVEL=INFO
```

### Docker Compose Override

To integrate with your main application stack, add to your main `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    environment:
      - ENABLE_METRICS=true
      - ENVIRONMENT=prod
    networks:
      - default
      - ai-agent-observability  # Connect to observability network

networks:
  ai-agent-observability:
    external: true
    name: ai-agent-observability
```

### Prometheus Configuration

Edit `prometheus.yml` to:
- Change scrape intervals
- Add alerting rules
- Configure retention policies

### Grafana Configuration

- **Admin password**: Change in `docker-compose.yml` (default: admin)
- **Data retention**: Configure in Prometheus, not Grafana
- **Custom dashboards**: Add JSON files to `grafana/dashboards/`

## 📊 Dashboard Guide

### AI Agent - Overview Dashboard

Located at: `grafana/dashboards/ai-agent-overview.json`

**Panels:**

1. **Agent Request Rate**: Requests per second (success vs errors)
2. **Agent Request Latency**: p50/p90/p95/p99 percentiles
3. **LLM Token Usage Rate**: Tokens per second by model
4. **Total LLM Cost**: Cumulative spend in USD
5. **LLM Cost Rate**: Spending rate per minute
6. **Node Execution Time**: Average duration by node
7. **Tool Call Rate**: Tool usage by success/error status
8. **Error Rate by Type**: Errors categorized by type

### Creating Custom Dashboards

1. Open Grafana UI
2. Click "Create" → "Dashboard"
3. Add panels with PromQL queries
4. Export JSON: Dashboard settings → "JSON Model" → Copy
5. Save to `grafana/dashboards/your-dashboard.json`

## 🔍 Debugging with Metrics

### Finding Slow Requests

```promql
# Requests taking > 5 seconds
histogram_quantile(0.99, agent_request_duration_seconds_bucket) > 5
```

### Identifying Cost Spikes

```promql
# Cost increase over last hour
increase(agent_llm_cost_usd_total[1h]) > 10
```

### Detecting Error Patterns

```promql
# Sudden increase in errors
delta(agent_errors_total[5m]) > 10
```

### Node Bottleneck Analysis

```promql
# Find slowest node
topk(1, sum(rate(agent_node_duration_seconds_sum[5m])) by (node))
```

## 🎯 Request Correlation

Every request gets a unique `request_id` that:
- Propagates through LangGraph state
- Appears in all log messages
- Enables end-to-end tracing

**Example log entry:**
```
2026-01-13 10:15:30 - agent - INFO - Processing message [request_id=req_abc123def456]
```

**Access in code:**
```python
from observability.correlation import get_request_id

request_id = get_request_id()
logger.info(f"Current request: {request_id}")
```

## ⚠️ Best Practices

### Cardinality Management

❌ **Don't** use high-cardinality labels:
```python
# BAD: Creates millions of unique time series
agent_requests_total{user_id="user123"}
```

✅ **Do** use low-cardinality labels:
```python
# GOOD: Limited unique values
agent_requests_total{tenant="default", environment="prod"}
```

### Cost Tracking

- Review costs daily using Grafana dashboards
- Set up alerts for unexpected spending
- Update pricing table in `observability/metrics.py` when models change

### Metrics vs Logs

- **Metrics**: Aggregated numbers (request count, latency, cost)
- **Logs**: Individual events (errors, debug info)
- Use both together for complete observability

## 🚨 Alerts (Optional)

Create alert rules in `prometheus/alerts.yml`:

```yaml
groups:
  - name: ai_agent_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(agent_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/second"

      - alert: HighLLMCost
        expr: increase(agent_llm_cost_usd_total[1h]) > 50
        labels:
          severity: critical
        annotations:
          summary: "LLM costs exceeding budget"
          description: "Spent ${{ $value }} in the last hour"
```

Requires setting up Alertmanager (not included by default).

## 📝 Adding Custom Metrics

### 1. Define Metric

Edit `backend/observability/metrics.py`:

```python
my_custom_metric = Counter(
    name='agent_custom_total',
    documentation='Description of what this measures',
    labelnames=['dimension1', 'dimension2'],
    registry=registry
)
```

### 2. Record Metric

In your code:

```python
from observability.metrics import my_custom_metric

my_custom_metric.labels(dimension1="value1", dimension2="value2").inc()
```

### 3. Query in Grafana

Add panel with PromQL:

```promql
rate(agent_custom_total[5m])
```

## 🧪 Testing Metrics

### Generate Load

```bash
# Send 100 test requests
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{"user_id":"test","message":"What is the weather in Budapest?"}'
  sleep 1
done
```

### Verify Metrics

```bash
# Check raw metrics
curl http://localhost:8000/metrics | grep agent_

# Check Prometheus
curl "http://localhost:9090/api/v1/query?query=agent_requests_total"
```

## 🛠️ Troubleshooting

### Metrics Not Showing Up

1. **Check backend is running**:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. **Check Prometheus is scraping**:
   - Open http://localhost:9090/targets
   - Verify `ai-agent` target is "UP"

3. **Check network connectivity**:
   ```bash
   docker network inspect ai-agent-observability
   ```

### Grafana Can't Connect to Prometheus

1. Verify datasource configuration:
   - Grafana → Configuration → Data Sources → Prometheus
   - URL should be: `http://prometheus:9090`

2. Check Docker network:
   ```bash
   docker-compose ps
   # Both containers should be on 'ai-agent-observability' network
   ```

### High Memory Usage

Prometheus stores metrics in-memory and on disk. To reduce:

1. Lower retention time in `prometheus.yml`:
   ```yaml
   storage:
     tsdb:
       retention.time: 7d  # Instead of 15d
   ```

2. Reduce scrape frequency:
   ```yaml
   global:
     scrape_interval: 30s  # Instead of 15s
   ```

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Query Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/best-practices/)

## 🔐 Security Considerations

### Production Deployment

1. **Change default passwords**:
   - Grafana admin password
   - Add authentication to /metrics endpoint if needed

2. **Use environment-specific configs**:
   - Separate `docker-compose.prod.yml`
   - Different retention policies per environment

3. **Network isolation**:
   - Don't expose Prometheus/Grafana ports publicly
   - Use reverse proxy with authentication

4. **Sensitive data**:
   - Never log full prompts or API keys
   - Metrics contain only aggregated data

## 🧑‍💻 Development

### Disable Metrics in Tests

```bash
export ENABLE_METRICS=false
pytest backend/tests/
```

### Reload Prometheus Config

```bash
curl -X POST http://localhost:9090/-/reload
```

(Requires `--web.enable-lifecycle` flag, already enabled)

## 📦 Files Overview

```
observability/
├── README.md                          # This file
├── docker-compose.yml                  # Prometheus + Grafana stack
├── prometheus.yml                      # Prometheus configuration
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── prometheus.yml          # Auto-configure Prometheus datasource
    │   └── dashboards/
    │       └── dashboards.yml          # Auto-load dashboards
    └── dashboards/
        └── ai-agent-overview.json      # Main overview dashboard

backend/observability/
├── __init__.py                         # Module exports
├── config.py                           # Configuration management
├── correlation.py                      # Request correlation (request_id)
├── metrics.py                          # Prometheus metrics definitions
└── llm_instrumentation.py              # LLM call wrappers with metrics
```

## 📄 License

Same as main project.

---

**Questions or issues?** Check existing documentation or create an issue in the repository.
