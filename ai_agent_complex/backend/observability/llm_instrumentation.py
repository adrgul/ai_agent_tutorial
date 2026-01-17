"""
LLM instrumentation wrappers for observability.

Provides instrumented wrappers around LangChain LLM calls to automatically
collect metrics on token usage, costs, and latency.

Usage:
    # Instead of calling llm directly:
    # response = await llm.ainvoke(messages)
    
    # Use instrumented wrapper:
    response = await instrumented_llm_call(llm, messages, model="gpt-4-turbo-preview")
"""
import time
import logging
from typing import Any, List, Optional, Dict
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel

from observability.metrics import (
    record_llm_usage,
    record_error,
    METRICS_ENABLED,
    model_fallback_count,
    max_retries_exceeded_count,
)
from observability.correlation import get_request_id
from observability.prompt_lineage import get_prompt_tracker

logger = logging.getLogger(__name__)


async def instrumented_llm_call(
    llm: BaseChatModel,
    messages: List[BaseMessage],
    model: str,
    tenant: Optional[str] = None,
    agent_execution_id: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Instrumented LLM call with automatic metrics collection.
    
    Wraps LangChain LLM.ainvoke() to collect:
    - Token usage (prompt/completion/total)
    - Estimated cost
    - Call duration
    - Error tracking
    - Prompt lineage tracking
    
    Args:
        llm: LangChain LLM instance
        messages: List of messages to send
        model: Model name for metrics labeling
        tenant: Optional tenant override
        agent_execution_id: Optional agent execution ID for prompt lineage
        **kwargs: Additional arguments passed to llm.ainvoke()
    
    Returns:
        LLM response (AIMessage)
    
    Raises:
        Exception: Re-raises any LLM errors after recording metrics
    
    Usage:
        response = await instrumented_llm_call(
            llm=self.llm,
            messages=conversation,
            model="gpt-4-turbo-preview",
            agent_execution_id="exec_123"
        )
    """
    request_id = get_request_id()
    start_time = time.time()
    
    # Track prompt lineage
    if agent_execution_id:
        tracker = get_prompt_tracker()
        tracker.track_prompt(
            messages=messages,
            model_name=model,
            agent_execution_id=agent_execution_id
        )
    
    logger.info(f"LLM call starting [model={model}, request_id={request_id}]")
    
    try:
        # Make actual LLM call
        response = await llm.ainvoke(messages, **kwargs)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract token usage from response
        # LangChain provides usage_metadata in response
        usage = getattr(response, 'usage_metadata', None) or {}
        
        prompt_tokens = usage.get('input_tokens', 0)
        completion_tokens = usage.get('output_tokens', 0)
        
        # Fallback: some models provide response_metadata
        if prompt_tokens == 0 and completion_tokens == 0:
            response_metadata = getattr(response, 'response_metadata', {})
            token_usage = response_metadata.get('token_usage', {})
            prompt_tokens = token_usage.get('prompt_tokens', 0)
            completion_tokens = token_usage.get('completion_tokens', 0)
        
        # Record metrics
        if METRICS_ENABLED and (prompt_tokens > 0 or completion_tokens > 0):
            record_llm_usage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_seconds=duration,
                tenant=tenant
            )
            
            logger.info(
                f"LLM call completed [model={model}, duration={duration:.2f}s, "
                f"tokens={prompt_tokens}+{completion_tokens}={prompt_tokens+completion_tokens}, "
                f"request_id={request_id}]"
            )
        else:
            logger.warning(
                f"LLM call completed but no token usage found [model={model}, "
                f"duration={duration:.2f}s, request_id={request_id}]"
            )
        
        return response
        
    except Exception as e:
        # Record error
        duration = time.time() - start_time
        record_error(error_type="llm_error", node="llm_call")
        
        logger.error(
            f"LLM call failed [model={model}, duration={duration:.2f}s, "
            f"error={type(e).__name__}, request_id={request_id}]: {e}"
        )
        
        raise


def instrumented_llm_call_sync(
    llm: BaseChatModel,
    messages: List[BaseMessage],
    model: str,
    tenant: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Synchronous version of instrumented LLM call.
    
    Use when you can't use async (rare in LangGraph).
    """
    request_id = get_request_id()
    start_time = time.time()
    
    logger.info(f"LLM call starting (sync) [model={model}, request_id={request_id}]")
    
    try:
        # Make actual LLM call
        response = llm.invoke(messages, **kwargs)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract token usage
        usage = getattr(response, 'usage_metadata', None) or {}
        prompt_tokens = usage.get('input_tokens', 0)
        completion_tokens = usage.get('output_tokens', 0)
        
        # Fallback
        if prompt_tokens == 0 and completion_tokens == 0:
            response_metadata = getattr(response, 'response_metadata', {})
            token_usage = response_metadata.get('token_usage', {})
            prompt_tokens = token_usage.get('prompt_tokens', 0)
            completion_tokens = token_usage.get('completion_tokens', 0)
        
        # Record metrics
        if METRICS_ENABLED and (prompt_tokens > 0 or completion_tokens > 0):
            record_llm_usage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_seconds=duration,
                tenant=tenant
            )
        
        logger.info(
            f"LLM call completed (sync) [model={model}, duration={duration:.2f}s, "
            f"tokens={prompt_tokens}+{completion_tokens}, request_id={request_id}]"
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        record_error(error_type="llm_error", node="llm_call")
        
        logger.error(
            f"LLM call failed (sync) [model={model}, duration={duration:.2f}s, "
            f"error={type(e).__name__}, request_id={request_id}]: {e}"
        )
        
        raise


class InstrumentedLLM:
    """
    Wrapper class that instruments all LLM calls automatically.
    
    Usage:
        # Wrap your LLM instance
        llm = ChatOpenAI(model="gpt-4-turbo-preview", ...)
        instrumented_llm = InstrumentedLLM(llm, model_name="gpt-4-turbo-preview")
        
        # Use as normal
        response = await instrumented_llm.ainvoke(messages)
    """
    
    def __init__(self, llm: BaseChatModel, model_name: str, tenant: Optional[str] = None):
        self.llm = llm
        self.model_name = model_name
        self.tenant = tenant
    
    async def ainvoke(self, messages: List[BaseMessage], **kwargs) -> Any:
        """Async invoke with instrumentation."""
        return await instrumented_llm_call(
            llm=self.llm,
            messages=messages,
            model=self.model_name,
            tenant=self.tenant,
            **kwargs
        )
    
    def invoke(self, messages: List[BaseMessage], **kwargs) -> Any:
        """Sync invoke with instrumentation."""
        return instrumented_llm_call_sync(
            llm=self.llm,
            messages=messages,
            model=self.model_name,
            tenant=self.tenant,
            **kwargs
        )
    
    def __getattr__(self, name):
        """Forward all other attributes to underlying LLM."""
        return getattr(self.llm, name)


async def instrumented_llm_call_with_fallback(
    primary_llm: BaseChatModel,
    fallback_llm: BaseChatModel,
    messages: List[BaseMessage],
    primary_model: str,
    fallback_model: str,
    max_retries: int = 2,
    tenant: Optional[str] = None,
    agent_execution_id: Optional[str] = None,
    **kwargs
) -> Any:
    """
    Instrumented LLM call with automatic fallback to secondary model.
    
    Tracks model fallback paths via model_fallback_count metric.
    
    Args:
        primary_llm: Primary LLM instance
        fallback_llm: Fallback LLM instance
        messages: Messages to send
        primary_model: Primary model name
        fallback_model: Fallback model name
        max_retries: Maximum retry attempts before giving up
        tenant: Optional tenant
        agent_execution_id: Optional agent execution ID
        **kwargs: Additional arguments
    
    Returns:
        LLM response
    
    Raises:
        Exception: If both primary and fallback fail
    """
    request_id = get_request_id()
    
    # Try primary model first
    for attempt in range(max_retries):
        try:
            logger.info(
                f"Attempting primary model [model={primary_model}, "
                f"attempt={attempt+1}/{max_retries}, request_id={request_id}]"
            )
            response = await instrumented_llm_call(
                llm=primary_llm,
                messages=messages,
                model=primary_model,
                tenant=tenant,
                agent_execution_id=agent_execution_id,
                **kwargs
            )
            return response
        except Exception as e:
            logger.warning(
                f"Primary model failed [model={primary_model}, "
                f"attempt={attempt+1}/{max_retries}, error={type(e).__name__}]: {e}"
            )
            if attempt == max_retries - 1:
                # Exceeded retries on primary, try fallback
                break
    
    # Track fallback
    if METRICS_ENABLED:
        model_fallback_count.labels(
            from_model=primary_model,
            to_model=fallback_model
        ).inc()
    
    logger.info(
        f"Falling back to secondary model [from={primary_model}, "
        f"to={fallback_model}, request_id={request_id}]"
    )
    
    # Try fallback model
    for attempt in range(max_retries):
        try:
            logger.info(
                f"Attempting fallback model [model={fallback_model}, "
                f"attempt={attempt+1}/{max_retries}, request_id={request_id}]"
            )
            response = await instrumented_llm_call(
                llm=fallback_llm,
                messages=messages,
                model=fallback_model,
                tenant=tenant,
                agent_execution_id=agent_execution_id,
                **kwargs
            )
            return response
        except Exception as e:
            logger.error(
                f"Fallback model failed [model={fallback_model}, "
                f"attempt={attempt+1}/{max_retries}, error={type(e).__name__}]: {e}"
            )
            if attempt == max_retries - 1:
                # Exceeded retries on fallback too
                if METRICS_ENABLED:
                    max_retries_exceeded_count.inc()
                raise

