"""
Observability module for AI Agent monitoring.

Provides Prometheus metrics, request correlation, and instrumentation helpers.
"""
from .metrics import (
    METRICS_ENABLED,
    init_metrics,
    record_agent_request,
    record_llm_usage,
    record_node_duration,
    record_tool_call,
    record_error,
    get_current_tenant,
    get_metrics_content,
    AgentRequestContext,
)
from .correlation import get_request_id, set_request_id, correlation_context

__all__ = [
    "METRICS_ENABLED",
    "init_metrics",
    "record_agent_request",
    "record_llm_usage",
    "record_node_duration",
    "record_tool_call",
    "record_error",
    "get_current_tenant",
    "get_metrics_content",
    "AgentRequestContext",
    "get_request_id",
    "set_request_id",
    "correlation_context",
]
