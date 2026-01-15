"""
Fan-Out Node - Spawns parallel tasks for concurrent execution.

This module implements the "fan-out" pattern for parallel execution.

WHY Fan-Out?
- Execute multiple independent tasks simultaneously
- Reduce overall latency (3 sequential 1s tasks = 3s, parallel = 1s)
- Better resource utilization
- Essential for real-world AI workflows (gather data from multiple sources)

HOW it works:
1. Receives list of tasks to execute in parallel
2. Identifies independent tasks (no dependencies)
3. Spawns each as separate execution path
4. LangGraph handles actual parallel execution
5. Each parallel branch updates state independently

CRITICAL: LangGraph Parallelism
- LangGraph doesn't execute nodes in parallel by default
- We use Send() API to spawn parallel branches
- Each Send() creates independent execution path
- Reducers merge results when branches converge

Following SOLID:
- Single Responsibility: Only task spawning, not execution
- Open/Closed: Easy to add new spawning strategies
"""

import logging
import asyncio
from typing import Dict, Any, List, Protocol

from ..state import AdvancedAgentState, ParallelTask
from observability.metrics import record_node_duration, tool_invocation_count

logger = logging.getLogger(__name__)


class ToolProtocol(Protocol):
    """Protocol for tool objects with execute method."""
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        ...


class FanOutNode:
    """
    LangGraph node that spawns parallel execution branches.
    
    This node:
    1. Reads parallel_tasks from state
    2. Validates task independence (no shared dependencies)
    3. Executes tasks in parallel
    4. Collects results for fan-in aggregation
    """
    
    def __init__(self, tools: Dict[str, Any] = None):
        """Initialize fan-out node with available tools."""
        self.tools = tools or {}
    
    async def __call__(self, state: AdvancedAgentState) -> Dict[str, Any]:
        """
        Execute parallel tasks concurrently.
        
        Args:
            state: Current agent state with parallel_tasks
            
        Returns:
            Updated state with parallel_results
        """
        with record_node_duration("fan_out"):
            tasks = state.get("parallel_tasks", [])
            
            if not tasks:
                logger.warning("[FAN-OUT] No tasks to fan out")
                return {
                    "parallel_execution_active": False,
                    "debug_logs": ["[FAN-OUT] No parallel tasks to execute"]
                }
            
            logger.info(f"[FAN-OUT] Fanning out {len(tasks)} tasks")
            logger.info(f"[FAN-OUT] DEBUG: Available tools: {list(self.tools.keys())}")
            
            # Validate task independence
            if not self._tasks_are_independent(tasks):
                logger.error("[FAN-OUT] Tasks have circular dependencies!")
                return {
                    "parallel_execution_active": False,
                    "debug_logs": ["[FAN-OUT] ✗ Cannot execute - tasks have dependencies"]
                }
            
            # Log task details
            task_names = [f"{t.tool_name}({t.task_id})" for t in tasks]
            logger.info(f"[FAN-OUT] Tasks: {', '.join(task_names)}")
            
            # Execute tasks in parallel
            parallel_results = await self._execute_tasks_in_parallel(tasks, state)
            
            return {
                "parallel_execution_active": True,
                "parallel_results": parallel_results,
                "debug_logs": [
                    f"[FAN-OUT] ✓ Executed {len(tasks)} parallel tasks",
                    f"[FAN-OUT] Results: {len(parallel_results)} completed"
                ]
            }
    
    async def _execute_tasks_in_parallel(
        self, 
        tasks: List[ParallelTask],
        state: AdvancedAgentState
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tasks concurrently using asyncio.gather.
        
        Args:
            tasks: List of tasks to execute
            state: Current state (for user_id, etc.)
            
        Returns:
            List of task results
        """
        async def execute_single_task(task: ParallelTask) -> Dict[str, Any]:
            """Execute one task and return result."""
            tool = self.tools.get(task.tool_name)
            if not tool:
                logger.error(f"[FAN-OUT] Tool not found: {task.tool_name}")
                return {
                    "task_id": task.task_id,
                    "tool_name": task.tool_name,
                    "success": False,
                    "error": f"Tool '{task.tool_name}' not found",
                    "data": None
                }
            
            logger.info(f"[FAN-OUT] Executing task {task.task_id}: {task.tool_name}")
            tool_invocation_count.labels(tool=task.tool_name).inc()
            
            try:
                # Add user_id if create_file tool
                if task.tool_name == "create_file" and "user_id" not in task.arguments:
                    task.arguments["user_id"] = state.get("user_id", "default_user")
                
                # Unpack arguments as keyword arguments
                result = await tool.execute(**task.arguments)
                logger.info(f"[FAN-OUT] Task {task.task_id} completed: {result.get('success')}")
                
                return {
                    "task_id": task.task_id,
                    "tool_name": task.tool_name,
                    **result  # Includes success, data, system_message
                }
            except Exception as e:
                logger.error(f"[FAN-OUT] Task {task.task_id} failed: {e}")
                return {
                    "task_id": task.task_id,
                    "tool_name": task.tool_name,
                    "success": False,
                    "error": str(e),
                    "data": None
                }
        
        # Execute all tasks in parallel
        logger.info(f"[FAN-OUT] Starting parallel execution of {len(tasks)} tasks")
        results = await asyncio.gather(
            *[execute_single_task(task) for task in tasks],
            return_exceptions=True
        )
        
        # Handle any exceptions that occurred
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[FAN-OUT] Task {tasks[i].task_id} raised exception: {result}")
                processed_results.append({
                    "task_id": tasks[i].task_id,
                    "tool_name": tasks[i].tool_name,
                    "success": False,
                    "error": str(result),
                    "data": None
                })
            else:
                processed_results.append(result)
        
        logger.info(f"[FAN-OUT] Parallel execution complete: {len(processed_results)} results")
        return processed_results
    
    def _tasks_are_independent(self, tasks: List[ParallelTask]) -> bool:
        """
        Verify that tasks can run in parallel (no inter-dependencies).
        
        WHY important?
        - Parallel execution assumes tasks don't depend on each other
        - Dependencies would cause race conditions
        - Educational: shows importance of task independence
        
        Args:
            tasks: List of tasks to validate
            
        Returns:
            True if tasks are independent
        """
        # For parallel tasks, we assume they're independent
        # In a more sophisticated system, we'd check for:
        # - Shared mutable state
        # - Data dependencies
        # - Resource conflicts
        
        # Simple check: all tasks should have unique task_ids
        task_ids = [t.task_id for t in tasks]
        return len(task_ids) == len(set(task_ids))
    
    def create_parallel_tasks(
        self,
        task_definitions: List[Dict[str, Any]]
    ) -> List[ParallelTask]:
        """
        Helper to create ParallelTask objects from definitions.
        
        WHY helper method?
        - Makes it easy to create tasks in other nodes
        - Validates task structure
        - Centralized task creation logic
        
        Args:
            task_definitions: List of task specs
            
        Returns:
            List of validated ParallelTask objects
        """
        tasks = []
        for i, task_def in enumerate(task_definitions):
            task = ParallelTask(
                task_id=task_def.get("task_id", f"task_{i}"),
                task_type=task_def.get("task_type", "api_call"),
                tool_name=task_def["tool_name"],
                arguments=task_def.get("arguments", {}),
                timeout_seconds=task_def.get("timeout_seconds", 30.0)
            )
            tasks.append(task)
        
        return tasks
