"""
Executor Node - Executes planned steps with retry logic.

This module implements the "Execute" part of Plan-and-Execute pattern.

WHY separate executor from planner?
- Single Responsibility Principle (SRP)
- Planner focuses on WHAT to do
- Executor focuses on HOW to do it
- Easier to test, modify, and extend each separately

HOW it works:
1. Reads execution plan from state
2. Identifies next step to execute based on dependencies
3. Routes to appropriate tool node
4. Handles errors with retry logic
5. Updates plan progress in state
6. Continues until all steps complete

Following SOLID:
- Single Responsibility: Only execution, not planning
- Open/Closed: Easy to add new execution strategies (retry, timeout, etc.)
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..state import AdvancedAgentState, ExecutionPlan, PlanStep
from observability.metrics import record_node_duration

logger = logging.getLogger(__name__)


class ExecutorNode:
    """
    LangGraph node that executes planned steps.
    
    This node:
    1. Checks which step to execute next
    2. Verifies dependencies are satisfied
    3. Routes to tool execution
    4. Handles retries on failure
    5. Updates execution status
    6. Determines if plan is complete
    """
    
    def __init__(self, max_retries: int = 3, retry_delay_seconds: float = 1.0):
        """
        Initialize executor node.
        
        Args:
            max_retries: Maximum retry attempts for failed steps
            retry_delay_seconds: Delay between retry attempts
        """
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.max_consecutive_failures = 3  # Stop if this many steps fail in a row
    
    async def __call__(self, state: AdvancedAgentState) -> Dict[str, Any]:
        """
        Execute next step in the plan.
        
        WHY iterative execution?
        - LangGraph nodes should be small and focused
        - Each execution is a separate graph traversal
        - Enables checkpoint/resume functionality
        - Better error handling and observability
        
        Args:
            state: Current agent state with execution plan
            
        Returns:
            Updated state with step result and progress
        """
        with record_node_duration("executor"):
            plan = state.get("execution_plan")
            
            if not plan:
                logger.error("[EXECUTOR] No execution plan found in state")
                return {
                    "plan_completed": True,
                    "debug_logs": ["[EXECUTOR] ✗ No plan to execute"]
                }
            
            current_index = state.get("current_step_index", 0)
            
            # SAFETY NET: Check for too many consecutive failures
            plan_results = state.get("plan_results", [])
            consecutive_failures = 0
            for result in reversed(plan_results):
                if not result.get("success", False):
                    consecutive_failures += 1
                else:
                    break
            
            if consecutive_failures >= self.max_consecutive_failures:
                logger.warning(f"[EXECUTOR] {consecutive_failures} consecutive failures, aborting plan")
                return {
                    "plan_completed": True,
                    "debug_logs": [f"[EXECUTOR] ✗ Aborted: {consecutive_failures} consecutive step failures"]
                }
            
            # Check if plan is already complete
            if current_index >= len(plan.steps):
                logger.info("[EXECUTOR] All plan steps completed")
                return {
                    "plan_completed": True,
                    "debug_logs": ["[EXECUTOR] ✓ Plan execution complete"]
                }
            
            # Get current step
            current_step = plan.steps[current_index]
            
            logger.info(f"[EXECUTOR] Executing step {current_index + 1}/{len(plan.steps)}: {current_step.description}")
            
            # Check dependencies
            if not self._dependencies_satisfied(current_step, state):
                logger.warning(f"[EXECUTOR] Dependencies not satisfied for step {current_step.step_id}")
                
                # Check if dependencies will NEVER be satisfied (previous step failed)
                plan_results = state.get("plan_results", [])
                failed_dependencies = []
                for dep_id in current_step.depends_on:
                    dep_result = next((r for r in plan_results if r["step_id"] == dep_id), None)
                    if dep_result and not dep_result.get("success", False):
                        failed_dependencies.append(dep_id)
                
                if failed_dependencies:
                    # Dependency failed, skip this step and move to next
                    logger.error(f"[EXECUTOR] Skipping step {current_step.step_id} due to failed dependencies: {failed_dependencies}")
                    next_index = current_index + 1
                    is_complete = next_index >= len(plan.steps)
                    
                    # Record skipped step
                    plan_results.append({
                        "step_id": current_step.step_id,
                        "description": current_step.description,
                    "result": None,
                    "error": f"Skipped due to failed dependencies: {failed_dependencies}",
                    "success": False,
                    "timestamp": datetime.now().isoformat()
                })
                
                return {
                    "plan_results": [plan_results[-1]],
                    "current_step_index": next_index,
                    "plan_completed": is_complete,
                    "debug_logs": [f"[EXECUTOR] ⏭ Skipped step {current_index + 1} (dependencies failed)"]
                }
            
            # Dependencies not yet satisfied, wait
            return {
                "debug_logs": [f"[EXECUTOR] ⏸ Waiting for dependencies: {current_step.depends_on}"]
            }
        
        # Execute step with retry logic
        result = await self._execute_step_with_retry(current_step, state)
        
        # Update state with result
        plan_results = state.get("plan_results", [])
        plan_results.append({
            "step_id": current_step.step_id,
            "description": current_step.description,
            "result": result,  # Store the entire result dict (contains success, data, city, etc.)
            "error": result.get("error"),
            "success": result.get("success", False),
            "timestamp": datetime.now().isoformat()
        })
        
        # Move to next step
        next_index = current_index + 1
        is_complete = next_index >= len(plan.steps)
        
        debug_msg = f"[EXECUTOR] ✓ Step {current_index + 1} complete"
        if result.get("error"):
            debug_msg = f"[EXECUTOR] ✗ Step {current_index + 1} failed: {result['error']}"
        
        return {
            "plan_results": [plan_results[-1]],  # Append to list via reducer
            "current_step_index": next_index,
            "plan_completed": is_complete,
            "debug_logs": [debug_msg],
            "tools_called": [{
                "tool_name": current_step.tool_name,
                "arguments": current_step.arguments,
                "success": result.get("success", False),
                "step_id": current_step.step_id
            }]
        }
    
    def _dependencies_satisfied(self, step: PlanStep, state: AdvancedAgentState) -> bool:
        """
        Check if all dependencies for a step are satisfied.
        
        WHY check dependencies?
        - Some steps need results from previous steps
        - Example: "Get weather for my location" needs location first
        - Prevents executing steps out of order
        
        Args:
            step: Step to check
            state: Current state with plan_results
            
        Returns:
            True if all dependencies are satisfied
        """
        if not step.depends_on:
            return True  # No dependencies
        
        plan_results = state.get("plan_results", [])
        completed_step_ids = {
            result["step_id"] 
            for result in plan_results 
            if result.get("success", False)
        }
        
        # Check if all dependencies are in completed steps
        return all(dep_id in completed_step_ids for dep_id in step.depends_on)
    
    async def _execute_step_with_retry(
        self, 
        step: PlanStep, 
        state: AdvancedAgentState
    ) -> Dict[str, Any]:
        """
        Execute a single step with retry logic.
        
        WHY retries?
        - External APIs can be flaky (network errors, rate limits)
        - Transient failures shouldn't fail entire workflow
        - Educational: shows enterprise-grade error handling
        
        Args:
            step: Step to execute
            state: Current state
            
        Returns:
            Result dictionary with success flag and data/error
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"[EXECUTOR] Attempt {attempt + 1}/{self.max_retries} for step {step.step_id}")
                
                # Execute the step (this would route to actual tool)
                # For now, we simulate execution
                result = await self._execute_tool(step, state)
                
                logger.info(f"[EXECUTOR] Step {step.step_id} succeeded")
                return {
                    "success": True,
                    "result": result,
                    "error": None
                }
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[EXECUTOR] Step {step.step_id} failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay_seconds)
        
        # All retries failed
        logger.error(f"[EXECUTOR] Step {step.step_id} failed after {self.max_retries} attempts")
        return {
            "success": False,
            "result": None,
            "error": last_error
        }
    
    async def _execute_tool(self, step: PlanStep, state: AdvancedAgentState) -> Any:
        """
        Execute the actual tool for a step.
        
        WHY separate method?
        - Makes testing easier (can mock tool execution)
        - Clear separation of retry logic from execution logic
        - Easy to swap with different execution strategies
        
        Args:
            step: Step with tool_name and arguments
            state: Current state (may contain tool instances)
            
        Returns:
            Tool execution result
            
        Raises:
            Exception: If tool execution fails
        """
        # CRITICAL FIX: Resolve argument placeholders like ${step_1.result.city}
        plan_results = state.get("plan_results", [])
        resolved_arguments = self._resolve_arguments(step.arguments, plan_results)
        
        logger.info(f"[EXECUTOR] Executing tool '{step.tool_name}' with args: {resolved_arguments}")
        
        # Check if tool is an MCP tool (AlphaVantage or DeepWiki)
        alphavantage_tools = state.get("alphavantage_tools", [])
        deepwiki_tools = state.get("deepwiki_tools", [])
        
        # Check AlphaVantage tools
        if any(t.get("name") == step.tool_name for t in alphavantage_tools):
            # This is an AlphaVantage MCP tool
            logger.info(f"[EXECUTOR] Calling AlphaVantage MCP tool: {step.tool_name}")
            mcp_client = state.get("alphavantage_mcp_client")
            if not mcp_client:
                raise ValueError("AlphaVantage MCP client not found in state")
            
            result = await mcp_client.call_tool(step.tool_name, resolved_arguments)
            logger.info(f"[EXECUTOR] AlphaVantage tool '{step.tool_name}' returned result")
            
            return {
                "success": True,
                "data": result,
                "system_message": f"AlphaVantage {step.tool_name} completed"
            }
        
        # Check DeepWiki tools
        elif any(t.get("name") == step.tool_name for t in deepwiki_tools):
            # This is a DeepWiki MCP tool
            logger.info(f"[EXECUTOR] Calling DeepWiki MCP tool: {step.tool_name}")
            mcp_client = state.get("deepwiki_mcp_client")
            if not mcp_client:
                raise ValueError("DeepWiki MCP client not found in state")
            
            result = await mcp_client.call_tool(step.tool_name, resolved_arguments)
            logger.info(f"[EXECUTOR] DeepWiki tool '{step.tool_name}' returned result")
            
            return {
                "success": True,
                "data": result,
                "system_message": f"DeepWiki {step.tool_name} completed"
            }
        
        # Regular tool (weather, geocode, etc.)
        else:
            # Get tools from state
            tools = state.get("tools", {})
            
            if step.tool_name not in tools:
                raise ValueError(f"Tool '{step.tool_name}' not found in available tools")
            
            # CRITICAL: Add user_id for file creation tool
            if step.tool_name == "create_file":
                user_id = state.get("user_id") or state.get("session_id", "default")
                resolved_arguments["user_id"] = user_id
                logger.info(f"[EXECUTOR] Injected user_id for create_file: {user_id}")
            
            # Execute the tool
            tool = tools[step.tool_name]
            result = await tool.execute(**resolved_arguments)
            
            logger.info(f"[EXECUTOR] Tool '{step.tool_name}' returned: {result.get('success', False)}")
            
            return result
    
    def _resolve_arguments(
        self, 
        arguments: Dict[str, Any], 
        plan_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Resolve argument placeholders with results from previous steps.
        
        WHY argument resolution?
        - Steps often need output from previous steps
        - Example: "Get weather for ${step_1.result.city}"
        - Enables complex multi-step workflows
        
        Args:
            arguments: Step arguments (may contain ${step_id.path} placeholders)
            plan_results: Results from completed steps
            
        Returns:
            Arguments with placeholders replaced by actual values
        """
        resolved = {}
        
        # Create lookup map of step results
        results_map = {r["step_id"]: r["result"] for r in plan_results}
        
        for key, value in arguments.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Extract placeholder: ${step_1.result.city} → ["step_1", "result", "city"]
                path = value[2:-1].split(".")
                step_id = path[0]
                
                if step_id in results_map:
                    # Navigate the path
                    result = results_map[step_id]
                    for part in path[1:]:
                        if isinstance(result, dict):
                            result = result.get(part)
                        else:
                            result = getattr(result, part, None)
                    resolved[key] = result
                else:
                    resolved[key] = value  # Keep placeholder if step not found
            else:
                resolved[key] = value
        
        return resolved
