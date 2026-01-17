"""
Advanced Agents Module - Enterprise-grade orchestration patterns for LangGraph.

This module demonstrates advanced AI agent architectures including:
- Plan-and-Execute workflows
- Parallel node execution (fan-out/fan-in)
- Dynamic routing and decision-making
- Result aggregation and state reduction
- Enterprise workflow patterns

Following SOLID principles:
- Each pattern is isolated and reusable
- Clear separation between planning, execution, routing, and aggregation
- Dependency injection for flexibility
- Educational comments explaining WHY, not just WHAT

Usage:
    from advanced_agents import AdvancedAgentGraph
    graph = AdvancedAgentGraph(llm, tools)
    result = await graph.run(state)
"""

__version__ = "1.0.0"
__author__ = "AI Agent Complex Education Team"

from .state import (
    AdvancedAgentState,
    ExecutionPlan,
    PlanStep,
    ParallelTask,
    AggregationResult,
    list_reducer,
    dict_merge_reducer,
    parallel_results_reducer
)

from .advanced_graph import AdvancedAgentGraph

__all__ = [
    "AdvancedAgentState",
    "ExecutionPlan",
    "PlanStep",
    "ParallelTask",
    "AggregationResult",
    "list_reducer",
    "dict_merge_reducer",
    "parallel_results_reducer",
    "AdvancedAgentGraph"
]
