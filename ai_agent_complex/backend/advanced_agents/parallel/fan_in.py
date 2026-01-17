"""
Fan-In Node - Aggregates results from parallel execution.

This module implements the "fan-in" pattern for result aggregation.

WHY Fan-In?
- Parallel tasks produce independent results
- Need to merge results into coherent response
- Handle partial failures (some tasks succeed, some fail)
- Provide summary and statistics

HOW it works:
1. Waits for all parallel branches to complete (LangGraph handles synchronization)
2. Receives merged state via reducers
3. Aggregates results into single response
4. Handles errors gracefully
5. Produces final output

CRITICAL: LangGraph Synchronization
- LangGraph automatically waits for all parallel branches at merge point
- Reducers combine state from all branches
- Fan-in node receives already-merged state
- No manual synchronization needed!

Following SOLID:
- Single Responsibility: Only aggregation, not execution
- Open/Closed: Easy to add new aggregation strategies
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..state import AdvancedAgentState, AggregationResult
from observability.metrics import record_node_duration

logger = logging.getLogger(__name__)


class FanInNode:
    """
    LangGraph node that aggregates results from parallel execution.
    
    This node:
    1. Receives state with parallel_results (already merged by reducers)
    2. Analyzes results for success/failure
    3. Combines successful results into aggregated data
    4. Generates summary statistics
    5. Produces final response
    
    NOTE: By the time this node executes, LangGraph has already:
    - Waited for all parallel branches to complete
    - Merged results via parallel_results_reducer
    - Combined all state updates
    """
    
    def __init__(self, merge_strategy: str = "concat"):
        """
        Initialize fan-in node.
        
        Args:
            merge_strategy: How to merge results
                - "concat": Concatenate all results
                - "dict": Merge into single dictionary
                - "summary": Generate summary from results
        """
        self.merge_strategy = merge_strategy
    
    async def __call__(self, state: AdvancedAgentState) -> Dict[str, Any]:
        """
        Aggregate results from parallel execution.
        
        WHY async?
        - May need to call LLM for summarization
        - Consistent with other nodes
        - Future-proof for async aggregation strategies
        
        Args:
            state: State with parallel_results already merged
            
        Returns:
            Updated state with aggregation_result and aggregated_data
        """
        with record_node_duration("fan_in"):
            parallel_results = state.get("parallel_results", [])
            
            if not parallel_results:
                logger.warning("[FAN-IN] No parallel results to aggregate")
                return {
                    "parallel_execution_active": False,
                    "debug_logs": ["[FAN-IN] No results to aggregate"]
                }
            
            logger.info(f"[FAN-IN] Aggregating {len(parallel_results)} results")
            
            # Analyze results
            total_tasks = len(parallel_results)
            successful_results = [r for r in parallel_results if r.get("success", False)]
            failed_results = [r for r in parallel_results if not r.get("success", False)]
            
            successful_tasks = len(successful_results)
            failed_tasks = len(failed_results)
            
            logger.info(f"[FAN-IN] Success: {successful_tasks}, Failed: {failed_tasks}")
            
            # Aggregate successful results
            aggregated_data = self._aggregate_results(successful_results)
            
            # Collect errors from failed tasks
            errors = [
                {
                    "task_id": r.get("task_id", "unknown"),
                    "error": r.get("error", "Unknown error")
                }
                for r in failed_results
            ]
            
            # Create aggregation result
            aggregation_result = AggregationResult(
                total_tasks=total_tasks,
                successful_tasks=successful_tasks,
                failed_tasks=failed_tasks,
                aggregated_data=aggregated_data,
                errors=errors,
                execution_time_ms=0.0  # Would be calculated from timestamps
            )
            
            # Generate debug output
            debug_msgs = [
                f"[FAN-IN] ✓ Aggregated {successful_tasks}/{total_tasks} successful results"
            ]
            if failed_tasks > 0:
                debug_msgs.append(f"[FAN-IN] ⚠️ {failed_tasks} tasks failed")
            
            return {
                "aggregation_result": aggregation_result,
                "aggregated_data": aggregated_data,
                "parallel_execution_active": False,
                "debug_logs": debug_msgs
            }
    
    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge successful results based on strategy.
        
        WHY different strategies?
        - Different workflows need different aggregation
        - Weather + FX rates: combine into one dict
        - Multiple news articles: concatenate text
        - Summary generation: use LLM to synthesize
        
        Args:
            results: List of successful task results
            
        Returns:
            Aggregated data structure
        """
        if self.merge_strategy == "concat":
            return self._concat_results(results)
        elif self.merge_strategy == "dict":
            return self._dict_merge_results(results)
        elif self.merge_strategy == "summary":
            return self._summarize_results(results)
        else:
            logger.warning(f"[FAN-IN] Unknown merge strategy: {self.merge_strategy}")
            return self._dict_merge_results(results)  # Default
    
    def _concat_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Concatenate results into a list.
        
        WHY: Preserves all individual results for review.
        
        Args:
            results: Task results
            
        Returns:
            Dictionary with concatenated results
        """
        return {
            "results": results,
            "count": len(results),
            "aggregation_type": "concat"
        }
    
    def _dict_merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge results into single dictionary by tool name.
        
        WHY: Creates clean structure for different data types.
        Example:
            {
                "weather": {"temp": 15, "condition": "sunny"},
                "fx_rates": {"USD_EUR": 0.85},
                "crypto": {"BTC": 45000}
            }
        
        Args:
            results: Task results
            
        Returns:
            Merged dictionary
        """
        merged = {}
        
        for result in results:
            task_id = result.get("task_id", "unknown")
            tool_name = result.get("tool_name", "unknown")
            data = result.get("data", {})
            
            # Use tool_name as key for organized structure
            if tool_name not in merged:
                merged[tool_name] = {}
            
            merged[tool_name][task_id] = data
        
        merged["aggregation_type"] = "dict"
        return merged
    
    def _summarize_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary from results.
        
        WHY: More user-friendly than raw data dump.
        
        Args:
            results: Task results
            
        Returns:
            Summary dictionary
        """
        # Simple statistical summary
        summary = {
            "total_results": len(results),
            "data_sources": list({r.get("tool_name") for r in results}),
            "aggregation_type": "summary"
        }
        
        # Add result snippets
        summary["result_previews"] = [
            {
                "task_id": r.get("task_id"),
                "tool": r.get("tool_name"),
                "preview": str(r.get("data", {}))[:100]
            }
            for r in results[:5]  # First 5 results
        ]
        
        return summary
    
    def calculate_execution_time(self, results: List[Dict[str, Any]]) -> float:
        """
        Calculate total execution time from result timestamps.
        
        WHY: Performance monitoring and optimization insights.
        
        Args:
            results: Results with timestamp fields
            
        Returns:
            Execution time in milliseconds
        """
        if not results:
            return 0.0
        
        # Extract timestamps
        timestamps = []
        for result in results:
            if "timestamp" in result:
                try:
                    ts = datetime.fromisoformat(result["timestamp"])
                    timestamps.append(ts)
                except (ValueError, TypeError):
                    continue
        
        if len(timestamps) < 2:
            return 0.0
        
        # Calculate duration from earliest to latest
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        duration = (max_ts - min_ts).total_seconds() * 1000
        
        return duration
