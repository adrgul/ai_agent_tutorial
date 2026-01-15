# Prometheus & Grafana Monitoring Guide

**Complete Programming Guide for AI Agent Observability**

Last Updated: January 15, 2026

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture & Data Flow](#architecture--data-flow)
3. [Metric Types Explained](#metric-types-explained)
4. [Python Implementation](#python-implementation)
5. [LangGraph Integration](#langgraph-integration)
6. [Grafana Dashboard Configuration](#grafana-dashboard-configuration)
7. [Complete Examples](#complete-examples)
8. [Best Practices](#best-practices)

---

## 📊 Overview

### What is this monitoring stack?

The AI Agent project uses a **three-tier observability stack**:

```
Python Application (LangGraph Agent)
         ↓ (records metrics)
    Prometheus Client Library
         ↓ (exposes /metrics endpoint)
    Prometheus Server (scrapes & stores)
         ↓ (queries via PromQL)
    Grafana Dashboards (visualizes)
```

### Key Components

| Component | Role | Port | Tech |
|-----------|------|------|------|
| **Backend** | Generates metrics during agent execution | 8001 | FastAPI + LangGraph + prometheus_client |
| **Prometheus** | Scrapes, stores time-series data | 9090 | Prometheus TSDB |
| **Grafana** | Visualizes metrics in dashboards | 3001 | Grafana |

---

## 🏗️ Architecture & Data Flow

### Complete Monitoring Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. USER SENDS MESSAGE                        │
│               "What's the weather in Budapest?"                 │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              2. LANGGRAPH AGENT PROCESSES REQUEST               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Node: agent_decide                                      │  │
│  │  → record_node_duration("agent_decide") starts timer     │  │
│  │  → instrumented_llm_call() records LLM metrics:          │  │
│  │     • llm_inference_count +1                             │  │
│  │     • llm_inference_token_input_total +450               │  │
│  │     • llm_inference_token_output_total +85               │  │
│  │     • llm_inference_latency_seconds 1.2s                 │  │
│  │     • llm_cost_total_usd +$0.015                         │  │
│  │  → record_node_duration() completes:                     │  │
│  │     • node_execution_latency_seconds{node="agent_decide"}│  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Node: tool_execution                                    │  │
│  │  → record_tool_call("weather") starts timer              │  │
│  │  → Weather API called                                    │  │
│  │  → record_tool_call() completes:                         │  │
│  │     • tool_invocation_count{tool="weather"} +1           │  │
│  │     • agent_tool_duration_seconds{tool="weather"} 0.8s   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Agent completes execution                               │  │
│  │  → agent_execution_count +1                              │  │
│  │  → agent_execution_latency_seconds 2.5s                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│         3. BACKEND EXPOSES METRICS AT /metrics ENDPOINT         │
│                                                                 │
│  GET http://localhost:8001/metrics returns:                    │
│                                                                 │
│  # HELP llm_inference_count Total LLM inference calls          │
│  # TYPE llm_inference_count counter                            │
│  llm_inference_count{model="gpt-4o-mini"} 1.0                  │
│                                                                 │
│  # HELP llm_inference_token_input_total Input tokens           │
│  # TYPE llm_inference_token_input_total counter                │
│  llm_inference_token_input_total{model="gpt-4o-mini"} 450.0    │
│                                                                 │
│  # HELP tool_invocation_count Tool invocations                 │
│  # TYPE tool_invocation_count counter                          │
│  tool_invocation_count{tool="weather"} 1.0                     │
│                                                                 │
│  ... (and 20+ other metrics)                                   │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│       4. PROMETHEUS SCRAPES /metrics EVERY 15 SECONDS           │
│                                                                 │
│  Prometheus configuration (prometheus.yml):                    │
│                                                                 │
│  scrape_configs:                                               │
│    - job_name: 'ai-agent'                                      │
│      static_configs:                                           │
│        - targets: ['ai-agent-backend:8000']                    │
│      scrape_interval: 15s                                      │
│                                                                 │
│  → Prometheus stores metrics in time-series database (TSDB)    │
│  → Retention: 15 days or 10GB                                  │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│           5. GRAFANA QUERIES PROMETHEUS WITH PromQL             │
│                                                                 │
│  Dashboard Panel Configuration:                                │
│                                                                 │
│  Query: rate(llm_inference_count[5m])                          │
│  Legend: {{model}}                                             │
│  Visualization: Time Series Graph                              │
│                                                                 │
│  → Grafana fetches data from Prometheus every 5-30s            │
│  → Displays interactive charts with zoom, pan, time ranges     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📏 Metric Types Explained

Prometheus supports **4 core metric types**. Understanding them is critical for proper instrumentation.

### 1. Counter

**Definition**: A monotonically increasing value that only goes up (or resets to zero on restart).

**When to use**: Counting events that accumulate over time.

**Python Example**:
```python
from prometheus_client import Counter

# Define counter
llm_inference_count = Counter(
    name='llm_inference_count',
    documentation='Total number of LLM inference calls',
    labelnames=['model']  # Labels for grouping
)

# Use counter
llm_inference_count.labels(model="gpt-4o-mini").inc()  # Increment by 1
llm_inference_count.labels(model="gpt-4o-mini").inc(5)  # Increment by 5
```

**Real example from project**:
```python
# File: backend/observability/metrics.py

tool_invocation_count = Counter(
    name='tool_invocation_count',
    documentation='Total number of tool invocations',
    labelnames=['tool']
)

# Usage in backend/services/tools.py:
with record_tool_call("weather"):
    result = await self.client.get_forecast(...)
    # Internally increments: tool_invocation_count{tool="weather"}
```

**PromQL queries for counters**:
```promql
# Total count
llm_inference_count{model="gpt-4o-mini"}

# Rate per second over 5 minutes
rate(llm_inference_count[5m])

# Total increase over 1 hour
increase(llm_inference_count[1h])
```

---

### 2. Gauge

**Definition**: A value that can go up or down (current state/level).

**When to use**: Measuring current values like temperature, memory usage, queue size.

**Python Example**:
```python
from prometheus_client import Gauge

# Define gauge
active_connections = Gauge(
    name='active_connections',
    documentation='Current number of active connections'
)

# Use gauge
active_connections.set(42)  # Set to specific value
active_connections.inc()    # Increment by 1
active_connections.dec(5)   # Decrement by 5
```

**Real example from project**:
```python
# File: backend/observability/metrics.py

rag_recall_rate = Gauge(
    name='rag_recall_rate',
    documentation='RAG recall rate (derived relevance metric)'
)

# Usage:
rag_recall_rate.set(0.87)  # 87% recall rate
```

**PromQL queries for gauges**:
```promql
# Current value
rag_recall_rate

# Average over time
avg_over_time(rag_recall_rate[5m])

# Max value in last hour
max_over_time(rag_recall_rate[1h])
```

---

### 3. Histogram

**Definition**: Samples observations and counts them in configurable buckets. Automatically provides count, sum, and quantile calculations.

**When to use**: Measuring distributions (latency, request sizes, durations).

**Python Example**:
```python
from prometheus_client import Histogram

# Define histogram
request_duration_seconds = Histogram(
    name='request_duration_seconds',
    documentation='Request duration in seconds',
    labelnames=['method'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]  # Custom buckets
)

# Use histogram
request_duration_seconds.labels(method="GET").observe(1.2)  # Record 1.2 seconds
```

**Real example from project**:
```python
# File: backend/observability/metrics.py

llm_inference_latency_seconds = Histogram(
    name='llm_inference_latency_seconds',
    documentation='Latency of LLM inference calls in seconds',
    labelnames=['model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# Usage in backend/observability/llm_instrumentation.py:
start_time = time.time()
response = await llm.ainvoke(messages)
duration = time.time() - start_time
llm_inference_latency_seconds.labels(model="gpt-4o-mini").observe(duration)
```

**What histogram creates**:
```
# Three metrics are automatically generated:
llm_inference_latency_seconds_bucket{model="gpt-4o-mini",le="0.5"} 10
llm_inference_latency_seconds_bucket{model="gpt-4o-mini",le="1.0"} 45
llm_inference_latency_seconds_bucket{model="gpt-4o-mini",le="5.0"} 98
llm_inference_latency_seconds_sum{model="gpt-4o-mini"} 123.4
llm_inference_latency_seconds_count{model="gpt-4o-mini"} 100
```

**PromQL queries for histograms**:
```promql
# Calculate 95th percentile latency
histogram_quantile(0.95, rate(llm_inference_latency_seconds_bucket[5m]))

# Calculate 50th percentile (median)
histogram_quantile(0.50, rate(llm_inference_latency_seconds_bucket[5m]))

# Average latency
rate(llm_inference_latency_seconds_sum[5m]) / rate(llm_inference_latency_seconds_count[5m])
```

---

### 4. Summary

**Definition**: Similar to histogram but calculates quantiles on the client side.

**When to use**: When you need precise quantiles but don't need aggregation across instances.

**Note**: This project uses **Histograms** instead of Summaries because histograms are more flexible for aggregation in distributed systems.

---

## 🐍 Python Implementation

### Step 1: Install Dependencies

```bash
# In backend/requirements.txt
prometheus-client==0.19.0
```

### Step 2: Define Metrics

**File: `backend/observability/metrics.py`**

```python
import os
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Create registry
registry = CollectorRegistry()

# Define metrics
llm_inference_count = Counter(
    name='llm_inference_count',
    documentation='Total number of LLM inference calls',
    labelnames=['model'],
    registry=registry
)

llm_inference_latency_seconds = Histogram(
    name='llm_inference_latency_seconds',
    documentation='Latency of LLM inference calls in seconds',
    labelnames=['model'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry
)

tool_invocation_count = Counter(
    name='tool_invocation_count',
    documentation='Total number of tool invocations',
    labelnames=['tool'],
    registry=registry
)
```

### Step 3: Record Metrics in Code

#### Example 1: Recording LLM Calls

**File: `backend/observability/llm_instrumentation.py`**

```python
import time
from observability.metrics import (
    llm_inference_count,
    llm_inference_latency_seconds,
    llm_inference_token_input_total,
    llm_inference_token_output_total,
    llm_cost_total_usd
)

async def instrumented_llm_call(llm, messages, model: str):
    """Wrapper that automatically records LLM metrics."""
    
    # Start timing
    start_time = time.time()
    
    try:
        # Make actual LLM call
        response = await llm.ainvoke(messages)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract token usage
        prompt_tokens = response.usage_metadata.get('input_tokens', 0)
        completion_tokens = response.usage_metadata.get('output_tokens', 0)
        
        # Record metrics
        llm_inference_count.labels(model=model).inc()
        llm_inference_latency_seconds.labels(model=model).observe(duration)
        llm_inference_token_input_total.labels(model=model).inc(prompt_tokens)
        llm_inference_token_output_total.labels(model=model).inc(completion_tokens)
        
        # Calculate and record cost
        cost = calculate_cost(model, prompt_tokens, completion_tokens)
        llm_cost_total_usd.labels(model=model).inc(cost)
        
        return response
        
    except Exception as e:
        # Record error metrics
        duration = time.time() - start_time
        llm_inference_latency_seconds.labels(model=model).observe(duration)
        raise
```

#### Example 2: Recording Tool Calls with Context Manager

**File: `backend/observability/metrics.py`**

```python
import time
from contextlib import contextmanager
from observability.metrics import tool_invocation_count, agent_tool_duration_seconds

@contextmanager
def record_tool_call(tool_name: str):
    """
    Context manager to record tool call metrics.
    
    Usage:
        with record_tool_call("weather"):
            result = await weather_api.get_forecast()
    """
    start_time = time.time()
    
    try:
        yield
        # Success path
        tool_invocation_count.labels(tool=tool_name).inc()
    except Exception as e:
        # Error path - still record invocation
        tool_invocation_count.labels(tool=tool_name).inc()
        raise
    finally:
        # Always record duration
        duration = time.time() - start_time
        agent_tool_duration_seconds.labels(
            tool=tool_name,
            environment="dev"
        ).observe(duration)
```

**Usage in `backend/services/tools.py`**:

```python
from observability.metrics import record_tool_call

class WeatherTool:
    async def execute(self, city: str):
        with record_tool_call("weather"):
            logger.info(f"Calling weather API for {city}")
            result = await self.client.get_forecast(city=city)
            return result
```

#### Example 3: Recording Node Execution Times

**File: `backend/observability/metrics.py`**

```python
@contextmanager
def record_node_duration(node_name: str):
    """
    Context manager to record LangGraph node execution time.
    
    Usage:
        with record_node_duration("agent_decide"):
            state = await _agent_decide_node(state)
    """
    start_time = time.time()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        node_execution_latency_seconds.labels(node=node_name).observe(duration)
        agent_node_executions_total.labels(
            node=node_name,
            environment="dev"
        ).inc()
```

### Step 4: Expose Metrics Endpoint

**File: `backend/main.py`**

```python
from fastapi import FastAPI
from prometheus_client import make_asgi_app, generate_latest, CONTENT_TYPE_LATEST
from observability.metrics import registry, init_metrics

app = FastAPI()

# Initialize metrics with metadata
init_metrics(environment="dev", version="1.0.0")

# Mount Prometheus metrics endpoint at /metrics
metrics_app = make_asgi_app(registry=registry)
app.mount("/metrics", metrics_app)

# Or manual endpoint:
@app.get("/metrics")
async def metrics():
    from starlette.responses import Response
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    )
```

### Step 5: Test Metrics Endpoint

```bash
# Start backend
docker-compose up -d backend

# Send a test request to generate metrics
curl -X POST http://localhost:8001/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "What is the weather?"}'

# Check metrics endpoint
curl http://localhost:8001/metrics

# Output:
# HELP llm_inference_count Total number of LLM inference calls
# TYPE llm_inference_count counter
llm_inference_count{model="gpt-4o-mini"} 1.0
# HELP tool_invocation_count Total number of tool invocations
# TYPE tool_invocation_count counter
tool_invocation_count{tool="weather"} 1.0
```

---

## 🔗 LangGraph Integration

### How LangGraph Nodes Record Metrics

**File: `backend/services/agent.py`**

```python
from langgraph.graph import StateGraph, END
from observability.metrics import record_node_duration
from observability.llm_instrumentation import instrumented_llm_call

class AIAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        # Add nodes with metric instrumentation
        workflow.add_node("agent_decide", self._agent_decide_node)
        workflow.add_node("tool_execution", self._tool_execution_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Add edges...
        return workflow.compile()
    
    async def _agent_decide_node(self, state: AgentState) -> AgentState:
        """
        LangGraph node that makes LLM decision.
        Records: node execution time, LLM metrics
        """
        with record_node_duration("agent_decide"):
            # Prepare messages
            messages = self._prepare_messages(state)
            
            # Call LLM with instrumentation
            response = await instrumented_llm_call(
                llm=self.llm,
                messages=messages,
                model="gpt-4o-mini",
                agent_execution_id=state.get("agent_execution_id")
            )
            
            # Parse decision
            decision = self._parse_decision(response.content)
            
            return {
                **state,
                "last_decision": decision,
                "messages": state["messages"] + [response]
            }
    
    async def _tool_execution_node(self, state: AgentState) -> AgentState:
        """
        LangGraph node that executes tools.
        Records: node execution time, tool invocation metrics
        """
        with record_node_duration("tool_execution"):
            decision = state["last_decision"]
            tool_name = decision["tool_name"]
            arguments = decision["arguments"]
            
            # Find and execute tool (tool already records its own metrics)
            tool = self.tools[tool_name]
            result = await tool.execute(**arguments)
            
            return {
                **state,
                "tool_results": state.get("tool_results", []) + [result]
            }
```

### Complete Flow Example

```python
# User sends: "What's the weather in Budapest?"

# 1. Agent graph starts execution
#    → agent_execution_count.inc()
#    → Start timer for agent_execution_latency_seconds

# 2. Node: agent_decide
#    with record_node_duration("agent_decide"):  # ← Node timer starts
#        response = await instrumented_llm_call(...)  # ← LLM metrics recorded
#        # Inside instrumented_llm_call():
#        #   llm_inference_count.labels(model="gpt-4o-mini").inc()
#        #   llm_inference_token_input_total.labels(model="gpt-4o-mini").inc(450)
#        #   llm_inference_token_output_total.labels(model="gpt-4o-mini").inc(85)
#        #   llm_inference_latency_seconds.labels(model="gpt-4o-mini").observe(1.2)
#        #   llm_cost_total_usd.labels(model="gpt-4o-mini").inc(0.015)
#    # Node timer ends:
#    #   node_execution_latency_seconds.labels(node="agent_decide").observe(1.3)

# 3. Node: tool_execution
#    with record_node_duration("tool_execution"):  # ← Node timer starts
#        with record_tool_call("weather"):  # ← Tool timer starts
#            result = await weather_client.get_forecast(city="Budapest")
#        # Tool timer ends:
#        #   tool_invocation_count.labels(tool="weather").inc()
#        #   agent_tool_duration_seconds.labels(tool="weather").observe(0.8)
#    # Node timer ends:
#    #   node_execution_latency_seconds.labels(node="tool_execution").observe(0.9)

# 4. Agent completes
#    → agent_execution_latency_seconds.observe(2.5)
```

---

## 📈 Grafana Dashboard Configuration

### How to Display Metrics in Grafana

#### Step 1: Configure Data Source

**File: `observability/grafana/provisioning/datasources/prometheus.yml`**

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    jsonData:
      timeInterval: "15s"
```

#### Step 2: Create Dashboard Panel

**Example: LLM Inference Count Graph**

```json
{
  "title": "LLM Inference Count (rate)",
  "type": "timeseries",
  "datasource": {
    "type": "prometheus",
    "uid": "PBFA97CFB590B2093"
  },
  "targets": [
    {
      "expr": "rate(llm_inference_count[5m])",
      "legendFormat": "{{model}}",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "ops",
      "custom": {
        "lineWidth": 2,
        "fillOpacity": 10
      }
    }
  }
}
```

#### Step 3: Common PromQL Queries for Dashboards

##### LLM Dashboard Panels

**Panel 1: LLM Inference Rate**
```promql
# Query:
rate(llm_inference_count[5m])

# Legend: {{model}}
# Visualization: Time Series
# Unit: ops (operations per second)
```

**Panel 2: Token Usage by Model**
```promql
# Input tokens:
rate(llm_inference_token_input_total[5m])

# Output tokens:
rate(llm_inference_token_output_total[5m])

# Legend: {{model}} - input/output
# Visualization: Stacked Area Chart
# Unit: tokens/s
```

**Panel 3: LLM Latency Percentiles**
```promql
# p50 (median):
histogram_quantile(0.50, rate(llm_inference_latency_seconds_bucket[5m]))

# p95:
histogram_quantile(0.95, rate(llm_inference_latency_seconds_bucket[5m]))

# p99:
histogram_quantile(0.99, rate(llm_inference_latency_seconds_bucket[5m]))

# Legend: p50, p95, p99
# Visualization: Time Series with multiple queries
# Unit: seconds
```

**Panel 4: Total Cost**
```promql
# Query:
sum(llm_cost_total_usd)

# Visualization: Stat (single number)
# Unit: currency USD ($)
```

##### Agent Workflow Dashboard Panels

**Panel 5: Tool Invocation Breakdown**
```promql
# Query:
sum by (tool) (increase(tool_invocation_count[5m]))

# Legend: {{tool}}
# Visualization: Bar Chart or Pie Chart
# Unit: short (count)
```

**Panel 6: Node Execution Latency**
```promql
# Average latency per node:
sum by (node) (rate(node_execution_latency_seconds_sum[5m])) 
  / 
sum by (node) (rate(node_execution_latency_seconds_count[5m]))

# Legend: {{node}}
# Visualization: Time Series
# Unit: seconds
```

**Panel 7: Agent Execution Count**
```promql
# Query:
increase(agent_execution_count[5m])

# Visualization: Stat or Time Series
# Unit: short
```

##### Cost Dashboard Panels

**Panel 8: Cost by Model (Last Hour)**
```promql
# Query:
sum by (model) (increase(llm_cost_total_usd[1h]))

# Legend: {{model}}
# Visualization: Pie Chart
# Unit: currency USD ($)
```

**Panel 9: Burn Rate (Cost per Day)**
```promql
# Query:
sum(increase(llm_cost_total_usd[24h]))

# Visualization: Stat with trend
# Unit: currency USD ($)
```

**Panel 10: Cost per Workflow**
```promql
# Query:
sum(increase(llm_cost_total_usd[5m])) 
  / 
sum(increase(agent_execution_count[5m]))

# Visualization: Gauge
# Unit: currency USD ($)
```

---

## 🔬 Complete Examples

### Example 1: Adding a New Metric

**Scenario**: Track how many times users reset their conversation context.

#### Step 1: Define Metric

**File: `backend/observability/metrics.py`**

```python
context_reset_count = Counter(
    name='context_reset_count',
    documentation='Total number of context resets',
    labelnames=['user_id'],  # ⚠️ Use with caution - can create high cardinality
    registry=registry
)
```

#### Step 2: Record Metric

**File: `backend/services/chat_service.py`**

```python
from observability.metrics import context_reset_count

class ChatService:
    async def process_message(self, user_id: str, message: str):
        # Detect reset command
        if message.lower().strip() == "reset context":
            # Clear session
            await self.conversation_repo.clear_session(user_id)
            
            # Record metric
            context_reset_count.labels(user_id=user_id).inc()
            
            return "Context reset successfully"
```

#### Step 3: Create Grafana Panel

```json
{
  "title": "Context Resets (Last Hour)",
  "type": "stat",
  "targets": [
    {
      "expr": "sum(increase(context_reset_count[1h]))",
      "refId": "A"
    }
  ]
}
```

---

### Example 2: Multi-Dimensional Metrics

**Scenario**: Track tool success vs. failure rates per tool.

#### Step 1: Add Status Label

**File: `backend/observability/metrics.py`**

```python
@contextmanager
def record_tool_call(tool_name: str):
    start_time = time.time()
    status = "success"  # Default
    
    try:
        yield
    except Exception as e:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        
        # Record with status label
        tool_invocation_count.labels(
            tool=tool_name,
            status=status  # ← Added status dimension
        ).inc()
        
        agent_tool_duration_seconds.labels(
            tool=tool_name
        ).observe(duration)
```

#### Step 2: Update Metric Definition

```python
tool_invocation_count = Counter(
    name='tool_invocation_count',
    documentation='Total number of tool invocations',
    labelnames=['tool', 'status'],  # ← Added status label
    registry=registry
)
```

#### Step 3: Query in Grafana

```promql
# Success rate:
sum by (tool) (rate(tool_invocation_count{status="success"}[5m]))
  / 
sum by (tool) (rate(tool_invocation_count[5m]))

# Error count:
sum by (tool) (increase(tool_invocation_count{status="error"}[5m]))
```

---

## 🎯 Best Practices

### 1. Label Cardinality

**❌ BAD** - High cardinality (millions of unique label combinations):
```python
request_count = Counter(
    'request_count',
    'Total requests',
    labelnames=['user_id', 'session_id', 'request_id']  # ❌ Too many unique values!
)
```

**✅ GOOD** - Low cardinality (limited unique values):
```python
request_count = Counter(
    'request_count',
    'Total requests',
    labelnames=['status', 'endpoint']  # ✅ Few unique values
)
```

**Rule**: Labels should have **< 100 unique values** per label.

---

### 2. Use Histograms for Latency

**❌ BAD** - Using average from counter:
```python
total_duration = Counter('total_duration', 'Total duration')
request_count = Counter('request_count', 'Requests')

# Average = total_duration / request_count  # ❌ Loses distribution info
```

**✅ GOOD** - Using histogram:
```python
request_duration = Histogram(
    'request_duration_seconds',
    'Request duration',
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0]  # ✅ Can calculate percentiles
)
```

---

### 3. Naming Conventions

Follow Prometheus naming conventions:

```python
# ✅ GOOD names:
llm_inference_count            # Counter - ends with _total or _count
llm_inference_latency_seconds  # Histogram - includes unit (_seconds)
active_connections             # Gauge - describes current state

# ❌ BAD names:
LLMInferenceCount             # Use snake_case, not CamelCase
llm_latency_ms                # Use base units (seconds, not milliseconds)
tool_calls_total_count        # Redundant (_total already implies count)
```

---

### 4. Metric Scope

**Define metrics globally, use them locally**:

```python
# ✅ GOOD - Define once in metrics.py
# backend/observability/metrics.py
request_count = Counter('request_count', 'Requests')

# Use everywhere
# backend/services/agent.py
from observability.metrics import request_count
request_count.inc()

# ❌ BAD - Don't redefine in multiple files
```

---

### 5. Error Handling

**Always record metrics even on errors**:

```python
@contextmanager
def record_operation():
    start_time = time.time()
    status = "error"  # Default to error
    
    try:
        yield
        status = "success"  # Only set on success
    finally:
        # Always record, even on exception
        duration = time.time() - start_time
        operation_count.labels(status=status).inc()
        operation_duration.observe(duration)
```

---

## 📚 Summary

### Python → Prometheus → Grafana Flow

1. **Python Code**: Use `prometheus_client` to define and record metrics
2. **Expose Endpoint**: FastAPI serves metrics at `/metrics`
3. **Prometheus Scrapes**: Every 15s, Prometheus fetches and stores metrics
4. **Grafana Queries**: Dashboards query Prometheus with PromQL
5. **Visualization**: Users see real-time charts and stats

### Key Metrics in This Project

| Metric | Type | Purpose | LangGraph Integration |
|--------|------|---------|----------------------|
| `llm_inference_count` | Counter | Count LLM calls | Recorded in `instrumented_llm_call()` wrapper |
| `llm_inference_latency_seconds` | Histogram | Measure LLM response time | Recorded with timing in wrapper |
| `tool_invocation_count` | Counter | Count tool calls | Recorded in `record_tool_call()` context manager |
| `node_execution_latency_seconds` | Histogram | Measure node execution time | Recorded in `record_node_duration()` wrapping each LangGraph node |
| `agent_execution_count` | Counter | Count agent runs | Recorded once per agent.run() invocation |
| `llm_cost_total_usd` | Counter | Track cumulative cost | Calculated from token usage in LLM wrapper |

### Files to Know

| File | Purpose |
|------|---------|
| `backend/observability/metrics.py` | Metric definitions |
| `backend/observability/llm_instrumentation.py` | LLM call wrapper with metrics |
| `backend/services/agent.py` | LangGraph nodes with `record_node_duration()` |
| `backend/services/tools.py` | Tool wrappers with `record_tool_call()` |
| `backend/main.py` | FastAPI `/metrics` endpoint setup |
| `observability/prometheus.yml` | Prometheus scrape configuration |
| `observability/grafana/dashboards/*.json` | Pre-built Grafana dashboards |

---

**End of Guide**

For more information:
- [DOCKER_ARCHITECTURE.md](DOCKER_ARCHITECTURE.md) - Container setup
- [MONITORING_TEST_PROMPTS.md](MONITORING_TEST_PROMPTS.md) - Test prompts to generate metrics
- [docs/09_MONITORING_PROMPT.md](docs/09_MONITORING_PROMPT.md) - Original monitoring specification
