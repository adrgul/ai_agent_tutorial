"""
Prometheus metrics definitions for AI Agent observability.

This module defines all Prometheus metrics used to monitor the AI agent's
performance, cost, errors, and behavior. Metrics are designed to be:
- Low cardinality (avoid raw user_id as labels)
- Production-ready (support multi-tenant scenarios)
- AI-agent specific (LLM tokens, costs, tool usage)

Best practices:
- Use tenant/environment labels instead of user_id
- Measure latency with histograms (not gauges)
- Track both successes and failures
- Include cost tracking for LLM usage
"""
import os
import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Environment-based control: disable metrics in tests or when not needed
METRICS_ENABLED = os.getenv("ENABLE_METRICS", "true").lower() == "true"

# Lazy import prometheus_client to avoid dependency errors if not installed
if METRICS_ENABLED:
    try:
        from prometheus_client import (
            Counter, Histogram, Gauge, Info,
            CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
        )
        
        # Create a separate registry for cleaner testing/isolation
        registry = CollectorRegistry()
        
        logger.info("Prometheus metrics initialized")
    except ImportError:
        logger.warning("prometheus_client not installed, metrics disabled")
        METRICS_ENABLED = False
        registry = None
else:
    logger.info("Metrics disabled via ENABLE_METRICS=false")
    registry = None


# ============================================================================
# METRIC DEFINITIONS
# ============================================================================

if METRICS_ENABLED:
    # ------------------------------------------------------------------------
    # Request Metrics
    # Measure end-to-end agent request performance and success/failure rates
    # ------------------------------------------------------------------------
    
    agent_requests_total = Counter(
        name='agent_requests_total',
        documentation='Total number of agent requests processed',
        labelnames=['status', 'tenant', 'environment'],
        registry=registry
    )
    # Why: Track request volume and success rate per tenant/environment
    # Usage: agent_requests_total{status="success",tenant="default",environment="prod"}
    
    agent_request_duration_seconds = Histogram(
        name='agent_request_duration_seconds',
        documentation='End-to-end agent request latency in seconds',
        labelnames=['tenant', 'environment'],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],  # AI agents can be slow
        registry=registry
    )
    # Why: Measure user-perceived latency, identify slow requests
    # Usage: histogram_quantile(0.95, agent_request_duration_seconds_bucket{tenant="default"})
    
    # ------------------------------------------------------------------------
    # LLM Usage Metrics
    # Track token consumption and estimated costs for LLM calls
    # ------------------------------------------------------------------------
    
    agent_llm_tokens_total = Counter(
        name='agent_llm_tokens_total',
        documentation='Total tokens used in LLM calls',
        labelnames=['model', 'direction', 'tenant', 'environment'],
        registry=registry
    )
    # Why: Monitor token usage for cost optimization and quota management
    # direction: prompt (input tokens) | completion (output tokens) | total
    # Usage: rate(agent_llm_tokens_total{direction="prompt",model="gpt-4"}[5m])
    
    agent_llm_cost_usd_total = Counter(
        name='agent_llm_cost_usd_total',
        documentation='Estimated LLM costs in USD',
        labelnames=['model', 'tenant', 'environment'],
        registry=registry
    )
    # Why: Track real-time cost accumulation, set budget alerts
    # Usage: sum(agent_llm_cost_usd_total{tenant="default"})
    
    agent_llm_call_duration_seconds = Histogram(
        name='agent_llm_call_duration_seconds',
        documentation='LLM API call latency in seconds',
        labelnames=['model', 'tenant', 'environment'],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
        registry=registry
    )
    # Why: Measure LLM API response time, detect performance degradation
    # Usage: histogram_quantile(0.99, agent_llm_call_duration_seconds_bucket{})
    
    # ------------------------------------------------------------------------
    # Node Metrics
    # Measure execution time of individual LangGraph nodes
    # ------------------------------------------------------------------------
    
    agent_node_duration_seconds = Histogram(
        name='agent_node_duration_seconds',
        documentation='LangGraph node execution duration in seconds',
        labelnames=['node', 'environment'],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
        registry=registry
    )
    # Why: Identify bottleneck nodes in the agent workflow
    # Usage: sum by (node) (rate(agent_node_duration_seconds_sum[5m]))
    
    agent_node_executions_total = Counter(
        name='agent_node_executions_total',
        documentation='Total number of node executions',
        labelnames=['node', 'environment'],
        registry=registry
    )
    # Why: Track how often each node runs (useful for conditional flows)
    # Usage: rate(agent_node_executions_total{node="agent_decide"}[5m])
    
    # ------------------------------------------------------------------------
    # Tool Metrics
    # Track external tool/API calls and their success rates
    # ------------------------------------------------------------------------
    
    agent_tool_calls_total = Counter(
        name='agent_tool_calls_total',
        documentation='Total number of tool calls',
        labelnames=['tool', 'status', 'environment'],
        registry=registry
    )
    # Why: Monitor which tools are used most, track tool reliability
    # status: success | error
    # Usage: rate(agent_tool_calls_total{status="error"}[5m])
    
    agent_tool_duration_seconds = Histogram(
        name='agent_tool_duration_seconds',
        documentation='Tool execution duration in seconds',
        labelnames=['tool', 'environment'],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
        registry=registry
    )
    # Why: Measure external API latency, identify slow integrations
    # Usage: histogram_quantile(0.95, agent_tool_duration_seconds_bucket{tool="weather"})
    
    # ------------------------------------------------------------------------
    # Error Metrics
    # Track errors by type and location for debugging
    # ------------------------------------------------------------------------
    
    agent_errors_total = Counter(
        name='agent_errors_total',
        documentation='Total number of errors in agent execution',
        labelnames=['error_type', 'node', 'environment'],
        registry=registry
    )
    # Why: Track error frequency and patterns, set alerts on spikes
    # error_type: llm_error | tool_error | validation_error | unknown
    # Usage: rate(agent_errors_total{error_type="llm_error"}[5m])
    
    # ------------------------------------------------------------------------
    # RAG Metrics
    # Track RAG retrieval performance and quality
    # ------------------------------------------------------------------------
    
    agent_rag_retrievals_total = Counter(
        name='agent_rag_retrievals_total',
        documentation='Total number of RAG retrievals',
        labelnames=['status', 'environment'],
        registry=registry
    )
    # Why: Monitor RAG usage and success rate
    # Usage: rate(agent_rag_retrievals_total{status="success"}[5m])
    
    agent_rag_chunks_retrieved = Histogram(
        name='agent_rag_chunks_retrieved',
        documentation='Number of chunks retrieved per RAG query',
        labelnames=['environment'],
        buckets=[0, 1, 2, 5, 10, 20, 50],
        registry=registry
    )
    # Why: Understand retrieval patterns, optimize chunk counts
    # Usage: histogram_quantile(0.90, agent_rag_chunks_retrieved_bucket{})
    
    agent_rag_duration_seconds = Histogram(
        name='agent_rag_duration_seconds',
        documentation='RAG retrieval latency in seconds',
        labelnames=['environment'],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0],
        registry=registry
    )
    # Why: Measure vector search performance
    # Usage: histogram_quantile(0.95, agent_rag_duration_seconds_bucket{})
    
    # ------------------------------------------------------------------------
    # System Info
    # Metadata about the agent deployment
    # ------------------------------------------------------------------------
    
    agent_info = Info(
        name='agent_info',
        documentation='Agent system information',
        registry=registry
    )
    # Why: Track version, environment, and configuration in metrics
    # Usage: agent_info{version="1.0.0",environment="prod"}
    
    # ------------------------------------------------------------------------
    # Additional Metrics per 09_MONITORING_PROMPT.md
    # ------------------------------------------------------------------------
    
    # LLM inference metrics (spec-compliant names)
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
    
    llm_inference_token_input_total = Counter(
        name='llm_inference_token_input_total',
        documentation='Total input tokens processed by LLM',
        labelnames=['model'],
        registry=registry
    )
    
    llm_inference_token_output_total = Counter(
        name='llm_inference_token_output_total',
        documentation='Total output tokens generated by LLM',
        labelnames=['model'],
        registry=registry
    )
    
    llm_cost_total_usd = Counter(
        name='llm_cost_total_usd',
        documentation='Total cost in USD for LLM inference',
        labelnames=['model'],
        registry=registry
    )
    
    # Agent workflow metrics (spec-compliant names)
    agent_execution_count = Counter(
        name='agent_execution_count',
        documentation='Total number of agent executions',
        registry=registry
    )
    
    agent_execution_latency_seconds = Histogram(
        name='agent_execution_latency_seconds',
        documentation='Latency of agent execution in seconds',
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
        registry=registry
    )
    
    node_execution_latency_seconds = Histogram(
        name='node_execution_latency_seconds',
        documentation='Latency of individual node execution in seconds',
        labelnames=['node'],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        registry=registry
    )
    
    tool_invocation_count = Counter(
        name='tool_invocation_count',
        documentation='Total number of tool invocations',
        labelnames=['tool'],
        registry=registry
    )
    
    rag_recall_rate = Gauge(
        name='rag_recall_rate',
        documentation='RAG recall rate (derived relevance metric)',
        registry=registry
    )
    
    # Error & fallback metrics
    model_fallback_count = Counter(
        name='model_fallback_count',
        documentation='Total number of model fallback occurrences',
        labelnames=['from_model', 'to_model'],
        registry=registry
    )
    
    max_retries_exceeded_count = Counter(
        name='max_retries_exceeded_count',
        documentation='Total number of times max retries were exceeded',
        registry=registry
    )
    
    # RAG metrics (spec-compliant names)
    rag_chunk_retrieval_count = Counter(
        name='rag_chunk_retrieval_count',
        documentation='Total number of RAG chunk retrievals',
        registry=registry
    )
    
    rag_retrieved_chunk_relevance_score_avg = Gauge(
        name='rag_retrieved_chunk_relevance_score_avg',
        documentation='Average relevance score of retrieved chunks',
        registry=registry
    )
    
    vector_db_query_latency_seconds = Histogram(
        name='vector_db_query_latency_seconds',
        documentation='Latency of vector database queries in seconds',
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
        registry=registry
    )
    
    embedding_generation_count = Counter(
        name='embedding_generation_count',
        documentation='Total number of embedding generations',
        registry=registry
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def init_metrics(environment: str = "dev", version: str = "unknown"):
    """
    Initialize metrics with system information.
    
    Call this once at application startup to set metadata labels.
    
    Args:
        environment: Deployment environment (dev/staging/prod)
        version: Application version string
    """
    if not METRICS_ENABLED:
        return
    
    agent_info.info({
        'environment': environment,
        'version': version,
        'initialized_at': datetime.utcnow().isoformat()
    })
    logger.info(f"Metrics initialized for environment={environment}, version={version}")


def get_current_tenant() -> str:
    """
    Get current tenant identifier for metrics labeling.
    
    In production, this would extract tenant from request context.
    For now, we use a default tenant to avoid high cardinality.
    
    Returns:
        Tenant identifier (default: "default")
    
    Note: Do NOT use raw user_id as tenant - it creates high cardinality!
    Instead, use tenant groups or organization IDs.
    """
    # In a real multi-tenant system, this would come from:
    # - Request headers (X-Tenant-ID)
    # - JWT claims
    # - User → Tenant mapping
    return os.getenv("TENANT_ID", "default")


def get_environment() -> str:
    """Get current environment for metrics labeling."""
    return os.getenv("ENVIRONMENT", "dev")


# ------------------------------------------------------------------------
# Request-Level Instrumentation
# ------------------------------------------------------------------------

@contextmanager
def record_agent_request(status: str = "success"):
    """
    Context manager to record end-to-end agent request metrics.
    
    Usage:
        with record_agent_request(status="success"):
            result = await agent.run(...)
    
    Args:
        status: Request status (success/error)
    
    Records:
        - Total request count
        - Request duration
    """
    if not METRICS_ENABLED:
        yield
        return
    
    tenant = get_current_tenant()
    env = get_environment()
    start_time = time.time()
    
    try:
        yield
        # Success path
        agent_requests_total.labels(
            status=status,
            tenant=tenant,
            environment=env
        ).inc()
    except Exception as e:
        # Error path
        agent_requests_total.labels(
            status="error",
            tenant=tenant,
            environment=env
        ).inc()
        raise
    finally:
        # Always record duration
        duration = time.time() - start_time
        agent_request_duration_seconds.labels(
            tenant=tenant,
            environment=env
        ).observe(duration)


class AgentRequestContext:
    """
    Context manager for complete agent request instrumentation.
    
    Provides cleaner API for recording requests with automatic error handling.
    
    Usage:
        async with AgentRequestContext() as ctx:
            result = await agent.run(...)
            ctx.set_status("success")
    """
    
    def __init__(self):
        self.status = "error"  # Default to error, caller must set success
        self.start_time = None
        self.tenant = None
        self.env = None
    
    async def __aenter__(self):
        if METRICS_ENABLED:
            self.start_time = time.time()
            self.tenant = get_current_tenant()
            self.env = get_environment()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not METRICS_ENABLED:
            return False
        
        # If exception occurred, ensure status is error
        if exc_type is not None:
            self.status = "error"
        
        # Record metrics
        agent_requests_total.labels(
            status=self.status,
            tenant=self.tenant,
            environment=self.env
        ).inc()
        
        duration = time.time() - self.start_time
        agent_request_duration_seconds.labels(
            tenant=self.tenant,
            environment=self.env
        ).observe(duration)
        
        return False  # Don't suppress exceptions
    
    def set_status(self, status: str):
        """Set final request status (success/error)."""
        self.status = status


# ------------------------------------------------------------------------
# LLM Instrumentation
# ------------------------------------------------------------------------

def record_llm_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_seconds: float,
    tenant: Optional[str] = None
):
    """
    Record LLM usage metrics including tokens and estimated cost.
    
    Args:
        model: LLM model name (e.g., "gpt-4-turbo-preview")
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        duration_seconds: API call duration
        tenant: Optional tenant override
    
    Cost calculation based on OpenAI pricing (as of Jan 2026):
        - gpt-4-turbo: $0.01/1K prompt, $0.03/1K completion
        - gpt-3.5-turbo: $0.0015/1K prompt, $0.002/1K completion
    
    Note: Update pricing table as models change!
    """
    if not METRICS_ENABLED:
        return
    
    tenant = tenant or get_current_tenant()
    env = get_environment()
    total_tokens = prompt_tokens + completion_tokens
    
    # Record token counts (original metrics with tenant/environment labels)
    agent_llm_tokens_total.labels(
        model=model,
        direction="prompt",
        tenant=tenant,
        environment=env
    ).inc(prompt_tokens)
    
    agent_llm_tokens_total.labels(
        model=model,
        direction="completion",
        tenant=tenant,
        environment=env
    ).inc(completion_tokens)
    
    agent_llm_tokens_total.labels(
        model=model,
        direction="total",
        tenant=tenant,
        environment=env
    ).inc(total_tokens)
    
    # Record duration (original metric)
    agent_llm_call_duration_seconds.labels(
        model=model,
        tenant=tenant,
        environment=env
    ).observe(duration_seconds)
    
    # Estimate cost (simplified pricing)
    cost_usd = _estimate_llm_cost(model, prompt_tokens, completion_tokens)
    agent_llm_cost_usd_total.labels(
        model=model,
        tenant=tenant,
        environment=env
    ).inc(cost_usd)
    
    # ALSO record spec-compliant metrics (no tenant/environment labels)
    llm_inference_count.labels(model=model).inc()
    llm_inference_token_input_total.labels(model=model).inc(prompt_tokens)
    llm_inference_token_output_total.labels(model=model).inc(completion_tokens)
    llm_inference_latency_seconds.labels(model=model).observe(duration_seconds)
    llm_cost_total_usd.labels(model=model).inc(cost_usd)


def _estimate_llm_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate LLM cost in USD based on token usage.
    
    Pricing table (USD per 1K tokens) - Updated Jan 2026:
    """
    # Pricing per 1K tokens (input, output) - Updated to match 09_MONITORING_PROMPT.md
    PRICING = {
        "gpt-4-turbo-preview": (0.01, 0.03),
        "gpt-4": (0.03, 0.06),
        "gpt-4.1": (0.03, 0.06),  # Added from spec
        "gpt-3.5-turbo": (0.0015, 0.002),
        "gpt-4o": (0.005, 0.015),
        "gpt-4o-mini": (0.00015, 0.0006),  # Added from spec: $0.15/$0.60 per 1M tokens
    }
    
    # Default to gpt-4 pricing if model unknown
    input_price, output_price = PRICING.get(model, PRICING["gpt-4"])
    
    cost = (prompt_tokens / 1000.0 * input_price) + \
           (completion_tokens / 1000.0 * output_price)
    
    return cost


@contextmanager
def track_llm_call(model: str, tenant: Optional[str] = None):
    """
    Context manager to automatically track LLM call duration.
    
    Usage:
        with track_llm_call(model="gpt-4-turbo-preview") as tracker:
            response = await llm.ainvoke(messages)
            tracker.record_tokens(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens
            )
    
    Returns:
        Tracker object with record_tokens() method
    """
    
    class LLMCallTracker:
        def __init__(self, model, tenant, start_time):
            self.model = model
            self.tenant = tenant
            self.start_time = start_time
        
        def record_tokens(self, prompt_tokens: int, completion_tokens: int):
            """Record token usage after LLM call completes."""
            duration = time.time() - self.start_time
            record_llm_usage(
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_seconds=duration,
                tenant=self.tenant
            )
    
    if not METRICS_ENABLED:
        # Return dummy tracker that does nothing
        class DummyTracker:
            def record_tokens(self, *args, **kwargs):
                pass
        yield DummyTracker()
        return
    
    start_time = time.time()
    tracker = LLMCallTracker(model, tenant or get_current_tenant(), start_time)
    yield tracker


# ------------------------------------------------------------------------
# Node Instrumentation
# ------------------------------------------------------------------------

@contextmanager
def record_node_duration(node_name: str):
    """
    Context manager to record LangGraph node execution time.
    
    Usage:
        with record_node_duration("agent_decide"):
            state = await _agent_decide_node(state)
    
    Args:
        node_name: Name of the LangGraph node being executed
    
    Records:
        - Node execution count
        - Node execution duration
    """
    if not METRICS_ENABLED:
        yield
        return
    
    env = get_environment()
    start_time = time.time()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        
        agent_node_executions_total.labels(
            node=node_name,
            environment=env
        ).inc()
        
        agent_node_duration_seconds.labels(
            node=node_name,
            environment=env
        ).observe(duration)


# ------------------------------------------------------------------------
# Tool Instrumentation
# ------------------------------------------------------------------------

@contextmanager
def record_tool_call(tool_name: str):
    """
    Context manager to record tool call metrics.
    
    Usage:
        with record_tool_call("weather"):
            result = await weather_tool.execute(city="London")
    
    Args:
        tool_name: Name of the tool being called
    
    Records:
        - Tool call count (success/error)
        - Tool call duration
    """
    if not METRICS_ENABLED:
        yield
        return
    
    env = get_environment()
    start_time = time.time()
    status = "success"
    
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time
        
        agent_tool_calls_total.labels(
            tool=tool_name,
            status=status,
            environment=env
        ).inc()
        
        agent_tool_duration_seconds.labels(
            tool=tool_name,
            environment=env
        ).observe(duration)


# ------------------------------------------------------------------------
# Error Instrumentation
# ------------------------------------------------------------------------

def record_error(error_type: str, node: str = "unknown"):
    """
    Record an error occurrence.
    
    Args:
        error_type: Type of error (llm_error, tool_error, validation_error, etc.)
        node: Node where error occurred
    
    Error types:
        - llm_error: LLM API failures, rate limits, etc.
        - tool_error: External tool/API failures
        - validation_error: Input validation failures
        - rag_error: RAG retrieval failures
        - unknown: Unclassified errors
    """
    if not METRICS_ENABLED:
        return
    
    env = get_environment()
    
    agent_errors_total.labels(
        error_type=error_type,
        node=node,
        environment=env
    ).inc()


# ------------------------------------------------------------------------
# RAG Instrumentation
# ------------------------------------------------------------------------

@contextmanager
def record_rag_retrieval():
    """
    Context manager to record RAG retrieval metrics.
    
    Usage:
        with record_rag_retrieval() as rag_tracker:
            chunks = await retrieval_service.retrieve(query)
            rag_tracker.set_chunks(len(chunks))
            rag_tracker.set_status("success")
    
    Records:
        - RAG retrieval count
        - Number of chunks retrieved
        - Retrieval duration
    """
    
    class RAGTracker:
        def __init__(self):
            self.status = "error"
            self.chunk_count = 0
        
        def set_status(self, status: str):
            self.status = status
        
        def set_chunks(self, count: int):
            self.chunk_count = count
    
    if not METRICS_ENABLED:
        yield RAGTracker()
        return
    
    env = get_environment()
    start_time = time.time()
    tracker = RAGTracker()
    
    try:
        yield tracker
    finally:
        duration = time.time() - start_time
        
        agent_rag_retrievals_total.labels(
            status=tracker.status,
            environment=env
        ).inc()
        
        if tracker.chunk_count > 0:
            agent_rag_chunks_retrieved.labels(
                environment=env
            ).observe(tracker.chunk_count)
        
        agent_rag_duration_seconds.labels(
            environment=env
        ).observe(duration)


# ============================================================================
# METRICS EXPORT
# ============================================================================

def get_metrics_content():
    """
    Get Prometheus metrics in text format for /metrics endpoint.
    
    Returns:
        Tuple of (metrics_text, content_type)
    """
    if not METRICS_ENABLED:
        return "# Metrics disabled\n", "text/plain"
    
    return generate_latest(registry), CONTENT_TYPE_LATEST


def get_registry():
    """Get the Prometheus registry (for testing or custom export)."""
    return registry
