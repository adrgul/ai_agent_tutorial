"""
Result Aggregator - Combines results from parallel/sequential steps into final response.

This module focuses on intelligent result aggregation and synthesis.

WHY Separate Aggregator?
- Fan-in merges raw data mechanically
- Aggregator synthesizes user-friendly response
- Handles complex data transformations
- Can use LLM for natural language synthesis

DIFFERENCE: Fan-In vs Aggregator
- Fan-In: Technical merge (parallel → single state)
- Aggregator: Semantic synthesis (data → answer)
- Fan-In always needed for parallelism
- Aggregator optional but improves UX

Following SOLID:
- Single Responsibility: Only result synthesis
- Open/Closed: Easy to add synthesis strategies
"""

import logging
from typing import Dict, Any, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..state import AdvancedAgentState
from observability.metrics import record_node_duration
from observability.llm_instrumentation import instrumented_llm_call
from observability.llm_instrumentation import instrumented_llm_call

logger = logging.getLogger(__name__)


class ResultAggregator:
    """
    Synthesizes final response from plan/parallel execution results.
    
    This aggregator:
    1. Takes raw results from multiple sources
    2. Structures data for user consumption
    3. Optionally uses LLM for natural language synthesis
    4. Handles missing/incomplete data gracefully
    5. Provides citations and sources
    """
    
    def __init__(
        self, 
        llm: Optional[ChatOpenAI] = None,
        use_llm_synthesis: bool = True
    ):
        """
        Initialize result aggregator.
        
        Args:
            llm: Optional LLM for synthesis
            use_llm_synthesis: Whether to use LLM for final answer generation
        """
        self.llm = llm
        self.use_llm_synthesis = use_llm_synthesis
    
    async def __call__(self, state: AdvancedAgentState) -> Dict[str, Any]:
        """
        Aggregate results into final response.
        
        Args:
            state: State with plan_results, parallel_results, aggregated_data
            
        Returns:
            Updated state with final_answer
        """
        with record_node_duration("aggregator"):
            logger.info("[AGGREGATOR] Synthesizing final response...")
            
            # Gather all results
            plan_results = state.get("plan_results", [])
            parallel_results = state.get("parallel_results", [])
            aggregated_data = state.get("aggregated_data", {})
            aggregation_result = state.get("aggregation_result")
            
            # Build context
            results_context = self._build_results_context(
                plan_results, 
                parallel_results, 
                aggregated_data,
                aggregation_result
            )
            
            # Generate final answer
            if self.use_llm_synthesis and self.llm:
                final_answer = await self._synthesize_with_llm(state, results_context)
            else:
                final_answer = self._synthesize_template(results_context)
            
            logger.info(f"[AGGREGATOR] Generated answer ({len(final_answer)} chars)")
            
            return {
                "final_answer": final_answer,
                "debug_logs": [
                    "[AGGREGATOR] ✓ Final response synthesized",
                    f"[AGGREGATOR] Answer length: {len(final_answer)} chars"
                ]
            }
    
    def _build_results_context(
        self,
        plan_results: List[Dict[str, Any]],
        parallel_results: List[Dict[str, Any]],
        aggregated_data: Dict[str, Any],
        aggregation_result: Optional[Any]
    ) -> Dict[str, Any]:
        """
        Build unified context from all result sources.
        
        WHY: Different execution patterns produce different result structures.
        This normalizes them for synthesis.
        
        Args:
            plan_results: Results from plan execution
            parallel_results: Results from parallel execution
            aggregated_data: Merged data from fan-in
            aggregation_result: Aggregation metadata
            
        Returns:
            Unified context dictionary
        """
        context = {
            "has_plan_results": len(plan_results) > 0,
            "has_parallel_results": len(parallel_results) > 0,
            "total_operations": len(plan_results) + len(parallel_results),
            "successful_operations": 0,
            "failed_operations": 0,
            "data": {}
        }
        
        # Count successes/failures
        for result in plan_results + parallel_results:
            if result.get("success", False):
                context["successful_operations"] += 1
            else:
                context["failed_operations"] += 1
        
        # Extract data
        if aggregated_data:
            context["data"] = aggregated_data
        else:
            # Manually aggregate if not done yet
            for result in plan_results:
                if result.get("success"):
                    key = result.get("step_id") or result.get("task_id", "result")
                    context["data"][key] = result.get("result", {})
            
            for result in parallel_results:
                if result.get("success"):
                    key = result.get("task_id", "result")
                    context["data"][key] = result.get("data", {})
        
        # Add aggregation summary if available
        if aggregation_result:
            context["aggregation_summary"] = {
                "total_tasks": aggregation_result.total_tasks,
                "successful_tasks": aggregation_result.successful_tasks,
                "failed_tasks": aggregation_result.failed_tasks,
                "execution_time_ms": aggregation_result.execution_time_ms
            }
        
        return context
    
    async def _synthesize_with_llm(
        self, 
        state: AdvancedAgentState,
        results_context: Dict[str, Any]
    ) -> str:
        """
        Use LLM to generate natural language response from results.
        
        WHY LLM synthesis?
        - Converts structured data to conversational response
        - Handles complex data relationships
        - Adapts tone to user request
        - More natural than template responses
        
        Args:
            state: Current state with user message
            results_context: Unified results context
            
        Returns:
            Natural language response
        """
        user_message = state.get("messages", [])[-1].content if state.get("messages") else ""
        
        system_prompt = """You are an AI assistant synthesizing results into a clear, helpful response.

Given:
- User's original question
- Results from various data sources
- Success/failure statistics

Generate a natural, conversational response that:
1. Directly answers the user's question
2. Incorporates all relevant data
3. Mentions if any operations failed (but don't dwell on it)
4. Is concise but complete
5. Uses proper formatting (markdown if appropriate)

Do NOT:
- Include technical details about execution
- Mention "step_1" or internal identifiers
- Apologize excessively for failures
- Repeat the user's question verbatim"""
        
        # Format results for LLM
        results_text = self._format_results_for_llm(results_context)
        
        user_prompt = f"""User question: {user_message}

Results:
{results_text}

Statistics:
- Total operations: {results_context['total_operations']}
- Successful: {results_context['successful_operations']}
- Failed: {results_context['failed_operations']}

Generate a helpful response."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = await instrumented_llm_call(
                llm=self.llm,
                messages=messages,
                model="gpt-4o-mini",
                agent_execution_id=state.get("session_id")
            )
            return response.content
        except Exception as e:
            logger.error(f"[AGGREGATOR] LLM synthesis failed: {e}")
            # Fallback to template
            return self._synthesize_template(results_context)
    
    def _format_results_for_llm(self, context: Dict[str, Any]) -> str:
        """
        Format results context into readable text for LLM.
        
        Args:
            context: Results context
            
        Returns:
            Formatted text
        """
        lines = []
        
        data = context.get("data", {})
        for key, value in data.items():
            if isinstance(value, dict):
                # Format nested data
                for sub_key, sub_value in value.items():
                    lines.append(f"- {key}.{sub_key}: {sub_value}")
            else:
                lines.append(f"- {key}: {value}")
        
        return "\n".join(lines) if lines else "No data available"
    
    def _synthesize_template(self, context: Dict[str, Any]) -> str:
        """
        Generate response using template (fallback when LLM unavailable).
        
        WHY template fallback?
        - LLM might fail or be unavailable
        - Some use cases need deterministic responses
        - Educational: shows you don't always need LLM
        
        Args:
            context: Results context
            
        Returns:
            Template-based response
        """
        total_ops = context["total_operations"]
        successful_ops = context["successful_operations"]
        failed_ops = context["failed_operations"]
        
        # Build response parts
        parts = []
        
        # Success summary
        if successful_ops > 0:
            parts.append(f"Successfully completed {successful_ops} operation(s):")
        
        # Add data
        data = context.get("data", {})
        if data:
            for key, value in data.items():
                if isinstance(value, dict):
                    value_str = ", ".join(f"{k}={v}" for k, v in value.items())
                    parts.append(f"• {key}: {value_str}")
                else:
                    parts.append(f"• {key}: {value}")
        
        # Failure note
        if failed_ops > 0:
            parts.append(f"\nNote: {failed_ops} operation(s) failed.")
        
        return "\n".join(parts) if parts else "No results to report."
