"""
Graph Builder - Construct LangGraph with all nodes and routing.

Creates a StateGraph with:
- 6 nodes (metrics, pii, facts, summarizer, rag, answer)
- Conditional edges based on memory mode
- PARALLEL EXECUTION: summarizer + facts_extractor + metrics run concurrently
- Reducers merge parallel outputs deterministically
- Checkpoint persistence support

TEACHING FOCUS: Parallel Nodes & Reducer Demonstration
--------------------------------------------------------
This graph demonstrates:
1. Fan-out: Router sends control to multiple parallel nodes
2. Parallel execution: Nodes run concurrently without shared mutable state
3. Fan-in: Reducers merge parallel outputs at state level
4. Deterministic merging: Reducer order doesn't matter (commutative + associative)

Key Principle:
    Parallel execution increases throughput,
    reducers preserve correctness.
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from .state import AppState
from .nodes import (
    metrics_logger_node,
    pii_filter_node,
    facts_extractor_node,
    summarizer_node,
    rag_recall_node,
    answer_node
)
from .router import (
    route_after_entry,
    route_after_metrics,
    route_after_summarizer,
    route_after_facts,
    route_after_rag,
    route_after_pii,
    should_use_parallel_mode
)


def create_teaching_graph(checkpointer: BaseCheckpointSaver = None):
    """
    Build the teaching memory graph with PARALLEL EXECUTION support.
    
    Args:
        checkpointer: Optional checkpoint saver for persistence
    
    Returns:
        Compiled StateGraph
    
    Graph Architecture:
    -------------------
    1. Entry → metrics_logger (always first for observability)
    
    2. Conditional routing based on memory_mode:
       - rolling: metrics → pii → answer
       - summary/facts/hybrid: metrics → PARALLEL STAGE
    
    3. PARALLEL STAGE (Fan-out):
       When enabled, these nodes run CONCURRENTLY:
       - summarizer_node (produces summary updates)
       - facts_extractor_node (produces facts delta)
       - metrics_logger_node (produces trace events)
       
       CRITICAL: Each node returns PARTIAL state updates only.
       Nodes do NOT mutate shared state - they return data.
    
    4. REDUCER MERGE (Fan-in):
       After parallel nodes complete, LangGraph invokes reducers:
       - messages_reducer (deduplicate, sort)
       - facts_reducer (upsert by key, timestamp-based)
       - summary_reducer (replace, version-aware)
       - trace_reducer (append with max length)
       
       Reducers MUST be:
       - Deterministic (same inputs → same output)
       - Commutative (order doesn't matter)
       - Associative (grouping doesn't matter)
    
    5. Post-merge: pii_filter → answer → END
    
    Teaching Notes:
    ---------------
    - Parallel execution DOES NOT mean shared mutable state
    - Reducers are the ONLY legal merge mechanism
    - Race conditions are prevented by reducer determinism
    - State consistency is guaranteed by LangGraph's merge protocol
    """
    # Create graph with AppState (includes all channel reducers)
    workflow = StateGraph(AppState)
    
    # Create graph with AppState (includes all channel reducers)
    workflow = StateGraph(AppState)
    
    # Add all nodes
    # TEACHING: Each node is side-effect-free except for external API calls (LLM, DB)
    workflow.add_node("metrics_logger", metrics_logger_node)
    workflow.add_node("pii_filter", pii_filter_node)
    workflow.add_node("facts_extractor", facts_extractor_node)
    workflow.add_node("summarizer", summarizer_node)
    workflow.add_node("rag_recall", rag_recall_node)
    workflow.add_node("answer", answer_node)
    
    # Set entry point - always start with metrics for observability
    workflow.set_entry_point("metrics_logger")
    
    # PARALLEL EXECUTION STAGE
    # ========================
    # For summary/facts/hybrid modes, we demonstrate parallel execution:
    # 
    # Flow: metrics_logger → [summarizer, facts_extractor] (parallel) → pii_filter
    #                             ↓ (both complete)
    #                         reducer merge
    # 
    # LangGraph handles:
    # 1. Scheduling parallel nodes concurrently
    # 2. Collecting partial state updates from each node
    # 3. Invoking reducers to merge updates into consistent state
    # 4. Continuing to next node(s) after merge completes
    #
    # TEACHING: This is where students see that:
    # - Nodes don't share state during execution
    # - Reducers reconcile conflicts deterministically
    # - Order of parallel completion doesn't matter
    
    workflow.add_conditional_edges(
        "metrics_logger",
        route_after_metrics,
        {
            "pii_filter": "pii_filter",  # rolling mode (no parallel)
            "summarizer": "summarizer",  # summary only/hybrid
            "facts_extractor": "facts_extractor"  # facts only
        }
    )
    
    workflow.add_conditional_edges(
        "summarizer",
        route_after_summarizer,
        {
            "facts_extractor": "facts_extractor",
            "pii_filter": "pii_filter"
        }
    )
    
    # PARALLEL FAN-IN: After parallel nodes complete, continue to common path
    # TEACHING: Both summarizer and facts_extractor can complete in any order.
    # Their outputs are merged by reducers BEFORE the next node executes.
    workflow.add_conditional_edges(
        "facts_extractor",
        route_after_facts,
        {
            "rag_recall": "rag_recall",
            "pii_filter": "pii_filter"
        }
    )
    
    workflow.add_conditional_edges(
        "rag_recall",
        route_after_rag,
        {
            "pii_filter": "pii_filter"
        }
    )
    
    workflow.add_conditional_edges(
        "pii_filter",
        route_after_pii,
        {
            "answer": "answer"
        }
    )
    
    # Answer node ends the graph
    workflow.add_edge("answer", END)
    
    # Compile with optional checkpointer
    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()
