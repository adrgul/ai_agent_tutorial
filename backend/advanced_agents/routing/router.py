"""
Dynamic Router - LLM-based intelligent routing for complex workflows.

This module implements dynamic routing that can decide at runtime:
- Which single node to execute next
- Multiple nodes to execute in parallel
- When to loop back for more information
- When to terminate the workflow

WHY Dynamic Routing?
- Static routing is too rigid for complex AI workflows
- Different user requests need different execution paths
- Enables adaptive workflows that respond to intermediate results
- Essential for Plan-and-Execute (routing between plan steps)

HOW it works:
1. LLM analyzes current state and user request
2. Decides which tools/nodes are needed
3. Determines if tools can run in parallel
4. Returns structured routing decision
5. Graph uses decision to route execution

CRITICAL: Routing vs. Planning
- Router: Decides WHICH nodes to execute NOW
- Planner: Decides ALL steps for entire workflow
- Router is reactive, Planner is proactive
- Both are needed for complex workflows

Following SOLID:
- Single Responsibility: Only routing decisions
- Open/Closed: Easy to add new routing strategies
- Dependency Inversion: Depends on LLM interface
"""

import json
import logging
from typing import Dict, Any, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..state import AdvancedAgentState
from observability.metrics import record_node_duration, agent_execution_count
from observability.llm_instrumentation import instrumented_llm_call

logger = logging.getLogger(__name__)


class RoutingDecision(BaseModel):
    """
    Structured routing decision from LLM.
    
    WHY Pydantic?
    - Forces LLM to output valid JSON structure
    - Type safety for routing logic
    - Clear schema for debugging
    """
    next_nodes: List[str] = Field(
        description="List of node names to execute (1 for single, >1 for parallel)"
    )
    reasoning: str = Field(
        description="Explanation of why these nodes were chosen"
    )
    is_parallel: bool = Field(
        description="Whether nodes should execute in parallel"
    )
    is_terminal: bool = Field(
        default=False,
        description="Whether workflow should terminate after these nodes"
    )
    confidence: float = Field(
        default=1.0,
        description="Confidence in routing decision (0-1)"
    )


class DynamicRouter:
    """
    LangGraph node that dynamically routes execution flow.
    
    This router can:
    1. Route to single node (sequential execution)
    2. Route to multiple nodes (parallel execution)
    3. Loop back for iterative refinement
    4. Terminate workflow when goal is achieved
    
    Educational: This is the "brain" of complex workflows!
    """
    
    def __init__(
        self, 
        llm: ChatOpenAI, 
        available_nodes: Dict[str, str],
        enable_parallel: bool = True
    ):
        """
        Initialize dynamic router.
        
        Args:
            llm: Language model for routing decisions
            available_nodes: Dict of node_name -> description
            enable_parallel: Whether to allow parallel routing
        """
        self.llm = llm
        self.available_nodes = available_nodes
        self.enable_parallel = enable_parallel
        
        # Build node descriptions for LLM
        self.node_descriptions = self._build_node_descriptions()
    
    def _build_node_descriptions(self) -> str:
        """
        Format available nodes for LLM prompt.
        
        WHY: LLM needs to know what nodes exist and what they do.
        """
        descriptions = []
        for node_name, desc in self.available_nodes.items():
            descriptions.append(f"- {node_name}: {desc}")
        return "\n".join(descriptions)
    
    async def __call__(self, state: AdvancedAgentState) -> Dict[str, Any]:
        """
        Make routing decision based on current state.
        
        WHY async?
        - LLM call is I/O bound
        - Allows other work while waiting
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with routing_decision and next_nodes
        """
        with record_node_duration("router"):
            # Track agent execution count on first router call
            iteration_count = state.get("iteration_count", 0)
            if iteration_count == 0:
                agent_execution_count.inc()
            
            # Extract context
            messages = state.get("messages", [])
            plan_completed = state.get("plan_completed", False)
            parallel_active = state.get("parallel_execution_active", False)
            max_iterations = state.get("max_iterations", 20)
            
            logger.info("[ROUTER] Making routing decision...")
            
            # Check termination conditions
            if iteration_count >= max_iterations:
                logger.warning("[ROUTER] Max iterations reached, terminating")
                return {
                    "routing_decision": {
                        "next_nodes": ["END"],
                        "reasoning": "Maximum iterations reached",
                        "is_terminal": True
                    },
                    "next_nodes": ["END"],
                    "debug_logs": ["[ROUTER] ⚠️ Max iterations reached"]
                }
            
            if plan_completed and not parallel_active:
                logger.info("[ROUTER] Plan completed, routing to finalize")
                return {
                    "routing_decision": {
                        "next_nodes": ["aggregator"],
                        "reasoning": "All plan steps completed",
                        "is_terminal": True
                    },
                    "next_nodes": ["aggregator"],
                    "debug_logs": ["[ROUTER] ✓ Routing to aggregator"]
                }
            
            # Get LLM routing decision
            decision = await self._get_routing_decision(state)
            
            # Build state updates
            decision_dict = decision.dict()
            state_updates = {
                "routing_decision": decision_dict,
                "next_nodes": decision.next_nodes,
                "iteration_count": iteration_count + 1,
                "debug_logs": [
                    f"[ROUTER] → {', '.join(decision.next_nodes)}",
                    f"[ROUTER] Reason: {decision.reasoning}"
                ]
            }
            
            # If routing to MCP execution, get tool details
            if "mcp_tool_execution" in decision.next_nodes or "mcp_parallel_execution" in decision.next_nodes:
                tool_info = await self._select_mcp_tool(state, decision.next_nodes[0])
                decision_dict.update(tool_info)
                
                # For parallel execution, also set parallel_tasks in state root
                if "mcp_parallel_execution" in decision.next_nodes and "tool_calls" in tool_info:
                    state_updates["parallel_tasks"] = tool_info["tool_calls"]
                    logger.info(f"[ROUTER] Set parallel_tasks with {len(tool_info['tool_calls'])} tasks")
            
            # If routing to individual tool nodes (tool_weather, tool_geocode, etc.), extract arguments
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
                        logger.info(f"[ROUTER] Created parallel task: {tool_name} with args {task.arguments}")
                    
                    state_updates["parallel_tasks"] = parallel_tasks
                    logger.info(f"[ROUTER] Set parallel_tasks with {len(parallel_tasks)} tasks for fan-out")
                else:
                    # Single tool execution
                    tool_node = decision.next_nodes[0]
                    tool_args = await self._select_individual_tool_args(state, tool_node)
                    decision_dict.update(tool_args)
                    logger.info(f"[ROUTER] Routing to {tool_node} with args: {tool_args.get('arguments', {})}")
            
            logger.info(f"[ROUTER] Decision: {decision.next_nodes} (parallel={decision.is_parallel})")
            
            return state_updates
    
    async def _get_routing_decision(self, state: AdvancedAgentState) -> RoutingDecision:
        """
        Use LLM to make routing decision.
        
        WHY LLM for routing?
        - Can understand complex context
        - Adapts to unexpected situations
        - No hardcoded rules needed
        - Educational: shows LLM reasoning for decisions
        
        Args:
            state: Current state
            
        Returns:
            Structured routing decision
        """
        # Build context summary
        messages = state.get("messages", [])
        last_message = messages[-1].content if messages else "No message"
        plan = state.get("execution_plan")
        plan_summary = f"Plan: {plan.goal} ({len(plan.steps)} steps)" if plan else "No plan"
        
        # Extract user preferences from SystemMessage (if present)
        user_preferences = ""
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'system' and 'Preferences:' in msg.content:
                user_preferences = msg.content
                break
        
        # Get MCP tools info
        alphavantage_tools = state.get("alphavantage_tools", [])
        deepwiki_tools = state.get("deepwiki_tools", [])
        mcp_tools_available = len(alphavantage_tools) + len(deepwiki_tools) > 0
        
        # Build MCP tools summary
        mcp_summary = ""
        if alphavantage_tools:
            mcp_summary += f"\n- AlphaVantage MCP: {len(alphavantage_tools)} financial tools available"
            # Sample some tool names
            sample_tools = [t.get("name", "") for t in alphavantage_tools[:5]]
            mcp_summary += f"\n  Examples: {', '.join(sample_tools)}"
        if deepwiki_tools:
            mcp_summary += f"\n- DeepWiki MCP: {len(deepwiki_tools)} knowledge tools available"
            sample_tools = [t.get("name", "") for t in deepwiki_tools[:3]]
            mcp_summary += f"\n  Examples: {', '.join(sample_tools)}"
        
        system_prompt = self._create_routing_prompt(mcp_tools_available)
        
        user_prompt = f"""Current state:
- Last user message: {last_message[:200]}
- {plan_summary}
- Parallel execution active: {state.get('parallel_execution_active', False)}
- Iteration: {state.get('iteration_count', 0)}
{mcp_summary}

{user_preferences if user_preferences else ''}

What nodes should execute next? Output JSON only."""
        
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
            decision_json = response.content
            
            # Parse JSON
            decision = self._parse_decision(decision_json)
            return decision
            
        except Exception as e:
            logger.error(f"[ROUTER] Failed to get routing decision: {e}")
            # Fallback to safe default
            return RoutingDecision(
                next_nodes=["direct_response"],
                reasoning=f"Error in routing: {str(e)}",
                is_parallel=False,
                is_terminal=True,
                confidence=0.0
            )
    
    def _create_routing_prompt(self, mcp_tools_available: bool = False) -> str:
        """
        Create system prompt for routing decisions.
        
        WHY detailed prompt?
        - LLM needs clear instructions for structured output
        - Examples help LLM understand parallel vs sequential
        - Constraints prevent invalid routing decisions
        """
        parallel_note = ""
        if self.enable_parallel:
            parallel_note = """
If multiple nodes don't depend on each other, set is_parallel=true to run them concurrently.
Example: weather and fx_rates can run in parallel."""
        
        # CRITICAL: Add guidance for knowledge-only questions
        knowledge_note = """
CRITICAL - KNOWLEDGE/ANALYSIS QUESTIONS (NO TOOLS NEEDED):
When the user asks questions that require ONLY general knowledge or analysis, use "direct_response".
These include:
- Analysis questions: "Analyze X", "Compare X and Y", "What are the pros and cons of X"
- Explanations: "Explain X", "How does X work", "What is X"
- Opinions: "Which is better X or Y", "Recommend X"
- Lists: "List 10 X", "Name some X"
- General knowledge: capital cities, history, definitions, concepts

DO NOT use "planner" for these! The planner is for tasks requiring TOOL CALLS (weather, stocks, files).
"""
        
        mcp_note = ""
        if mcp_tools_available:
            mcp_note = """
IMPORTANT - MCP TOOLS:
- Use "mcp_tool_execution" for executing a SINGLE MCP tool (stocks, forex, crypto, economic data, etc.)
- Use "mcp_parallel_execution" for executing MULTIPLE MCP tools concurrently (e.g., multiple stock quotes)
- MCP tools handle: stock prices, forex rates, crypto prices, technical indicators, economic data, etc.
- AlphaVantage MCP provides 118 financial data tools
- If user asks for stock prices, forex rates, crypto, or financial data → use mcp_tool_execution or mcp_parallel_execution

EXAMPLES with MCP:
- "Get Apple stock price" → ["mcp_tool_execution"] (single call)
- "Get Apple, Microsoft, Google stock prices" → ["mcp_parallel_execution"] (3 parallel calls)
- "Get USD/EUR rate" → ["mcp_tool_execution"] (single currency exchange)
- "Get USD to EUR, GBP, JPY rates" → ["mcp_parallel_execution"] (3 parallel calls)
"""
        
        # Add note about individual API caller tool nodes
        tool_note = """
INDIVIDUAL TOOL NODES (from basic workflow):
- Use "tool_weather" for weather forecast queries (e.g., "What's the weather in Budapest?")
- Use "tool_geocode" for address to coordinates conversion or reverse geocoding
- Use "tool_ip_geolocation" for IP address location lookup
- Use "tool_fx_rates" for basic currency exchange rates (use MCP for advanced forex data)
- Use "tool_crypto_price" for cryptocurrency prices (BTC, ETH, etc.)
- Use "tool_create_file" for saving text to files
- Use "tool_search_history" for searching past conversations

EXAMPLES with individual tools:
- "What's the weather in London?" → ["tool_weather"]
- "Convert my address to coordinates" → ["tool_geocode"]
- "Where is IP 8.8.8.8?" → ["tool_ip_geolocation"]
- "What's the current price of Bitcoin?" → ["tool_crypto_price"]
- "Save this to a file" → ["tool_create_file"]
"""
        
        return f"""You are a workflow routing expert. Your job is to decide which nodes should execute next.

Available nodes:
{self.node_descriptions}

{knowledge_note}

RULES:
1. Output ONLY valid JSON matching RoutingDecision schema
2. Choose nodes based on what's needed to fulfill user request
3. Set is_terminal=true if workflow should end after these nodes
4. Provide clear reasoning for your decision
5. For analysis/explanation/comparison questions WITHOUT tool needs → ALWAYS use "direct_response"
{parallel_note}
{mcp_note}
{tool_note}

OUTPUT FORMAT (JSON):
{{
  "next_nodes": ["node_name"],
  "reasoning": "Why these nodes were chosen",
  "is_parallel": false,
  "is_terminal": false,
  "confidence": 1.0
}}

EXAMPLE 1 - Single MCP tool:
State: User asks "What's the current stock price of Apple (AAPL)?"
Decision:
{{
  "next_nodes": ["mcp_tool_execution"],
  "reasoning": "User wants a single stock price, use MCP tool execution",
  "is_parallel": false,
  "is_terminal": false,
  "confidence": 1.0
}}

EXAMPLE 2 - Parallel MCP tools:
State: User asks "Get me the current stock prices for Apple (AAPL), Microsoft (MSFT), and Google (GOOGL)."
Decision:
{{
  "next_nodes": ["mcp_parallel_execution"],
  "reasoning": "User wants multiple stock prices, use parallel MCP execution for speed",
  "is_parallel": false,
  "is_terminal": false,
  "confidence": 1.0
}}

EXAMPLE 3 - Direct response (no tools needed):
State: User asks "What is the capital of France?"
Decision:
{{
  "next_nodes": ["direct_response"],
  "reasoning": "Simple factual question, no tools needed",
  "is_parallel": false,
  "is_terminal": true,
  "confidence": 1.0
}}

EXAMPLE 4 - Analysis/comparison question (MUST use direct_response):
State: User asks "Analyze the pros and cons of Python, JavaScript, and Java"
Decision:
{{
  "next_nodes": ["direct_response"],
  "reasoning": "Analysis/comparison question requires only general knowledge, no tools needed",
  "is_parallel": false,
  "is_terminal": true,
  "confidence": 1.0
}}

EXAMPLE 5 - Explanation question (MUST use direct_response):
State: User asks "Explain how machine learning works"
Decision:
{{
  "next_nodes": ["direct_response"],
  "reasoning": "Explanation question requires only knowledge synthesis, no tools needed",
  "is_parallel": false,
  "is_terminal": true,
  "confidence": 1.0
}}

Now make a routing decision based on the current state."""
    
    def _parse_decision(self, decision_json: str) -> RoutingDecision:
        """
        Parse LLM output into RoutingDecision.
        
        Args:
            decision_json: JSON string from LLM
            
        Returns:
            Validated RoutingDecision object
        """
        # Extract JSON from markdown if present
        if "```json" in decision_json:
            decision_json = decision_json.split("```json")[1].split("```")[0].strip()
        elif "```" in decision_json:
            decision_json = decision_json.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        decision_dict = json.loads(decision_json)
        
        # Validate with Pydantic
        return RoutingDecision(**decision_dict)
    
    async def _select_mcp_tool(self, state: AdvancedAgentState, node_type: str) -> Dict[str, Any]:
        """
        Select which MCP tool(s) to call based on user request.
        
        Args:
            state: Current state with MCP tools
            node_type: 'mcp_tool_execution' or 'mcp_parallel_execution'
            
        Returns:
            Dict with tool_name and tool_arguments (or tool_calls for parallel)
        """
        alphavantage_tools = state.get("alphavantage_tools", [])
        deepwiki_tools = state.get("deepwiki_tools", [])
        last_message = state.get("messages", [])[-1].content if state.get("messages") else ""
        
        # Build tool catalog
        tool_catalog = "Available MCP Tools:\n\n"
        if alphavantage_tools:
            tool_catalog += "AlphaVantage Financial Tools:\n"
            for tool in alphavantage_tools[:20]:  # Limit to avoid token overflow
                name = tool.get("name", "")
                desc = tool.get("description", "")
                tool_catalog += f"- {name}: {desc}\n"
        if deepwiki_tools:
            tool_catalog += "\nDeepWiki Knowledge Tools:\n"
            for tool in deepwiki_tools:
                name = tool.get("name", "")
                desc = tool.get("description", "")
                tool_catalog += f"- {name}: {desc}\n"
        
        if node_type == "mcp_parallel_execution":
            prompt = f"""Based on the user's request, select MULTIPLE MCP tools to call in parallel.

User request: {last_message}

{tool_catalog}

Output JSON with an array of tool calls:
{{
  "tool_calls": [
    {{"tool_name": "TOOL_NAME", "tool_arguments": {{"arg1": "value1"}}}},
    {{"tool_name": "TOOL_NAME2", "tool_arguments": {{"arg1": "value2"}}}}
  ]
}}

For stock quotes, use tool name "GLOBAL_QUOTE" with argument "symbol": "TICKER"
For currency exchange, use "CURRENCY_EXCHANGE_RATE" with "from_currency" and "to_currency"
"""
        else:  # mcp_tool_execution
            prompt = f"""Based on the user's request, select ONE MCP tool to call.

User request: {last_message}

{tool_catalog}

Output JSON:
{{
  "tool_name": "TOOL_NAME",
  "tool_arguments": {{"arg1": "value1", "arg2": "value2"}}
}}

For stock quotes, use tool name "GLOBAL_QUOTE" with argument "symbol": "TICKER"
For currency exchange, use "CURRENCY_EXCHANGE_RATE" with "from_currency" and "to_currency"
"""
        
        try:
            response = await instrumented_llm_call(
                llm=self.llm,
                messages=[HumanMessage(content=prompt)],
                model="gpt-4o-mini",
                agent_execution_id=state.get("session_id")
            )
            result_json = response.content
            
            # Extract JSON
            if "```json" in result_json:
                result_json = result_json.split("```json")[1].split("```")[0].strip()
            elif "```" in result_json:
                result_json = result_json.split("```")[1].split("```")[0].strip()
            
            return json.loads(result_json)
        except Exception as e:
            logger.error(f"[ROUTER] Failed to select MCP tool: {e}")
            return {}
    
    async def _select_individual_tool_args(self, state: AdvancedAgentState, tool_node: str) -> Dict[str, Any]:
        """
        Extract arguments for individual API caller tool nodes.
        
        Args:
            state: Current state with user request
            tool_node: Node name like "tool_weather", "tool_geocode", etc.
            
        Returns:
            Dict with "arguments" key containing tool parameters
        """
        last_message = state.get("messages", [])[-1].content if state.get("messages") else ""
        tool_name = tool_node.replace("tool_", "")
        
        # Define parameter schemas for each tool
        tool_schemas = {
            "weather": {
                "description": "Get weather forecast",
                "parameters": ["city OR (lat AND lon)"],
                "example": '{"city": "London"} OR {"lat": 51.5074, "lon": -0.1278}'
            },
            "geocode": {
                "description": "Convert address to coordinates or reverse",
                "parameters": ["address OR (lat AND lon)"],
                "example": '{"address": "1600 Amphitheatre Parkway"} OR {"lat": 37.4224764, "lon": -122.0842499}'
            },
            "ip_geolocation": {
                "description": "Get location from IP address",
                "parameters": ["ip_address"],
                "example": '{"ip_address": "8.8.8.8"}'
            },
            "fx_rates": {
                "description": "Get currency exchange rates",
                "parameters": ["base", "target", "date (optional)"],
                "example": '{"base": "USD", "target": "EUR"} OR {"base": "USD", "target": "EUR", "date": "2024-01-15"}'
            },
            "crypto_price": {
                "description": "Get cryptocurrency prices",
                "parameters": ["symbol", "fiat (optional, default USD)"],
                "example": '{"symbol": "BTC", "fiat": "USD"} OR {"symbol": "ETH"}'
            },
            "create_file": {
                "description": "Save text to a file",
                "parameters": ["filename", "content", "user_id (auto-injected)"],
                "example": '{"filename": "summary.txt", "content": "..."}'
            },
            "search_history": {
                "description": "Search past conversations",
                "parameters": ["query"],
                "example": '{"query": "weather discussions"}'
            }
        }
        
        schema_info = tool_schemas.get(tool_name, {
            "description": f"{tool_name} tool",
            "parameters": [],
            "example": "{}"
        })
        
        # Extract user preferences from messages
        user_prefs_text = ""
        messages = state.get("messages", [])
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'system' and 'Preferences:' in msg.content:
                user_prefs_text = f"\n{msg.content}"
                break
        
        prompt = f"""Based on the user's request, extract the arguments needed to call the {tool_name} tool.

User request: {last_message}
{user_prefs_text}

Tool: {tool_name}
Description: {schema_info["description"]}
Parameters: {", ".join(schema_info["parameters"])}
Example: {schema_info["example"]}

Output ONLY a JSON object with the arguments:
{{
  "arguments": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}

CRITICAL: If the user request doesn't specify all required parameters, use user preferences when available:
- For weather without city: use default_city from preferences
- For other tools: make reasonable inferences

For weather: extract city name or coordinates (or use default_city if not specified)
For geocode: extract address or coordinates
For IP: extract IP address
For fx_rates: extract currency codes (3-letter ISO codes)
For crypto: extract symbol (BTC, ETH, etc.)
For create_file: extract filename and content from context
For search_history: extract search query

Output JSON only, no explanations."""
        
        try:
            response = await instrumented_llm_call(
                llm=self.llm,
                messages=[HumanMessage(content=prompt)],
                model="gpt-4o-mini",
                agent_execution_id=state.get("session_id")
            )
            result_json = response.content
            
            # Extract JSON
            if "```json" in result_json:
                result_json = result_json.split("```json")[1].split("```")[0].strip()
            elif "```" in result_json:
                result_json = result_json.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_json)
            logger.info(f"[ROUTER] Extracted {tool_name} arguments: {result.get('arguments', {})}")
            return result
        except Exception as e:
            logger.error(f"[ROUTER] Failed to extract {tool_name} arguments: {e}")
            return {"arguments": {}}
    
    def route_function(self, state: AdvancedAgentState) -> str:
        """
        Synchronous routing function for LangGraph conditional edges.
        
        WHY separate function?
        - LangGraph conditional edges expect synchronous function
        - Main __call__ is async for LLM calls
        - This provides simple synchronous routing based on state
        
        Args:
            state: Current state with routing_decision
            
        Returns:
            Node name to route to
        """
        routing_decision = state.get("routing_decision", {})
        next_nodes = routing_decision.get("next_nodes", ["END"])
        
        if len(next_nodes) == 1:
            return next_nodes[0]
        else:
            # Multiple nodes means parallel execution
            return "fan_out"  # Route to fan-out node for parallelization
