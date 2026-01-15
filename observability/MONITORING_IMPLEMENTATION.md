# Deep Observability Implementation

## Overview

This implementation provides **deep observability** for the LangGraph-based AI agent, following the strict requirements from `docs/09_MONITORING_PROMPT.md`.

## ✅ Implemented Capabilities

### 1. Prompt Lineage Tracking

**Module**: `backend/observability/prompt_lineage.py`

- Tracks prompt versions/hashes per LLM invocation
- Associates each prompt with:
  - `request_id`
  - `agent_execution_id`
  - `model_name`
  - Timestamp
- **NO full prompt content stored** (as per spec)

**Usage**:
```python
from observability.prompt_lineage import get_prompt_tracker

tracker = get_prompt_tracker()
lineage = tracker.track_prompt(
    messages=messages,
    model_name="gpt-4o-mini",
    agent_execution_id="exec_123"
)
```

### 2. Agent Decision Trace

**Module**: `backend/observability/state_tracker.py`

Captures LangGraph state snapshots:
- **Before execution**
- **After each node**
- **After completion**

**Usage**:
```python
from observability.state_tracker import get_state_tracker

tracker = get_state_tracker()

# Before execution
tracker.snapshot_before_execution(agent_execution_id, initial_state)

# After node
tracker.snapshot_after_node(agent_execution_id, "agent_decide", state)

# After completion
tracker.snapshot_after_completion(agent_execution_id, final_state)
```

### 3. Token-Level Cost Tracking

**Module**: `backend/observability/metrics.py`

Real-time token and cost tracking:
- Input tokens
- Output tokens
- Cost calculated per model using configured pricing

**Pricing** (as of Jan 2026):
- `gpt-4o-mini`: $0.15/$0.60 per 1M tokens (input/output)
- `gpt-4o`: $2.50/$10.00 per 1M tokens
- `gpt-4`: $30/$60 per 1M tokens
- `gpt-3.5-turbo`: $0.50/$1.50 per 1M tokens

### 4. Model Fallback Path Visibility

**Module**: `backend/observability/llm_instrumentation.py`

Function: `instrumented_llm_call_with_fallback()`

Tracks:
- Primary model attempts
- Fallback model usage
- Retry exhaustion
- Fallback paths via `model_fallback_count` metric

**Usage**:
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

## 📊 Prometheus Metrics

### 1️⃣ LLM Inference Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `llm_inference_count` | Counter | `model` | Total LLM inference calls |
| `llm_inference_latency_seconds` | Histogram | `model` | LLM call latency |
| `llm_inference_token_input_total` | Counter | `model` | Total input tokens |
| `llm_inference_token_output_total` | Counter | `model` | Total output tokens |
| `llm_cost_total_usd` | Counter | `model` | Total cost in USD |

### 2️⃣ Agent Workflow Metrics (LangGraph)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `agent_execution_count` | Counter | - | Total agent executions |
| `agent_execution_latency_seconds` | Histogram | - | Agent execution latency |
| `node_execution_latency_seconds` | Histogram | `node` | Node execution latency |
| `tool_invocation_count` | Counter | `tool` | Tool invocations |
| `rag_recall_rate` | Gauge | - | RAG recall rate |

### 3️⃣ Error & Fallback Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `agent_error_count` | Counter | - | Agent execution errors |
| `tool_failure_count` | Counter | `tool` | Tool invocation failures |
| `model_fallback_count` | Counter | `from_model`, `to_model` | Model fallback occurrences |
| `max_retries_exceeded_count` | Counter | - | Max retries exceeded |

### 4️⃣ RAG Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rag_chunk_retrieval_count` | Counter | - | RAG chunk retrievals |
| `rag_retrieved_chunk_relevance_score_avg` | Gauge | - | Avg relevance score |
| `vector_db_query_latency_seconds` | Histogram | - | Vector DB query latency |
| `embedding_generation_count` | Counter | - | Embedding generations |

## 📈 Grafana Dashboards

Four dashboards exported as JSON:

### 1. LLM Dashboard (`llm_dashboard.json`)

Panels:
- **Inference count** (rate by model)
- **Token usage** (input/output rate)
- **Cost** (total USD by model)
- **Latency** (p50/p95/p99)
- **Error rate**

### 2. Agent Workflow Dashboard (`agent_workflow_dashboard.json`)

Panels:
- **Agent execution latency** (p50/p95/p99)
- **Node latency** (retriever, parser, router)
- **Tool invocation count** (stacked by tool)
- **Model fallback count**

### 3. RAG Dashboard (`rag_dashboard.json`)

Panels:
- **Retrieval latency** (p50/p95/p99)
- **Top-k relevance score** (gauge)
- **Vector DB load** (query rate)
- **Embedding generation count**

### 4. Cost Dashboard (`cost_dashboard.json`)

Panels:
- **Cost per model** (stacked bar chart)
- **Total cost** (all models, gauge)
- **Cost per agent workflow** (average)
- **Daily burn rate**

## 🐳 Docker Setup

### Services

```yaml
prometheus:
  - Port: 9090
  - Config: observability/prometheus.yml
  - Retention: 15 days / 10GB

grafana:
  - Port: 3001 (to avoid conflict with frontend on 3000)
  - Credentials: admin/admin
  - Dashboards auto-loaded from observability/grafana/dashboards/
```

### Starting the Stack

```bash
# From repo root
docker-compose up --build

# Or use the convenience script
./start.sh
```

### Accessing Services

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **Metrics endpoint**: http://localhost:8001/metrics

## 🔧 Integration Guide

### Using Instrumented LLM Calls

Replace direct LLM calls with instrumented versions:

**Before**:
```python
response = await llm.ainvoke(messages)
```

**After**:
```python
from observability.llm_instrumentation import instrumented_llm_call

response = await instrumented_llm_call(
    llm=llm,
    messages=messages,
    model="gpt-4o-mini",
    agent_execution_id=execution_id
)
```

### Using State Tracker

In your LangGraph nodes:

```python
from observability.state_tracker import get_state_tracker

async def my_node(state):
    tracker = get_state_tracker()
    tracker.snapshot_after_node(
        agent_execution_id=state.get("execution_id"),
        node_name="my_node",
        state=state
    )
    # ... node logic
    return state
```

### Using Metrics

```python
from observability.metrics import (
    llm_inference_count,
    node_execution_latency_seconds,
    tool_invocation_count
)

# Increment counter
llm_inference_count.labels(model="gpt-4o-mini").inc()

# Observe latency
node_execution_latency_seconds.labels(node="agent_decide").observe(2.5)

# Or use context managers
from observability.metrics import record_node_duration

with record_node_duration("agent_decide"):
    # ... node execution
    pass
```

## 📝 Query Examples

### Prometheus Queries

**Cost per model (last hour)**:
```promql
increase(llm_cost_total_usd[1h])
```

**Average agent execution time**:
```promql
rate(agent_execution_latency_seconds_sum[5m]) / rate(agent_execution_latency_seconds_count[5m])
```

**Model fallback rate**:
```promql
rate(model_fallback_count[5m])
```

**Tool failure rate**:
```promql
rate(tool_failure_count[5m]) / rate(tool_invocation_count[5m])
```

## 🚫 Non-Goals (As Per Spec)

The following were **explicitly NOT implemented**:

- ❌ Tracing frameworks (Jaeger, Tempo, OpenTelemetry)
- ❌ External SaaS observability tools
- ❌ Logging of raw prompts or PII
- ❌ Dashboards beyond the four specified
- ❌ Metrics beyond the listed ones

## ✅ Final State Validation

The system provides:

✅ **Full visibility into**:
- Prompt evolution (via prompt lineage)
- Agent decision paths (via state snapshots)
- Model fallback behavior (via fallback metrics)
- Real-time cost (via cost metrics)

✅ **Accurate Prometheus metrics**:
- All metrics defined and exposed at `/metrics`
- Low cardinality (no `user_id` labels)
- Proper types (Counter, Histogram, Gauge)

✅ **Ready-to-import Grafana dashboards**:
- 4 dashboards in JSON format
- Auto-provisioned on Grafana startup

✅ **Zero impact on agent functional behavior**:
- All instrumentation is opt-in
- Metrics can be disabled via `ENABLE_METRICS=false`
- No blocking operations in metrics collection

## 📚 References

- Specification: `docs/09_MONITORING_PROMPT.md`
- Metrics module: `backend/observability/metrics.py`
- LLM instrumentation: `backend/observability/llm_instrumentation.py`
- Prompt lineage: `backend/observability/prompt_lineage.py`
- State tracker: `backend/observability/state_tracker.py`
- Dashboards: `observability/grafana/dashboards/`

## 🔍 Troubleshooting

### Metrics not appearing in Prometheus

1. Check backend is exposing metrics: `curl http://localhost:8001/metrics`
2. Check Prometheus targets: http://localhost:9090/targets
3. Verify Prometheus can reach backend: check `ai-agent-backend:8000` resolves in container

### Dashboards not loading in Grafana

1. Check dashboard JSON files exist in `observability/grafana/dashboards/`
2. Check Grafana provisioning config: `observability/grafana/provisioning/dashboards/dashboards.yml`
3. Restart Grafana: `docker-compose restart grafana`

### Costs seem incorrect

1. Verify model pricing in `backend/observability/metrics.py` (search for `MODEL_PRICING`)
2. Check token counts are being tracked: look for `usage_metadata` in LLM responses
3. Enable debug logging: set `logging.level=DEBUG` in backend

---

**Implementation Date**: January 14, 2026  
**Specification**: `docs/09_MONITORING_PROMPT.md`  
**Status**: ✅ Complete
