"""
Request correlation for distributed tracing.

Provides request_id/trace_id generation and propagation through the agent execution.
This enables correlating all logs, metrics, and events from a single user request.

Best practices:
- Generate request_id at API entry point
- Propagate through LangGraph state
- Include in all log messages
- Use for debugging multi-step workflows
"""
import uuid
import logging
from contextvars import ContextVar
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# Thread-local storage for request correlation ID
# Using ContextVar for async-safe storage
_request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def generate_request_id() -> str:
    """
    Generate a new unique request ID.
    
    Returns:
        UUID string in format: "req_abc123..."
    
    Note: Shortened UUID for readability (first 12 chars)
    """
    return f"req_{uuid.uuid4().hex[:12]}"


def get_request_id() -> Optional[str]:
    """
    Get current request ID from context.
    
    Returns:
        Current request ID or None if not set
    
    Usage:
        request_id = get_request_id()
        logger.info(f"Processing request {request_id}")
    """
    return _request_id_var.get()


def set_request_id(request_id: str):
    """
    Set request ID in current context.
    
    Args:
        request_id: Request identifier to set
    
    Usage:
        set_request_id(generate_request_id())
    """
    _request_id_var.set(request_id)
    logger.debug(f"Request ID set: {request_id}")


def clear_request_id():
    """Clear request ID from context (cleanup)."""
    _request_id_var.set(None)


@contextmanager
def correlation_context(request_id: Optional[str] = None):
    """
    Context manager for request correlation.
    
    Automatically generates, sets, and cleans up request ID.
    
    Usage:
        with correlation_context() as req_id:
            logger.info(f"Processing {req_id}")
            # All code here has access to request_id
    
    Args:
        request_id: Optional request ID, generates new one if not provided
    
    Yields:
        The request ID being used
    """
    # Generate new ID if not provided
    if request_id is None:
        request_id = generate_request_id()
    
    # Store previous value for restoration
    previous_id = get_request_id()
    
    try:
        set_request_id(request_id)
        yield request_id
    finally:
        # Restore previous value (for nested contexts)
        if previous_id is not None:
            set_request_id(previous_id)
        else:
            clear_request_id()


def add_request_id_to_state(state: dict) -> dict:
    """
    Add request_id to LangGraph state if not already present.
    
    Args:
        state: LangGraph state dictionary
    
    Returns:
        Updated state with request_id
    
    Usage:
        initial_state = add_request_id_to_state(initial_state)
    """
    if "request_id" not in state:
        state["request_id"] = get_request_id() or generate_request_id()
    
    return state


def get_request_id_from_state(state: dict) -> Optional[str]:
    """
    Extract request_id from LangGraph state.
    
    Args:
        state: LangGraph state dictionary
    
    Returns:
        Request ID from state or None
    """
    return state.get("request_id")


class CorrelatedLogger:
    """
    Logger wrapper that automatically includes request_id in all log messages.
    
    Usage:
        logger = CorrelatedLogger(__name__)
        logger.info("Processing request")
        # Output: "Processing request [req_abc123]"
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _format_message(self, msg: str) -> str:
        """Add request_id to message if available."""
        request_id = get_request_id()
        if request_id:
            return f"{msg} [request_id={request_id}]"
        return msg
    
    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(self._format_message(msg), *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self.logger.info(self._format_message(msg), *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(self._format_message(msg), *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self.logger.error(self._format_message(msg), *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(self._format_message(msg), *args, **kwargs)


# Example: Enhanced logging format that includes request_id
def configure_correlated_logging():
    """
    Configure logging format to include request_id automatically.
    
    Call this during application startup to enable request correlation in logs.
    
    Example log format:
        2026-01-13 10:15:30 - agent - INFO - Processing message [req_abc123]
    """
    
    class CorrelationFilter(logging.Filter):
        """Add request_id to log records."""
        
        def filter(self, record):
            record.request_id = get_request_id() or "no-request-id"
            return True
    
    # Add filter to root logger
    logging.root.addFilter(CorrelationFilter())
    
    # Update format to include request_id
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(request_id)s]'
    )
    
    # Apply to all handlers
    for handler in logging.root.handlers:
        handler.setFormatter(formatter)
    
    logger.info("Correlation logging configured")
