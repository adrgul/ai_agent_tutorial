"""
Advanced Agent Graph - LangGraph workflow integrating all advanced patterns.

This module wires together:
- Plan-and-Execute workflow
- Parallel execution (fan-out/fan-in)
- Dynamic routing
- Result aggregation

WHY This Graph?
- Demonstrates enterprise-grade agent architecture
- Shows how patterns compose together
- Educational: each edge and node is clearly commented
- Production-ready: handles errors, iterations, termination

GRAPH STRUCTURE:

    START
      ↓
    router ─────────────────┐
      ↓                     │
  ┌───┴───┐                │
  │       │                │
planner  direct           │
  ↓      response          │
executor    ↓              │
  ↓        END             │
  ↓                        │
fan_out ←──────────────────┘
  ↓
  ├→ tool_1 ─┐
  ├→ tool_2 ─┤
  ├→ tool_3 ─┘
  ↓
fan_in
  ↓
aggregator
  ↓
 END

KEY CONCEPTS:
1. Router decides workflow path (plan-execute vs direct vs parallel)
2. Planner+Executor handle multi-step sequential workflows
3. Fan-out/Fan-in enable true parallelism
4. Aggregator synthesizes final response
5. Conditional edges enable dynamic routing

Following SOLID:
- Open/Closed: Easy to add new nodes without changing graph structure
- Dependency Inversion: Graph depends on node interfaces, not implementations
"""

import logging
from typing import Dict, Any, List, Callable
from operator import add

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

from .state import AdvancedAgentState, list_reducer, parallel_results_reducer
from .planning import PlannerNode, ExecutorNode
from .parallel import FanOutNode, FanInNode
from .routing import DynamicRouter
from .aggregation import ResultAggregator
from observability.llm_instrumentation import instrumented_llm_call

logger = logging.getLogger(__name__)


class AdvancedAgentGraph:
    """
    Complete LangGraph workflow with advanced orchestration.
    
    This graph demonstrates:
    - How to compose multiple patterns
    - How routing decisions flow through the graph
    - How state is managed across complex workflows
    - How to handle both sequential and parallel execution
    """
    
    def __init__(
        self,
        llm: ChatOpenAI,
        tools: Dict[str, Any],
        enable_checkpointing: bool = False,
        alphavantage_mcp_client=None,
        deepwiki_mcp_client=None,
        alphavantage_url: str = None,
        deepwiki_url: str = None
    ):
        """
        Initialize advanced agent graph.

        Args:
            llm: Language model for planning, routing, synthesis
            tools: Dictionary of available tools
            enable_checkpointing: Whether to enable state checkpointing
            alphavantage_mcp_client: MCP client for AlphaVantage
            deepwiki_mcp_client: MCP client for DeepWiki
            alphavantage_url: URL for AlphaVantage MCP server
            deepwiki_url: URL for DeepWiki MCP server
        """
        self.llm = llm
        self.tools = tools
        self.enable_checkpointing = enable_checkpointing
        self.alphavantage_mcp_client = alphavantage_mcp_client
        self.deepwiki_mcp_client = deepwiki_mcp_client
        self.alphavantage_url = alphavantage_url
        self.deepwiki_url = deepwiki_url

        # Initialize all nodes
        self._init_nodes()

        # Build the graph
        self.workflow = self._build_graph()
    
    def _init_nodes(self):
        """
        Initialize all node instances.

        WHY separate initialization?
        - Clear separation of construction and composition
        - Easier to test individual nodes
        - Centralized configuration
        """
        # Build tool descriptions for planner and router
        tool_descriptions = self._build_tool_descriptions()
        available_nodes = self._build_available_nodes()

        # Planning nodes
        self.planner = PlannerNode(
            llm=self.llm,
            available_tools=tool_descriptions
        )
        self.executor = ExecutorNode(
            max_retries=3,
            retry_delay_seconds=1.0
        )

        # Parallel execution nodes
        self.fan_out = FanOutNode(tools=self.tools)  # Pass tools for parallel execution
        self.fan_in = FanInNode(merge_strategy="dict")

        # Routing node
        self.router = DynamicRouter(
            llm=self.llm,
            available_nodes=available_nodes,
            enable_parallel=True
        )

        # Aggregation node
        self.aggregator = ResultAggregator(
            llm=self.llm,
            use_llm_synthesis=True
        )

        # MCP nodes (if clients are provided)
        if self.alphavantage_mcp_client and self.alphavantage_url:
            from .mcp_nodes import MCPToolFetcherNode
            self.fetch_alphavantage = MCPToolFetcherNode(
                mcp_client=self.alphavantage_mcp_client,
                server_name="AlphaVantage",
                server_url=self.alphavantage_url
            )
        else:
            self.fetch_alphavantage = None

        if self.deepwiki_mcp_client and self.deepwiki_url:
            from .mcp_nodes import MCPToolFetcherNode
            self.fetch_deepwiki = MCPToolFetcherNode(
                mcp_client=self.deepwiki_mcp_client,
                server_name="DeepWiki",
                server_url=self.deepwiki_url
            )
        else:
            self.fetch_deepwiki = None

        # MCP execution nodes
        if self.alphavantage_mcp_client or self.deepwiki_mcp_client:
            from .mcp_nodes import MCPToolExecutionNode, MCPParallelExecutionNode
            self.mcp_tool_execution = MCPToolExecutionNode(
                alphavantage_client=self.alphavantage_mcp_client,
                deepwiki_client=self.deepwiki_mcp_client
            )
            self.mcp_parallel_execution = MCPParallelExecutionNode(
                alphavantage_client=self.alphavantage_mcp_client,
                deepwiki_client=self.deepwiki_mcp_client
            )
        else:
            self.mcp_tool_execution = None
            self.mcp_parallel_execution = None
    
    def _build_tool_descriptions(self) -> Dict[str, Any]:
        """
        Build tool descriptions for planner.
        
        Returns:
            Dict of tool_name -> tool info
        """
        descriptions = {}
        for tool_name, tool in self.tools.items():
            descriptions[tool_name] = {
                "description": getattr(tool, "description", f"{tool_name} tool"),
                "parameters": getattr(tool, "parameters", {})
            }
        return descriptions
    
    def _build_available_nodes(self) -> Dict[str, str]:
        """
        Build node descriptions for router.
        
        Returns:
            Dict of node_name -> description
        """
        nodes = {
            "planner": "Create a multi-step execution plan for complex multi-step tasks",
            "direct_response": "Generate direct response for simple questions without tools"
        }
        
        # Add MCP execution nodes if available
        if self.alphavantage_mcp_client or self.deepwiki_mcp_client:
            nodes["mcp_tool_execution"] = "Execute a single MCP tool (stocks, forex, economic data)"
            nodes["mcp_parallel_execution"] = "Execute multiple MCP tools in parallel (multiple stocks, forex rates)"
        
        # Add individual tool nodes for direct execution
        tool_descriptions = {
            "tool_weather": "Get weather forecast for a city (single tool call)",
            "tool_geocode": "Convert address to coordinates or reverse geocode (single tool call)",
            "tool_ip_geolocation": "Get location from IP address (single tool call)",
            "tool_fx_rates": "Get currency exchange rates (single tool call)",
            "tool_crypto_price": "Get cryptocurrency prices (single tool call)",
            "tool_create_file": "Save text to a file (single tool call)",
            "tool_search_history": "Search past conversations (single tool call)"
        }
        
        # Only include tools that exist in self.tools
        for tool_key, description in tool_descriptions.items():
            tool_name = tool_key.replace("tool_", "")
            if tool_name in self.tools:
                nodes[tool_key] = description
        
        return nodes
    
    def _build_graph(self) -> StateGraph:
        """
        Build the complete LangGraph workflow.
        
        EDUCATIONAL: This is where all patterns come together!
        
        Returns:
            Compiled LangGraph workflow
        """
        # Create state graph with reducer annotations
        # NOTE: Reducers are defined in AdvancedAgentState via Annotated[]
        workflow = StateGraph(AdvancedAgentState)
        
        # ================================================================
        # ADD NODES
        # ================================================================

        logger.info("[GRAPH] Adding nodes...")

        # MCP tool fetching nodes (if available)
        if self.fetch_alphavantage:
            workflow.add_node("fetch_alphavantage", self.fetch_alphavantage)
        if self.fetch_deepwiki:
            workflow.add_node("fetch_deepwiki", self.fetch_deepwiki)

        # Core orchestration nodes
        workflow.add_node("router", self.router)
        workflow.add_node("planner", self.planner)
        workflow.add_node("executor", self.executor)
        workflow.add_node("fan_out", self.fan_out)
        workflow.add_node("fan_in", self.fan_in)
        workflow.add_node("aggregator", self.aggregator)

        # MCP execution nodes (if available)
        if self.mcp_tool_execution:
            workflow.add_node("mcp_tool_execution", self.mcp_tool_execution)
        if self.mcp_parallel_execution:
            workflow.add_node("mcp_parallel_execution", self.mcp_parallel_execution)

        # Add individual API caller tool nodes from basic workflow
        # These allow direct routing from router to specific tools
        for tool_name in self.tools.keys():
            workflow.add_node(f"tool_{tool_name}", self._create_tool_node(tool_name, self.tools[tool_name]))
        
        logger.info(f"[GRAPH] Added {len(self.tools)} individual tool nodes")

        # Direct response node (bypass planning)
        workflow.add_node("direct_response", self._direct_response_node)

        # ================================================================
        # SET ENTRY POINT
        # ================================================================

        # Start with MCP tool fetching if available, otherwise router
        if self.fetch_alphavantage:
            workflow.set_entry_point("fetch_alphavantage")
            if self.fetch_deepwiki:
                workflow.add_edge("fetch_alphavantage", "fetch_deepwiki")
                workflow.add_edge("fetch_deepwiki", "router")
            else:
                workflow.add_edge("fetch_alphavantage", "router")
        elif self.fetch_deepwiki:
            workflow.set_entry_point("fetch_deepwiki")
            workflow.add_edge("fetch_deepwiki", "router")
        else:
            workflow.set_entry_point("router")
        
        # ================================================================
        # ADD EDGES
        # ================================================================
        
        logger.info("[GRAPH] Adding edges...")
        
        # Router decides first action
        routing_map = {
            "planner": "planner",
            "fan_out": "fan_out",
            "direct_response": "direct_response",
            "aggregator": "aggregator",
            "END": END
        }

        # Add MCP execution routes if available
        if self.mcp_tool_execution:
            routing_map["mcp_tool_execution"] = "mcp_tool_execution"
        if self.mcp_parallel_execution:
            routing_map["mcp_parallel_execution"] = "mcp_parallel_execution"
        
        # Add individual tool routes for direct execution
        for tool_name in self.tools.keys():
            routing_map[f"tool_{tool_name}"] = f"tool_{tool_name}"
        
        logger.info(f"[GRAPH] Router can route to {len(routing_map)} destinations")

        workflow.add_conditional_edges(
            "router",
            self._route_from_router,
            routing_map
        )
        
        # Planner → Executor (start plan execution)
        workflow.add_edge("planner", "executor")
        
        # Executor can:
        # - Continue to next step (loop back to executor)
        # - Complete plan (go to aggregator)
        workflow.add_conditional_edges(
            "executor",
            self._route_from_executor,
            {
                "continue": "executor",  # Loop for next step
                "complete": "aggregator",  # Plan done
                "END": END
            }
        )
        
        # Fan-out spawns parallel tasks
        # In real LangGraph, we'd use Send() API here to spawn parallel branches
        # For now, we route to fan_in which will handle result collection
        workflow.add_edge("fan_out", "fan_in")
        
        # Fan-in → Aggregator (results collected, now synthesize)
        workflow.add_edge("fan_in", "aggregator")
        
        # Note: No edges for individual tool nodes since they're not in the graph
        # Tools are called dynamically by executor/fan_out nodes

        # MCP execution nodes → Aggregator (synthesize results, then END)
        if self.mcp_tool_execution:
            workflow.add_edge("mcp_tool_execution", "aggregator")
        if self.mcp_parallel_execution:
            workflow.add_edge("mcp_parallel_execution", "aggregator")
        
        # Individual tool nodes → Aggregator (can loop or finalize)
        for tool_name in self.tools.keys():
            workflow.add_edge(f"tool_{tool_name}", "aggregator")
        
        logger.info(f"[GRAPH] Connected {len(self.tools)} tool nodes to aggregator")

        # Aggregator → END (workflow complete)
        workflow.add_edge("aggregator", END)
        
        # Direct response → END (simple query, no planning needed)
        workflow.add_edge("direct_response", END)
        
        # ================================================================
        # COMPILE
        # ================================================================
        
        # Add checkpointing if enabled
        checkpointer = MemorySaver() if self.enable_checkpointing else None
        
        logger.info("[GRAPH] Compiling workflow...")
        compiled = workflow.compile(checkpointer=checkpointer)
        
        logger.info("[GRAPH] ✓ Advanced agent graph ready")
        return compiled
    
    # ====================================================================
    # ROUTING FUNCTIONS
    # ====================================================================
    
    def _route_from_router(self, state: AdvancedAgentState) -> str:
        """
        Route from router node based on routing decision.
        
        WHY: Router makes high-level decision about workflow path.
        
        Args:
            state: Current state with routing_decision
            
        Returns:
            Next node name
        """
        routing_decision = state.get("routing_decision", {})
        next_nodes = routing_decision.get("next_nodes", ["direct_response"])
        is_parallel = routing_decision.get("is_parallel", False)
        is_terminal = routing_decision.get("is_terminal", False)
        
        # Check for termination
        if is_terminal and next_nodes[0] == "END":
            return "END"
        
        # If multiple nodes and parallel enabled, go to fan-out
        if len(next_nodes) > 1 and is_parallel:
            return "fan_out"
        
        # If single node, route there
        if len(next_nodes) == 1:
            return next_nodes[0]
        
        # Default to direct response
        return "direct_response"
    
    def _route_from_executor(self, state: AdvancedAgentState) -> str:
        """
        Route from executor based on plan completion.
        
        WHY: Executor needs to either continue to next step or finish plan.
        
        Args:
            state: Current state with plan progress
            
        Returns:
            Next node name
        """
        plan_completed = state.get("plan_completed", False)
        
        if plan_completed:
            # All steps done, aggregate results
            return "complete"
        else:
            # More steps to execute
            return "continue"
    
    # ====================================================================
    # NODE IMPLEMENTATIONS
    # ====================================================================
    
    def _create_tool_node(self, tool_name: str, tool: Any) -> Callable:
        """
        Create a LangGraph node for a tool.
        
        WHY: Wraps tools in node interface for graph execution.
        
        Args:
            tool_name: Name of the tool
            tool: Tool instance
            
        Returns:
            Async function that can be used as LangGraph node
        """
        async def tool_node(state: AdvancedAgentState) -> Dict[str, Any]:
            """Execute tool and return result."""
            logger.info(f"[TOOL:{tool_name}] Executing...")
            
            # Get arguments from routing decision or state
            routing_decision = state.get("routing_decision", {})
            arguments = routing_decision.get("arguments", {})
            
            # CRITICAL: Add user_id for file creation tool
            if tool_name == "create_file":
                user_id = state.get("user_id") or state.get("session_id", "default")
                arguments["user_id"] = user_id
                logger.info(f"[TOOL:{tool_name}] Injected user_id: {user_id}")
            
            try:
                # Execute tool
                result = await tool.execute(**arguments)
                
                logger.info(f"[TOOL:{tool_name}] ✓ Success")
                
                return {
                    "tools_called": [{
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "result": result,
                        "success": True
                    }],
                    "aggregated_data": {tool_name: result},
                    "debug_logs": [f"[TOOL:{tool_name}] ✓ Executed successfully"]
                }
            
            except Exception as e:
                logger.error(f"[TOOL:{tool_name}] ✗ Error: {e}")
                
                return {
                    "tools_called": [{
                        "tool_name": tool_name,
                        "arguments": arguments,
                        "error": str(e),
                        "success": False
                    }],
                    "debug_logs": [f"[TOOL:{tool_name}] ✗ Error: {str(e)}"]
                }
        
        return tool_node
    
    async def _direct_response_node(self, state: AdvancedAgentState) -> Dict[str, Any]:
        """
        Generate direct response without planning or tools.
        
        WHY: Not all queries need complex workflows.
        Simple questions should get simple answers.
        
        Args:
            state: Current state
            
        Returns:
            State update with final_answer
        """
        logger.info("[DIRECT] Generating direct response...")
        
        user_message = state.get("messages", [])[-1].content if state.get("messages") else ""
        
        # Use LLM to generate response
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content="You are a helpful AI assistant. Answer concisely."),
            HumanMessage(content=user_message)
        ]
        
        try:
            response = await instrumented_llm_call(
                llm=self.llm,
                messages=messages,
                model="gpt-4o-mini",
                agent_execution_id=state.get("session_id")
            )
            answer = response.content
            
            logger.info(f"[DIRECT] ✓ Generated response ({len(answer)} chars)")
            
            return {
                "final_answer": answer,
                "debug_logs": ["[DIRECT] ✓ Direct response generated"]
            }
        
        except Exception as e:
            logger.error(f"[DIRECT] ✗ Error: {e}")
            return {
                "final_answer": f"I apologize, but I encountered an error: {str(e)}",
                "debug_logs": [f"[DIRECT] ✗ Error: {str(e)}"]
            }
    
    # ====================================================================
    # PUBLIC API
    # ====================================================================
    
    async def run(self, state: AdvancedAgentState) -> AdvancedAgentState:
        """
        Execute the workflow with given initial state.
        
        Args:
            state: Initial state
            
        Returns:
            Final state after workflow completion
        """
        logger.info("="*80)
        logger.info("ADVANCED AGENT WORKFLOW START")
        logger.info("="*80)
        
        # Inject tools into state if not already present
        if "tools" not in state or not state["tools"]:
            state["tools"] = self.tools
            logger.info(f"[GRAPH] Injected {len(self.tools)} tools into state")
        
        # Inject MCP clients into state for executor to use
        if self.alphavantage_mcp_client:
            state["alphavantage_mcp_client"] = self.alphavantage_mcp_client
            logger.info("[GRAPH] Injected AlphaVantage MCP client into state")
        
        if self.deepwiki_mcp_client:
            state["deepwiki_mcp_client"] = self.deepwiki_mcp_client
            logger.info("[GRAPH] Injected DeepWiki MCP client into state")
        
        # Run workflow with increased recursion limit for complex queries
        # Default is 25, we increase to 100 to handle multi-step workflows and complex queries
        # Note: Very complex queries that don't require tools may still hit this limit
        # due to MCP tool fetching at the start of each invocation
        final_state = await self.workflow.ainvoke(
            state, 
            {"recursion_limit": 100}
        )
        
        logger.info("="*80)
        logger.info("WORKFLOW COMPLETE")
        logger.info("="*80)
        
        return final_state
