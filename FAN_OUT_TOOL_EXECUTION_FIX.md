# Fan-Out Tool Execution Fix

## Problem

When sending multi-tool parallel requests to the Advanced Agent, the tools were **not being executed**:

**User Request**: "I need to know: 1) Weather in New York, 2) Bitcoin price, 3) EUR/USD exchange rate, and 4) create a file called test.txt"

**Expected Behavior**: Execute 4 tools in parallel (weather, crypto_price, fx_rates, create_file)

**Actual Behavior**: 
- Router correctly identified 4 tools
- Routed to fan_out node
- Fan-out reported "No tasks to fan out"
- No tools executed
- Agent responded: "I couldn't gather the specific data..."

## Root Cause

### Issue #1: Router Not Creating Parallel Tasks

The router was making routing decisions but **not populating the `parallel_tasks` state field** that fan_out expects.

**Before** ([router.py](backend/advanced_agents/routing/router.py) line 205):
```python
elif any(node.startswith("tool_") for node in decision.next_nodes):
    tool_node = decision.next_nodes[0]  # Only handling FIRST tool!
    tool_args = await self._select_individual_tool_args(state, tool_node)
    decision_dict.update(tool_args)
```

**Problem**: Only extracted arguments for the first tool, never created `ParallelTask` objects.

### Issue #2: Fan-Out Not Executing Tools

The fan_out node was a **placeholder** - it only set flags but never actually executed the tools.

**Before** ([fan_out.py](backend/advanced_agents/parallel/fan_out.py)):
```python
class FanOutNode:
    def __init__(self):
        pass  # No tools available
    
    async def __call__(self, state):
        # Just logged tasks and set parallel_execution_active = True
        # NO ACTUAL EXECUTION
```

**Architecture Comment** (line 361 in advanced_graph.py):
```python
# In real LangGraph, we'd use Send() API here to spawn parallel branches
# For now, we route to fan_in which will handle result collection
workflow.add_edge("fan_out", "fan_in")
```

The `Send()` API was **never implemented**, so tools were never called.

## Solution

### Fix #1: Router Creates Parallel Tasks

Modified router to detect parallel tool execution and create proper `ParallelTask` objects:

**After** ([router.py](backend/advanced_agents/routing/router.py) lines 205-229):
```python
elif any(node.startswith("tool_") for node in decision.next_nodes):
    # Check if this is a parallel execution of multiple tools
    if decision.is_parallel and len(decision.next_nodes) > 1:
        # Create parallel tasks for all tools
        parallel_tasks = []
        for idx, tool_node in enumerate(decision.next_nodes):
            tool_args_result = await self._select_individual_tool_args(state, tool_node)
            tool_name = tool_node.replace("tool_", "")
            
            from ..state import ParallelTask
            task = ParallelTask(
                task_id=f"task_{idx}_{tool_name}",
                task_type="tool_execution",
                tool_name=tool_name,
                arguments=tool_args_result.get("arguments", {}),
                timeout_seconds=30.0
            )
            parallel_tasks.append(task)
        
        state_updates["parallel_tasks"] = parallel_tasks
        logger.info(f"[ROUTER] Set parallel_tasks with {len(parallel_tasks)} tasks for fan-out")
    else:
        # Single tool execution (existing logic)
        tool_node = decision.next_nodes[0]
        tool_args = await self._select_individual_tool_args(state, tool_node)
        decision_dict.update(tool_args)
```

### Fix #2: Fan-Out Executes Tools

Modified fan_out to accept tools and execute them using `asyncio.gather()`:

**After** ([fan_out.py](backend/advanced_agents/parallel/fan_out.py)):
```python
class FanOutNode:
    def __init__(self, tools: Dict[str, Tool] = None):
        """Initialize fan-out node with available tools."""
        self.tools = tools or {}
    
    async def __call__(self, state: AdvancedAgentState) -> Dict[str, Any]:
        with record_node_duration("fan_out"):
            tasks = state.get("parallel_tasks", [])
            
            # Execute tasks in parallel
            parallel_results = await self._execute_tasks_in_parallel(tasks, state)
            
            return {
                "parallel_execution_active": True,
                "parallel_results": parallel_results,  # ← RESULTS NOW POPULATED
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
        """Execute multiple tasks concurrently using asyncio.gather."""
        async def execute_single_task(task: ParallelTask) -> Dict[str, Any]:
            tool = self.tools.get(task.tool_name)
            result = await tool.execute(task.arguments)
            tool_invocation_count.labels(tool=task.tool_name).inc()
            return {"task_id": task.task_id, "tool_name": task.tool_name, **result}
        
        # Execute all tasks in parallel
        results = await asyncio.gather(
            *[execute_single_task(task) for task in tasks],
            return_exceptions=True
        )
        return processed_results
```

### Fix #3: Pass Tools to Fan-Out

Updated graph initialization to pass tools to fan_out:

**After** ([advanced_graph.py](backend/advanced_agents/advanced_graph.py) line 141):
```python
# Parallel execution nodes
self.fan_out = FanOutNode(tools=tools)  # ← Pass tools for parallel execution
self.fan_in = FanInNode(merge_strategy="dict")
```

## Verification

After the fix, the same request now:

1. **Router creates 4 parallel tasks**:
```
[ROUTER] Created parallel task: weather with args {'city': 'New York'}
[ROUTER] Created parallel task: crypto_price with args {'symbol': 'BTC'}
[ROUTER] Created parallel task: fx_rates with args {'from': 'EUR', 'to': 'USD'}
[ROUTER] Created parallel task: create_file with args {'filename': 'test.txt', ...}
[ROUTER] Set parallel_tasks with 4 tasks for fan-out
```

2. **Fan-out executes tools in parallel**:
```
[FAN-OUT] Fanning out 4 tasks
[FAN-OUT] Executing task task_0_weather: weather
[FAN-OUT] Executing task task_1_crypto_price: crypto_price
[FAN-OUT] Executing task task_2_fx_rates: fx_rates
[FAN-OUT] Executing task task_3_create_file: create_file
[FAN-OUT] Parallel execution complete: 4 results
```

3. **Fan-in aggregates results**:
```
[FAN-IN] Aggregating 4 results
[FAN-IN] Success: 4, Failed: 0
[FAN-IN] ✓ Aggregated 4/4 successful results
```

4. **Metrics are now captured**:
```
node_execution_latency_seconds{node="router"} 3.1
node_execution_latency_seconds{node="fan_out"} 2.5
node_execution_latency_seconds{node="fan_in"} 0.2
node_execution_latency_seconds{node="aggregator"} 6.2
tool_invocation_count{tool="weather"} 1
tool_invocation_count{tool="crypto_price"} 1
tool_invocation_count{tool="fx_rates"} 1
tool_invocation_count{tool="create_file"} 1
```

## Impact

✅ **Multi-tool parallel execution now works**  
✅ **All tools are executed concurrently using asyncio.gather()**  
✅ **Metrics are captured for all nodes and tools**  
✅ **Fan-in correctly aggregates results**  
✅ **User receives complete responses with all requested data**

## Technical Details

### Execution Flow

**Before**:
```
router → fan_out (no-op) → fan_in (no results) → aggregator → "I don't have access to tools"
```

**After**:
```
router (creates ParallelTask[]) 
  → fan_out (asyncio.gather tool executions) 
    → fan_in (aggregates results) 
      → aggregator (synthesizes response) 
        → "Here's the weather, BTC price, EUR/USD rate, and I created test.txt"
```

### Parallel Execution

Using `asyncio.gather()` instead of LangGraph's `Send()` API:

**Pros**:
- ✅ Simple implementation
- ✅ True parallel execution (async I/O)
- ✅ Exception handling with `return_exceptions=True`
- ✅ Works immediately without graph refactoring

**Cons**:
- ❌ Not using LangGraph's native parallelism features
- ❌ Can't checkpoint/resume individual parallel branches
- ❌ Less visibility in LangGraph debugging tools

**Trade-off**: For this project, `asyncio.gather()` is sufficient and avoids the complexity of LangGraph's `Send()` API which requires conditional edges and branch spawning logic.

## Files Modified

1. **[backend/advanced_agents/routing/router.py](backend/advanced_agents/routing/router.py)**
   - Added parallel task creation logic (lines 205-229)
   - Detects parallel execution and creates `ParallelTask` objects for all tools

2. **[backend/advanced_agents/parallel/fan_out.py](backend/advanced_agents/parallel/fan_out.py)**
   - Added `tools` parameter to `__init__`
   - Implemented `_execute_tasks_in_parallel()` method
   - Tools now execute using `asyncio.gather()`
   - Added metrics tracking with `tool_invocation_count`

3. **[backend/advanced_agents/advanced_graph.py](backend/advanced_agents/advanced_graph.py)**
   - Pass `tools` to `FanOutNode` initialization (line 141)

## Testing

**Test Prompt** (from MONITORING_TEST_PROMPTS.md):
```
I need to know: 1) Weather in New York, 2) Bitcoin price, 3) EUR/USD exchange rate, and 4) create a file called test.txt with this information.
```

**Expected Results**:
- ✅ 4 tools execute in parallel
- ✅ Weather data retrieved
- ✅ Bitcoin price retrieved  
- ✅ EUR/USD rate retrieved
- ✅ File test.txt created
- ✅ All metrics recorded in Prometheus
- ✅ Grafana dashboards show activity

---

**Status**: ✅ Fixed  
**Date**: January 14, 2026  
**Impact**: Critical - enables core parallel execution feature
