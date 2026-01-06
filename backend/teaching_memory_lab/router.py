"""
Router - Decide which nodes to execute based on memory mode and heuristics.

Routing logic:
- rolling: answer directly (no parallel)
- summary: summarize → answer (sequential)
- facts: extract_facts → answer (sequential)
- hybrid: PARALLEL MODE → summarize + extract_facts (concurrent) → (maybe recall_rag) → answer

TEACHING FOCUS: Parallel Routing Demonstration
-----------------------------------------------
The router determines when to use PARALLEL EXECUTION mode.
In hybrid mode, summarizer and facts_extractor run CONCURRENTLY,
demonstrating how LangGraph handles fan-out and reducer-based fan-in.

Also determines when to trigger RAG recall in hybrid mode.
"""
from typing import Literal, Dict, Any, List

from .state import AppState


def should_use_parallel_mode(state: AppState, config: Dict[str, Any]) -> bool:
    """
    Determine if we should use parallel execution stage.
    
    TEACHING: Parallel mode is enabled for hybrid memory strategy to demonstrate:
    - Concurrent node execution
    - Reducer-based state merging
    - Deterministic conflict resolution
    
    Returns True if memory_mode is 'hybrid' and message count > 2
    (need enough context for both summarization and fact extraction)
    """
    memory_mode = config.get("configurable", {}).get("memory_mode", "rolling")
    return memory_mode == "hybrid" and len(state.messages) > 2


def should_recall_rag(state: AppState) -> bool:
    """
    Heuristic: should we recall from RAG?
    
    Triggers if last user message contains reference keywords.
    """
    if not state.messages:
        return False
    
    user_messages = [msg for msg in state.messages if msg.role == "user"]
    if not user_messages:
        return False
    
    last_user_message = user_messages[-1].content.lower()
    
    # Keywords that suggest user wants past information
    reference_keywords = [
        "remember", "recall", "earlier", "before", "previous",
        "you said", "we discussed", "last time", "mentioned"
    ]
    
    return any(keyword in last_user_message for keyword in reference_keywords)


def route_after_entry(
    state: AppState,
    config: Dict[str, Any]
) -> Literal["metrics_logger", "answer"]:
    """
    Route from entry point.
    
    Always go to metrics_logger first for observability.
    """
    return "metrics_logger"


def route_after_metrics(
    state: AppState,
    config: Dict[str, Any]
) -> Literal["pii_filter", "summarizer", "facts_extractor"]:
    """
    Route after metrics logging based on memory mode.
    
    TEACHING: This router demonstrates conditional routing:
    - rolling: Direct path (no memory processing)
    - summary: Sequential summarization
    - facts: Sequential fact extraction
    - hybrid: Sequential (summarizer then facts_extractor)
    """
    memory_mode = config.get("configurable", {}).get("memory_mode", "rolling")
    
    if memory_mode == "rolling":
        # Rolling: go straight to answer (via PII filter)
        return "pii_filter"
    elif memory_mode == "summary":
        # Summary: summarize first (sequential)
        return "summarizer"
    elif memory_mode == "facts":
        # Facts: extract facts first (sequential)
        return "facts_extractor"
    elif memory_mode == "hybrid":
        # Hybrid: summarizer first, then facts_extractor
        return "summarizer"
    else:
        return "pii_filter"


def route_after_summarizer(
    state: AppState,
    config: Dict[str, Any]
) -> Literal["facts_extractor", "pii_filter"]:
    """
    Route after summarizer.
    
    In hybrid mode, continue to facts extraction.
    In summary mode, go to PII filter.
    """
    memory_mode = config.get("configurable", {}).get("memory_mode", "summary")
    
    if memory_mode == "hybrid":
        return "facts_extractor"
    else:
        return "pii_filter"


def route_after_facts(
    state: AppState,
    config: Dict[str, Any]
) -> Literal["rag_recall", "pii_filter"]:
    """
    Route after facts extraction.
    
    In hybrid mode, check if we should recall from RAG.
    Otherwise go to PII filter.
    """
    memory_mode = config.get("configurable", {}).get("memory_mode", "hybrid")
    
    if memory_mode == "hybrid" and should_recall_rag(state):
        return "rag_recall"
    else:
        return "pii_filter"


def route_after_rag(
    state: AppState,
    config: Dict[str, Any]
) -> Literal["pii_filter"]:
    """
    After RAG recall, always go to PII filter.
    """
    return "pii_filter"


def route_after_pii(
    state: AppState,
    config: Dict[str, Any]
) -> Literal["answer"]:
    """
    After PII filtering, always go to answer.
    """
    return "answer"
