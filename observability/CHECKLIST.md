# Integration Checklist for AI Agent Observability

Use this checklist to verify the observability implementation is working correctly.

## ✅ Pre-Flight Checks

### 1. Dependencies Installed

```bash
cd backend
pip install -r requirements.txt
```

Verify `prometheus_client` is installed:
```bash
python3 -c "import prometheus_client; print('✅ prometheus_client installed')"
```

### 2. Environment Variables Set

Create or update `.env` file in `backend/` directory:

```bash
# Required
OPENAI_API_KEY=your-key-here

# Observability (optional, defaults shown)
ENABLE_METRICS=true
ENVIRONMENT=dev
TENANT_ID=default
```

### 3. Code Compilation

Verify all observability modules compile:

```bash
cd backend
python3 -m py_compile observability/*.py
echo "✅ All modules compile successfully"
```

## 🚀 Startup Sequence

### 1. Start Backend

```bash
cd backend
python3 -m uvicorn main:app --reload --port 8000
```

Expected output should include:
```
INFO:     Observability initialized [environment=dev, metrics_enabled=True]
INFO:     Application startup complete
```

### 2. Verify /metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

Expected: Prometheus metrics in text format. Should see lines like:
```
# HELP agent_requests_total Total number of agent requests processed
# TYPE agent_requests_total counter
agent_info{environment="dev",...} 1.0
```

### 3. Send Test Request

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "message": "What is the weather in Budapest?"
  }'
```

### 4. Check Metrics Updated

```bash
curl http://localhost:8000/metrics | grep agent_requests_total
```

Should show count > 0:
```
agent_requests_total{status="success",...} 1.0
```

## 📊 Observability Stack

### 1. Start Prometheus & Grafana

```bash
cd observability
./start.sh
```

Or manually:
```bash
docker-compose up -d
```

### 2. Verify Prometheus

Open http://localhost:9090/targets

Expected:
- Target `ai-agent` should show state **UP**
- Last scrape should be recent (< 30 seconds ago)

If DOWN:
- Check backend is running
- Verify Docker network connectivity
- Check `prometheus.yml` configuration

### 3. Verify Grafana

Open http://localhost:3001

Login: `admin` / `admin`

Navigate to: **Dashboards** → **AI Agent** → **AI Agent - Overview**

Expected:
- Dashboard loads without errors
- All panels show "No data" or actual data
- Time range selector works

### 4. Generate Load

Run test script to generate metrics:

```bash
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"test\",\"message\":\"Test $i\"}"
  sleep 2
done
```

### 5. Verify Dashboard Updates

Refresh Grafana dashboard (F5) or set auto-refresh to 5s

Expected panels to show data:
- ✅ Agent Request Rate (should show ~0.5 req/sec)
- ✅ Agent Request Latency (p50/p90/p95/p99)
- ✅ LLM Token Usage Rate
- ✅ Total LLM Cost (should be > $0)
- ✅ Node Execution Time
- ✅ Tool Call Rate (if tools were used)

## 🔍 Debugging

### Metrics Not Appearing

**Check 1: Backend logs**
```bash
# Look for observability initialization
grep "Observability initialized" backend_logs.txt
```

**Check 2: Metrics endpoint**
```bash
curl -v http://localhost:8000/metrics
# Should return 200 OK with text/plain content
```

**Check 3: Prometheus scraping**
```bash
# Check Prometheus logs
docker logs ai-agent-prometheus | grep ai-agent
```

**Check 4: Network connectivity**
```bash
docker exec ai-agent-prometheus wget -qO- http://backend:8000/metrics
```

### High Memory Usage

**Check Prometheus storage:**
```bash
docker exec ai-agent-prometheus du -sh /prometheus
```

**Reduce retention** if needed (edit `prometheus.yml`):
```yaml
storage:
  tsdb:
    retention.time: 7d  # Instead of 15d
```

### Grafana Dashboard Empty

**Check datasource:**
- Grafana → Configuration → Data Sources → Prometheus
- Click "Test" button - should show "Data source is working"

**Check time range:**
- Dashboard time range should include recent data
- Try "Last 5 minutes"

**Check PromQL queries:**
- Grafana → Explore
- Enter query: `agent_requests_total`
- Should return results

## 🧪 Test Scenarios

### Scenario 1: Basic Request Tracking

1. Send 5 requests
2. Check metrics:
   ```bash
   curl http://localhost:8000/metrics | grep agent_requests_total
   ```
3. Expected: `agent_requests_total{...} 5.0`

### Scenario 2: LLM Cost Tracking

1. Send request requiring LLM call
2. Check cost metric:
   ```bash
   curl http://localhost:8000/metrics | grep agent_llm_cost_usd_total
   ```
3. Expected: Cost > 0 (e.g., `0.002` for small request)

### Scenario 3: Error Tracking

1. Send invalid request (trigger error)
2. Check error metrics:
   ```bash
   curl http://localhost:8000/metrics | grep agent_errors_total
   ```
3. Expected: Error count > 0

### Scenario 4: Request Correlation

1. Send request and note the request_id in backend logs
2. Grep logs for that request_id:
   ```bash
   grep "req_abc123" backend.log
   ```
3. Expected: See all related log entries with same request_id

## 📋 Production Checklist

Before deploying to production:

- [ ] Change Grafana admin password
- [ ] Set `ENVIRONMENT=prod`
- [ ] Set appropriate `TENANT_ID`
- [ ] Set `APP_VERSION` to current version
- [ ] Review LLM pricing in `observability/metrics.py`
- [ ] Set up Prometheus alerting (if needed)
- [ ] Configure data retention policies
- [ ] Add authentication to /metrics endpoint (if public)
- [ ] Test alert rules (if configured)
- [ ] Document runbook for common issues
- [ ] Set up log aggregation (complement metrics)
- [ ] Configure backups for Grafana dashboards
- [ ] Review and adjust scrape intervals
- [ ] Set up monitoring for Prometheus/Grafana themselves

## 🎓 Learning Exercises

### Exercise 1: Add Custom Metric

1. Define new metric in `observability/metrics.py`
2. Record it in agent code
3. Query it in Prometheus
4. Visualize in Grafana

### Exercise 2: Create Alert Rule

1. Create `prometheus/alerts.yml`
2. Define alert for high error rate
3. Reload Prometheus config
4. Trigger alert condition
5. Verify alert fires

### Exercise 3: Optimize Dashboard

1. Add new panel to dashboard
2. Create useful PromQL query
3. Export dashboard JSON
4. Share with team

## ✅ Success Criteria

You know observability is working when:

- ✅ `/metrics` endpoint returns data
- ✅ Prometheus shows target as UP
- ✅ Grafana dashboard displays panels
- ✅ Metrics increase after requests
- ✅ LLM costs are tracked
- ✅ Request IDs appear in logs
- ✅ Error metrics increment on failures
- ✅ Dashboard updates in real-time

## 📞 Support

If you encounter issues:

1. Check this checklist thoroughly
2. Review `observability/README.md`
3. Check `observability/IMPLEMENTATION_SUMMARY.md`
4. Search Prometheus/Grafana documentation
5. Check container logs:
   ```bash
   docker logs ai-agent-prometheus
   docker logs ai-agent-grafana
   ```

## 🎉 Completion

Once all checks pass:

1. Document any environment-specific changes
2. Update team on new observability capabilities
3. Schedule training on dashboard usage
4. Set up regular reviews of metrics
5. Establish SLOs based on baseline metrics

---

**Checklist Version**: 1.0
**Last Updated**: 2026-01-13
