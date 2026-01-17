"""
Parallel Execution Demo - Educational example of parallel workflow.

This module demonstrates a complete parallel execution workflow:
1. User asks for weather + exchange rates + crypto prices
2. Planner creates a plan with parallel steps
3. Router identifies that all steps can run concurrently
4. Fan-out spawns parallel tasks
5. Three tools execute simultaneously:
   - Weather API
   - Exchange rate API
   - Crypto price API
6. Fan-in aggregates results
7. Aggregator synthesizes final response

WHY This Example?
- Shows real-world use case (gathering data from multiple sources)
- Demonstrates latency reduction (parallel vs sequential)
- Educational: clearly labeled with execution flow
- Includes error handling (what if one API fails?)

LEARNING OBJECTIVES:
- Understand parallel execution patterns
- See how LangGraph coordinates parallel nodes
- Learn when parallelism is beneficial
- Observe reducer behavior with concurrent updates

Following SOLID:
- Single Responsibility: Only demonstration, not production code
- Open/Closed: Easy to add more parallel tasks
"""

import logging
from typing import Dict, Any, List
import asyncio
from datetime import datetime

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from ..state import (
    AdvancedAgentState, 
    ParallelTask, 
    create_initial_state
)
from ..parallel import FanOutNode, FanInNode
from ..aggregation import ResultAggregator

logger = logging.getLogger(__name__)


class ParallelExecutionDemo:
    """
    Complete demo of parallel execution workflow.
    
    This is an educational example that can run standalone
    to show how parallel execution works in LangGraph.
    """
    
    def __init__(self, llm: ChatOpenAI):
        """
        Initialize demo with LLM for synthesis.
        
        Args:
            llm: Language model for response generation
        """
        self.llm = llm
        self.fan_out = FanOutNode()
        self.fan_in = FanInNode(merge_strategy="dict")
        self.aggregator = ResultAggregator(llm=llm, use_llm_synthesis=True)
    
    async def run_demo(self, user_message: str = None) -> Dict[str, Any]:
        """
        Run complete parallel execution demo.
        
        Educational: This shows the full lifecycle of a parallel workflow.
        
        Args:
            user_message: Optional custom message (default: demo query)
            
        Returns:
            Final state with results and timing
        """
        if not user_message:
            user_message = "What's the weather in London, the USD to EUR exchange rate, and the current Bitcoin price?"
        
        logger.info("="*80)
        logger.info("PARALLEL EXECUTION DEMO START")
        logger.info("="*80)
        logger.info(f"User Query: {user_message}")
        logger.info("")
        
        # Step 1: Initialize state
        logger.info("[Step 1] Initializing state...")
        state = create_initial_state(
            user_id="demo_user",
            message=user_message,
            session_id="demo_session"
        )
        
        # Step 2: Create parallel tasks
        logger.info("[Step 2] Creating parallel tasks...")
        parallel_tasks = self._create_demo_tasks()
        state["parallel_tasks"] = parallel_tasks
        
        logger.info(f"  → Created {len(parallel_tasks)} tasks:")
        for task in parallel_tasks:
            logger.info(f"    - {task.task_id}: {task.tool_name}")
        logger.info("")
        
        # Step 3: Fan-out (prepare for parallel execution)
        logger.info("[Step 3] Fan-out: Spawning parallel tasks...")
        start_time = datetime.now()
        
        fan_out_result = await self.fan_out(state)
        state.update(fan_out_result)
        
        logger.info("  → Fan-out complete")
        logger.info(f"  → Parallel execution active: {state['parallel_execution_active']}")
        logger.info("")
        
        # Step 4: Execute tasks in parallel (simulated)
        logger.info("[Step 4] Executing tasks in parallel...")
        logger.info("  → Simulating parallel API calls...")
        
        # In real implementation, LangGraph would execute these in parallel
        # For demo, we simulate with asyncio.gather
        results = await self._execute_tasks_parallel(parallel_tasks)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"  → All tasks completed in {execution_time:.2f}s")
        logger.info("")
        
        # Update state with results
        state["parallel_results"] = results
        
        # Step 5: Fan-in (aggregate results)
        logger.info("[Step 5] Fan-in: Aggregating results...")
        fan_in_result = await self.fan_in(state)
        state.update(fan_in_result)
        
        aggregation = state.get("aggregation_result")
        if aggregation:
            logger.info(f"  → Successful tasks: {aggregation.successful_tasks}/{aggregation.total_tasks}")
            logger.info(f"  → Failed tasks: {aggregation.failed_tasks}")
        logger.info("")
        
        # Step 6: Synthesize final response
        logger.info("[Step 6] Synthesizing final response...")
        aggregator_result = await self.aggregator(state)
        state.update(aggregator_result)
        
        final_answer = state.get("final_answer", "No answer generated")
        logger.info(f"  → Final answer ({len(final_answer)} chars):")
        logger.info("")
        logger.info("─" * 80)
        logger.info(final_answer)
        logger.info("─" * 80)
        logger.info("")
        
        # Summary
        logger.info("="*80)
        logger.info("DEMO SUMMARY")
        logger.info("="*80)
        logger.info(f"Total execution time: {execution_time:.2f}s")
        logger.info(f"Tasks executed: {len(parallel_tasks)}")
        logger.info(f"Success rate: {aggregation.successful_tasks}/{aggregation.total_tasks}")
        logger.info("")
        logger.info("KEY LEARNINGS:")
        logger.info("1. Parallel execution reduces latency (vs sequential)")
        logger.info("2. Reducers safely merge results from concurrent nodes")
        logger.info("3. Partial failures are handled gracefully")
        logger.info("4. State remains consistent despite concurrent updates")
        logger.info("="*80)
        
        return {
            "state": state,
            "execution_time": execution_time,
            "final_answer": final_answer,
            "aggregation": aggregation
        }
    
    def _create_demo_tasks(self) -> List[ParallelTask]:
        """
        Create three parallel tasks for demo.
        
        Educational: Shows how to structure independent tasks.
        """
        tasks = [
            ParallelTask(
                task_id="weather_task",
                task_type="api_call",
                tool_name="weather",
                arguments={"city": "London"},
                timeout_seconds=5.0
            ),
            ParallelTask(
                task_id="fx_task",
                task_type="api_call",
                tool_name="fx_rates",
                arguments={"from": "USD", "to": "EUR", "amount": 100},
                timeout_seconds=5.0
            ),
            ParallelTask(
                task_id="crypto_task",
                task_type="api_call",
                tool_name="crypto_price",
                arguments={"symbol": "BTC"},
                timeout_seconds=5.0
            )
        ]
        return tasks
    
    async def _execute_tasks_parallel(self, tasks: List[ParallelTask]) -> List[Dict[str, Any]]:
        """
        Simulate parallel task execution.
        
        Educational: In real LangGraph, this would be handled by Send() API.
        
        Args:
            tasks: List of tasks to execute
            
        Returns:
            List of task results
        """
        # Execute all tasks concurrently using asyncio.gather
        results = await asyncio.gather(
            *[self._execute_single_task(task) for task in tasks],
            return_exceptions=True
        )
        
        # Format results
        formatted_results = []
        for i, result in enumerate(results):
            task = tasks[i]
            
            if isinstance(result, Exception):
                # Task failed
                formatted_results.append({
                    "task_id": task.task_id,
                    "tool_name": task.tool_name,
                    "success": False,
                    "error": str(result),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Task succeeded
                formatted_results.append({
                    "task_id": task.task_id,
                    "tool_name": task.tool_name,
                    "success": True,
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                })
        
        return formatted_results
    
    async def _execute_single_task(self, task: ParallelTask) -> Dict[str, Any]:
        """
        Simulate execution of a single task.
        
        Educational: Shows what a task execution looks like.
        In real implementation, this would call actual tools.
        
        Args:
            task: Task to execute
            
        Returns:
            Task result data
        """
        logger.info(f"  → Executing {task.task_id}...")
        
        # Simulate API call latency
        await asyncio.sleep(0.5 + (hash(task.task_id) % 10) / 10)
        
        # Return simulated data based on tool
        if task.tool_name == "weather":
            result = {
                "city": task.arguments.get("city", "Unknown"),
                "temperature": 15.5,
                "condition": "Partly Cloudy",
                "humidity": 65
            }
        elif task.tool_name == "fx_rates":
            result = {
                "from": task.arguments.get("from", "USD"),
                "to": task.arguments.get("to", "EUR"),
                "rate": 0.85,
                "amount": task.arguments.get("amount", 100),
                "converted": task.arguments.get("amount", 100) * 0.85
            }
        elif task.tool_name == "crypto_price":
            result = {
                "symbol": task.arguments.get("symbol", "BTC"),
                "price_usd": 45000.00,
                "change_24h": 2.5
            }
        else:
            result = {"message": "Simulated result"}
        
        logger.info(f"  ✓ {task.task_id} completed")
        return result


async def main():
    """
    Standalone demo runner.
    
    Run this file directly to see the parallel execution demo.
    """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4-turbo-preview",
        temperature=0.7,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Run demo
    demo = ParallelExecutionDemo(llm)
    await demo.run_demo()


if __name__ == "__main__":
    # Enable debug logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # Run demo
    asyncio.run(main())
