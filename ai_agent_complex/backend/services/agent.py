"""
Service layer - LangGraph agent implementation with RAG integration.
Following SOLID:
- Single Responsibility - Agent handles orchestration, delegates tool execution.
- Dependency Inversion - Agent depends on tool abstractions.
- Open/Closed - Easy to add new tools without modifying agent core logic.
"""
from typing import List, Dict, Any, Optional, Annotated, Sequence
from typing_extensions import TypedDict
import json
import logging
import asyncio
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# Observability imports
from observability.metrics import record_node_duration, record_error
from observability.llm_instrumentation import instrumented_llm_call
from observability.correlation import get_request_id, add_request_id_to_state

from domain.models import Message, Memory, WorkflowState, ToolCall
from services.tools import (
    WeatherTool, GeocodeTool, IPGeolocationTool,
    FXRatesTool, CryptoPriceTool, FileCreationTool, HistorySearchTool
)
from services.parallel_execution import execute_parallel_mcp_tools

logger = logging.getLogger(__name__)

# Maximum iterations to prevent infinite loops in multi-step workflows
MAX_ITERATIONS = 20  # Increased from 10 to support complex multi-tool requests


def parallel_results_reducer(existing: List[Dict], new: List[Dict]) -> List[Dict]:
    """Merge results from parallel tool executions."""
    # Handle None values
    if existing is None:
        existing = []
    if new is None:
        new = []
    
    existing_ids = {r.get("tool_name", "") + str(r.get("arguments", {})) for r in existing}
    for result in new:
        result_id = result.get("tool_name", "") + str(result.get("arguments", {}))
        if result_id not in existing_ids:
            existing.append(result)
    return existing


class AgentState(TypedDict, total=False):
    """State object for LangGraph agent with RAG support and parallel execution."""
    messages: Sequence[BaseMessage]
    memory: Memory
    tools_called: List[ToolCall]
    current_user_id: str
    next_action: str
    tool_decision: Dict[str, Any]
    iteration_count: int  # Track iterations to prevent infinite loops

    # NEW: RAG fields
    rag_context: Dict[str, Any]  # RAG context (rewritten_query, chunks, citations, etc.)
    rag_metrics: Dict[str, Any]  # RAG performance metrics
    skip_rag: bool  # Flag to skip RAG (e.g., for "reset context")
    
    # MCP Tools
    deepwiki_tools: List[Dict[str, Any]]  # Tools fetched from DeepWiki MCP server
    alphavantage_tools: List[Dict[str, Any]]  # Tools fetched from AlphaVantage MCP server
    debug_logs: List[str]  # Debug information for frontend display
    
    # Parallel execution support
    parallel_tasks: Annotated[List[Dict[str, Any]], parallel_results_reducer]
    parallel_results: Annotated[List[Dict[str, Any]], parallel_results_reducer]
    
    # Observability: request correlation
    request_id: str  # Unique request ID for tracing and correlation


class AIAgent:
    """
    LangGraph-based AI Agent with RAG implementing the workflow:
    Prompt → RAG → Decision → Tool → Observation → Memory → Response

    Graph structure: RAG → Agent → Tool → Agent → User
    """

    def __init__(
        self,
        openai_api_key: str,
        weather_tool: WeatherTool,
        geocode_tool: GeocodeTool,
        ip_tool: IPGeolocationTool,
        fx_tool: FXRatesTool,
        crypto_tool: CryptoPriceTool,
        file_tool: FileCreationTool,
        history_tool: HistorySearchTool,
        rag_subgraph: Optional[Any] = None,  # NEW: RAG subgraph
        mcp_client: Optional[Any] = None,  # NEW: MCP client for DeepWiki tools
        alphavantage_mcp_client: Optional[Any] = None  # NEW: MCP client for AlphaVantage
    ):
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            openai_api_key=openai_api_key
        )

        # Store tools
        self.tools = {
            "weather": weather_tool,
            "geocode": geocode_tool,
            "ip_geolocation": ip_tool,
            "fx_rates": fx_tool,
            "crypto_price": crypto_tool,
            "create_file": file_tool,
            "search_history": history_tool
        }

        # Store RAG subgraph
        self.rag_subgraph = rag_subgraph
        
        # Store MCP clients
        self.mcp_client = mcp_client
        self.alphavantage_mcp_client = alphavantage_mcp_client

        # Build LangGraph workflow
        self.workflow = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow graph with RAG integration.

        Nodes:
        - rag_pipeline: RAG subgraph (if configured) - runs FIRST
        - agent_decide: LLM reasoning and decision-making (can loop multiple times)
        - tool_*: Individual tool execution nodes
        - agent_finalize: Final response generation

        Flow: rag_pipeline → agent_decide → tool → agent_decide (loop) → ... → agent_finalize
        """
        workflow = StateGraph(AgentState)

        # Add RAG pipeline node if configured
        if self.rag_subgraph is not None:
            workflow.add_node("rag_pipeline", self.rag_subgraph)
            logger.info("RAG pipeline integrated into agent graph")

        # Add MCP tools fetching nodes (before agent decision)
        workflow.add_node("fetch_alphavantage_tools", self._fetch_alphavantage_tools_node)
        workflow.add_node("fetch_deepwiki_tools", self._fetch_deepwiki_tools_node)

        # Add nodes
        workflow.add_node("agent_decide", self._agent_decide_node)
        workflow.add_node("agent_finalize", self._agent_finalize_node)
        
        # Add MCP tool execution node
        workflow.add_node("mcp_tool_execution", self._mcp_tool_execution_node)
        
        # Add parallel tool execution node
        workflow.add_node("parallel_tool_execution", self._parallel_tool_execution_node)

        # Add tool nodes
        for tool_name in self.tools.keys():
            workflow.add_node(f"tool_{tool_name}", self._create_tool_node(tool_name))

        # Set entry point - RAG pipeline if configured, otherwise fetch_alphavantage_tools
        if self.rag_subgraph is not None:
            workflow.set_entry_point("rag_pipeline")
            # RAG pipeline → fetch_alphavantage_tools → fetch_deepwiki_tools → agent_decide
            workflow.add_edge("rag_pipeline", "fetch_alphavantage_tools")
        else:
            workflow.set_entry_point("fetch_alphavantage_tools")
        
        # AlphaVantage tools fetched first (currency data), then DeepWiki
        workflow.add_edge("fetch_alphavantage_tools", "fetch_deepwiki_tools")
        workflow.add_edge("fetch_deepwiki_tools", "agent_decide")

        # Add conditional edges from agent_decide
        workflow.add_conditional_edges(
            "agent_decide",
            self._route_decision,
            {
                "final_answer": "agent_finalize",
                "mcp_tool_execution": "mcp_tool_execution",
                "parallel_tool_execution": "parallel_tool_execution",
                **{f"tool_{name}": f"tool_{name}" for name in self.tools.keys()}
            }
        )

        # Add edges from tools back to agent_decide (for multi-step reasoning)
        for tool_name in self.tools.keys():
            workflow.add_edge(f"tool_{tool_name}", "agent_decide")
        
        # Add edge from MCP tool execution back to agent_decide
        workflow.add_edge("mcp_tool_execution", "agent_decide")
        
        # Add edge from parallel tool execution back to agent_decide
        workflow.add_edge("parallel_tool_execution", "agent_decide")

        # Add edge from finalize to end
        workflow.add_edge("agent_finalize", END)

        # Compile the workflow
        return workflow.compile()
    
    async def _fetch_alphavantage_tools_node(self, state: AgentState) -> AgentState:
        """
        Fetch available tools from AlphaVantage MCP server before agent decision.
        
        This node:
        1. Connects to AlphaVantage MCP server
        2. Fetches all available currency/financial tools
        3. Stores them in state for agent to use
        4. Runs FIRST before any other tool decisions
        """
        with record_node_duration("fetch_alphavantage_tools"):
            logger.info("Fetching tools from AlphaVantage MCP server")
        
        # Initialize debug logs if not exists
        if "debug_logs" not in state:
            state["debug_logs"] = []
        
        state["debug_logs"].append("[MCP] Starting AlphaVantage MCP server connection...")
        
        alphavantage_tools = []
        
        if self.alphavantage_mcp_client is None:
            logger.warning("No AlphaVantage MCP client configured, skipping AlphaVantage tools fetch")
            state["debug_logs"].append("[MCP] ⚠️ No AlphaVantage MCP client configured")
            state["alphavantage_tools"] = []
            return state
        
        try:
            # Ensure connection to AlphaVantage MCP server
            if not hasattr(self.alphavantage_mcp_client, 'connected') or not self.alphavantage_mcp_client.connected:
                import os
                api_key = os.getenv('ALPHAVANTAGE_API_KEY', '')
                logger.info("Connecting to AlphaVantage MCP server: https://mcp.alphavantage.co/mcp?apikey=***")
                state["debug_logs"].append("[MCP] Connecting to AlphaVantage server (https://mcp.alphavantage.co/mcp)...")
                await self.alphavantage_mcp_client.connect(f"https://mcp.alphavantage.co/mcp?apikey={api_key}")
                state["debug_logs"].append("[MCP] ✓ Connected to AlphaVantage MCP server")
            
            # List all available tools from AlphaVantage
            state["debug_logs"].append("[MCP] Fetching available tools from AlphaVantage...")
            alphavantage_tools = await self.alphavantage_mcp_client.list_tools()
            logger.info(f"Successfully fetched {len(alphavantage_tools)} tools from AlphaVantage MCP server")
            
            # Log tool names for debugging
            tool_names = [tool.get("name", "unknown") for tool in alphavantage_tools]
            logger.info(f"Available AlphaVantage tools: {tool_names}")
            state["debug_logs"].append(f"[MCP] ✓ Fetched {len(alphavantage_tools)} tools from AlphaVantage: {', '.join(tool_names)}")
            
        except ConnectionError as e:
            logger.error(f"Failed to connect to AlphaVantage MCP server: {e}")
            state["debug_logs"].append(f"[MCP] ✗ Connection failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching AlphaVantage tools: {e}")
            state["debug_logs"].append(f"[MCP] ✗ Error fetching tools: {str(e)}")
        
            # Store tools in state for agent to use
            state["alphavantage_tools"] = alphavantage_tools
            
            return state
    
    async def _fetch_deepwiki_tools_node(self, state: AgentState) -> AgentState:
        """
        Fetch available tools from DeepWiki MCP server before agent decision.
        
        This node:
        1. Connects to DeepWiki MCP server
        2. Fetches all available tools
        3. Stores them in state for agent to use
        4. The agent will then select relevant tools based on user prompt
        """
        with record_node_duration("fetch_deepwiki_tools"):
            logger.info("Fetching tools from DeepWiki MCP server")
        
        # Initialize debug logs if not exists
        if "debug_logs" not in state:
            state["debug_logs"] = []
        
        state["debug_logs"].append("[MCP] Starting DeepWiki MCP server connection...")
        
        deepwiki_tools = []
        
        if self.mcp_client is None:
            logger.warning("No MCP client configured, skipping DeepWiki tools fetch")
            state["debug_logs"].append("[MCP] ⚠️ No DeepWiki MCP client configured")
            state["deepwiki_tools"] = []
            return state
        
        try:
            # Ensure connection to DeepWiki MCP server
            if not hasattr(self.mcp_client, 'connected') or not self.mcp_client.connected:
                logger.info("Connecting to DeepWiki MCP server: https://mcp.deepwiki.com/mcp")
                state["debug_logs"].append("[MCP] Connecting to DeepWiki server (https://mcp.deepwiki.com/mcp)...")
                await self.mcp_client.connect("https://mcp.deepwiki.com/mcp")
                state["debug_logs"].append("[MCP] ✓ Connected to DeepWiki MCP server")
            
            # List all available tools from DeepWiki
            state["debug_logs"].append("[MCP] Fetching available tools from DeepWiki...")
            deepwiki_tools = await self.mcp_client.list_tools()
            logger.info(f"Successfully fetched {len(deepwiki_tools)} tools from DeepWiki MCP server")
            
            # Log tool names for debugging
            tool_names = [tool.get("name", "unknown") for tool in deepwiki_tools]
            logger.info(f"Available DeepWiki tools: {tool_names}")
            state["debug_logs"].append(f"[MCP] ✓ Fetched {len(deepwiki_tools)} tools from DeepWiki: {', '.join(tool_names)}")
            state["debug_logs"].append(f"[MCP] ✓ Fetched {len(deepwiki_tools)} tools from DeepWiki: {', '.join(tool_names)}")
            
        except ConnectionError as e:
            logger.error(f"Failed to connect to DeepWiki MCP server: {e}")
            state["debug_logs"].append(f"[MCP] ✗ Connection failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching DeepWiki tools: {e}")
            state["debug_logs"].append(f"[MCP] ✗ Error fetching tools: {str(e)}")
        
            # Store tools in state for agent to use
            state["deepwiki_tools"] = deepwiki_tools
            
            return state
    
    async def _agent_decide_node(self, state: AgentState) -> AgentState:
        """
        Agent decision node: Analyzes user request and decides next action.
        """
        with record_node_duration("agent_decide"):
            logger.info(f"Agent decision node executing [request_id={get_request_id()}]")
        
        # Build context for LLM
        system_prompt = self._build_system_prompt(state["memory"])
        
        # Get last user message
        last_user_msg = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break
        
        # Build conversation context for decision
        recent_history = state["memory"].chat_history[-5:] if state["memory"].chat_history else []
        history_context = "\n".join([f"{msg.role}: {msg.content[:100]}" for msg in recent_history]) if recent_history else "No previous conversation"
        
        # Build list of already called tools with their arguments to prevent duplicates
        tools_called_info = [
            f"{tc.tool_name}({tc.arguments})"
            for tc in state["tools_called"]
        ]

        # NEW: Build RAG context section if available
        rag_section = ""
        rag_context = state.get("rag_context", {})
        if rag_context and rag_context.get("has_knowledge", False):
            context_text = rag_context.get("context_text", "")
            citations = rag_context.get("citations", [])
            rewritten_query = rag_context.get("rewritten_query", "")

            rag_section = f"""
═══════════════════════════════════════════════════════════════
🔍 PRIORITY: KNOWLEDGE BASE SEARCH RESULTS
═══════════════════════════════════════════════════════════════

The system has searched the user's uploaded documents and found relevant information.

Query optimized for search: "{rewritten_query}"
Documents retrieved: {len(citations)} relevant passages

Retrieved Context:
{context_text}

Available Citations: {", ".join(citations)}

═══════════════════════════════════════════════════════════════
🎯 CRITICAL RULES FOR USING THIS KNOWLEDGE:
═══════════════════════════════════════════════════════════════

1. PREFER RETRIEVED KNOWLEDGE OVER TOOLS
   - If the retrieved context answers the user's question, use "final_answer" immediately
   - ONLY call external tools if the knowledge base doesn't have sufficient information

2. MANDATORY CITATION
   - When using information from retrieved context, you MUST include citations
   - Use format: [RAG-1], [RAG-2], etc.
   - NEVER claim document content without citing

3. INSUFFICIENT KNOWLEDGE HANDLING
   - If retrieved context doesn't answer the question, explicitly state:
     "The uploaded documents don't contain information about X."
   - THEN consider calling appropriate tools

4. NO HALLUCINATION
   - ONLY use information explicitly present in the context above
   - NEVER invent or extrapolate document content

═══════════════════════════════════════════════════════════════
"""

        # Build available tools list dynamically
        available_tools_list = [
            "- weather: Get weather forecast (params: city OR lat/lon) - ONLY provides current + 2 day future forecast, NO historical data",
            "- geocode: Convert address to coordinates or reverse (params: address OR lat/lon)",
            "- ip_geolocation: Get location from IP address (params: ip_address)",
            "- fx_rates: Get currency exchange rates (params: base, target, optional date)",
            "- crypto_price: Get CRYPTOCURRENCY prices ONLY like BTC, ETH (params: symbol, fiat) - DO NOT use for STOCKS",
            "- create_file: Save text to a file (params: user_id, filename, content)",
            "- search_history: Search past conversations (params: query)"
        ]
        
        # Add AlphaVantage MCP tools if available
        alphavantage_tools = state.get("alphavantage_tools", [])
        if alphavantage_tools:
            available_tools_list.append("\n📊 AlphaVantage Financial & Market Data Tools (stocks, commodities, forex, economic indicators):")
            
            # Prioritize commodities and stock quote tools (they're most commonly used)
            priority_tools = ["WTI", "BRENT", "NATURAL_GAS", "COPPER", "ALUMINUM", "WHEAT", "CORN", "COFFEE", "COTTON", 
                            "GLOBAL_QUOTE", "CURRENCY_EXCHANGE_RATE", "DIGITAL_CURRENCY_DAILY", "CPI", "REAL_GDP"]
            
            # Add priority tools first
            for tool in alphavantage_tools:
                tool_name = tool.get("name", "")
                if tool_name in priority_tools:
                    tool_desc = tool.get("description", "No description")
                    input_schema = tool.get("inputSchema", {})
                    properties = input_schema.get("properties", {})
                    params_desc = ", ".join(properties.keys()) if properties else "see schema"
                    available_tools_list.append(f"  - {tool_name}: {tool_desc} (params: {params_desc})")
            
            # Add remaining tools (up to 30 total)
            remaining_count = 0
            for tool in alphavantage_tools:
                tool_name = tool.get("name", "")
                if tool_name not in priority_tools and remaining_count < 15:
                    tool_desc = tool.get("description", "No description")
                    input_schema = tool.get("inputSchema", {})
                    properties = input_schema.get("properties", {})
                    params_desc = ", ".join(properties.keys()) if properties else "see schema"
                    available_tools_list.append(f"  - {tool_name}: {tool_desc} (params: {params_desc})")
                    remaining_count += 1
        
        available_tools_str = "\n".join(available_tools_list)
        
        # Create decision prompt - MUST return ONLY JSON, nothing else
        decision_prompt = f"""
You must analyze the user's request and respond with ONLY a valid JSON object, nothing else.

{rag_section}

Recent conversation context:
{history_context}

Available tools:
{available_tools_str}

User's original request: {last_user_msg}

Tools already called with their arguments: {tools_called_info}

CRITICAL RULES:
1. YOU MUST CALL THE APPROPRIATE TOOL if one exists for the user's request - DO NOT say "data not available" if a tool exists
2. For COMMODITIES (oil, gas, copper, aluminum, wheat, corn, coffee, cotton): use AlphaVantage tools like WTI, BRENT, NATURAL_GAS, COPPER, etc.
3. For STOCK prices (AAPL, MSFT, GOOGL, TSLA): use AlphaVantage GLOBAL_QUOTE tool, NOT crypto_price
4. For CRYPTOCURRENCY prices (BTC, ETH, DOGE): use crypto_price tool
5. NEVER call the same tool with the same arguments twice
6. If a tool was called and couldn't provide the data, do NOT retry - move to final_answer
7. If the user requested multiple DIFFERENT tasks, execute them ONE AT A TIME
8. Only use "final_answer" when ALL requested tasks are complete OR no suitable tool exists

Respond with ONLY this JSON structure (no other text, no markdown):
{{
  "action": "call_tool",
  "tool_name": "TOOL_NAME_HERE",
  "arguments": {{...}},
  "reasoning": "brief explanation"
}}

For PARALLEL execution (when tools don't depend on each other's results):
{{
  "action": "call_tools_parallel",
  "tools": [
    {{"tool_name": "TOOL1", "arguments": {{...}}}},
    {{"tool_name": "TOOL2", "arguments": {{...}}}}
  ],
  "reasoning": "these tools are independent and can run concurrently"
}}

Examples:
- Weather: {{"action": "call_tool", "tool_name": "weather", "arguments": {{"city": "Budapest"}}, "reasoning": "get weather forecast"}}
- Commodities: {{"action": "call_tool", "tool_name": "WTI", "arguments": {{}}, "reasoning": "get WTI crude oil price"}}
- Stock quote: {{"action": "call_tool", "tool_name": "GLOBAL_QUOTE", "arguments": {{"symbol": "AAPL"}}, "reasoning": "get Apple stock price"}}
- Parallel stocks: {{"action": "call_tools_parallel", "tools": [{{"tool_name": "GLOBAL_QUOTE", "arguments": {{"symbol": "AAPL"}}}}, {{"tool_name": "GLOBAL_QUOTE", "arguments": {{"symbol": "TSLA"}}}}], "reasoning": "fetch multiple stock prices simultaneously"}}
- Parallel commodities: {{"action": "call_tools_parallel", "tools": [{{"tool_name": "WTI", "arguments": {{}}}}, {{"tool_name": "BRENT", "arguments": {{}}}}, {{"tool_name": "NATURAL_GAS", "arguments": {{}}}}], "reasoning": "fetch multiple commodity prices simultaneously"}}
- Create file: {{"action": "call_tool", "tool_name": "create_file", "arguments": {{"filename": "summary.txt", "content": "..."}}, "reasoning": "save summary"}}
- Final answer: {{"action": "final_answer", "reasoning": "all tasks completed"}}

IMPORTANT: The "action" field must be "call_tool", "call_tools_parallel", or "final_answer" - NEVER use a tool name as the action!
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=decision_prompt)
        ]
        
        # Use instrumented LLM call for metrics collection
        try:
            response = await instrumented_llm_call(
                llm=self.llm,
                messages=messages,
                model="gpt-4-turbo-preview"
            )
        except Exception as e:
            record_error(error_type="llm_error", node="agent_decide")
            raise
        
        # Parse decision
        try:
            # Try to extract JSON from the response
            content = response.content.strip()
            
            # If response contains markdown code blocks, extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            decision = json.loads(content)
            logger.info(f"Agent decision: {decision}")
            
            state["next_action"] = decision.get("action", "final_answer")
            
            # Store decision for tool execution
            if decision.get("action") == "call_tool":
                state["tool_decision"] = decision
                # Increment iteration count when calling a tool
                state["iteration_count"] = state.get("iteration_count", 0) + 1
            
            # Handle parallel tool execution
            elif decision.get("action") == "call_tools_parallel":
                state["parallel_tasks"] = decision.get("tools", [])
                logger.info(f"Parallel execution requested for {len(state['parallel_tasks'])} tools")
            
        except (json.JSONDecodeError, IndexError, AttributeError) as e:
            logger.error(f"Failed to parse agent decision: {e}, defaulting to final_answer")
            logger.error(f"Response content: {response.content[:200]}")
            state["next_action"] = "final_answer"
        
        return state
    
    def _detect_parallel_tools(self, state: AgentState) -> List[Dict[str, Any]]:
        """Detect if multiple independent tools can be executed in parallel."""
        parallel_tasks = state.get("parallel_tasks", [])
        if not parallel_tasks:
            return []
        
        # All MCP tools are independent (they don't have data dependencies)
        # Local tools may have dependencies, so we only parallelize MCP tools
        alphavantage_tools = {t.get("name") for t in state.get("alphavantage_tools", [])}
        deepwiki_tools = {t.get("name") for t in state.get("deepwiki_tools", [])}
        
        independent_tasks = []
        for task in parallel_tasks:
            tool_name = task.get("tool_name", "")
            # Strip prefix if present
            if ":" in tool_name:
                tool_name = tool_name.split(":", 1)[1]
                task["tool_name"] = tool_name
            
            # Only MCP tools can be parallelized
            if tool_name in alphavantage_tools or tool_name in deepwiki_tools:
                independent_tasks.append(task)
        
        logger.info(f"Detected {len(independent_tasks)} independent tools for parallel execution")
        return independent_tasks
    
    async def _execute_parallel_tools(self, state: AgentState) -> AgentState:
        """Execute multiple MCP tools in parallel using asyncio.gather."""
        tasks = self._detect_parallel_tools(state)
        
        if not tasks:
            logger.warning("No parallel tasks to execute")
            return state
        
        logger.info(f"Executing {len(tasks)} tools in parallel")
        
        # Create coroutines for each tool
        async def execute_single_tool(task: Dict[str, Any]) -> Dict[str, Any]:
            tool_name = task.get("tool_name")
            arguments = task.get("arguments", {})
            
            try:
                logger.info(f"Parallel execution: {tool_name} with args {arguments}")
                result = await self.mcp_client.call_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                    session_id=state.get("alphavantage_session_id")
                )
                
                return {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": result.get("content") if result else None,
                    "success": True
                }
            except Exception as e:
                logger.error(f"Parallel tool {tool_name} failed: {e}")
                return {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "error": str(e),
                    "success": False
                }
        
        # Execute all tools in parallel
        results = await asyncio.gather(*[execute_single_tool(task) for task in tasks])
        
        # Update state with results
        state["parallel_results"] = results
        
        # Record successful tool calls
        for result in results:
            if result.get("success"):
                tool_call = ToolCall(
                    tool_name=result["tool_name"],
                    arguments=result["arguments"],
                    result=result.get("result"),
                    error=None
                )
                state["tools_called"].append(tool_call)
                
                # Add to messages
                tool_msg = f"Tool {result['tool_name']} executed: {str(result.get('result', ''))[:200]}"
                state["messages"].append(AIMessage(content=tool_msg))
        
        # Increment iteration count
        state["iteration_count"] = state.get("iteration_count", 0) + len(results)
        
        # Clear parallel tasks after execution
        state["parallel_tasks"] = []
        
        logger.info(f"Parallel execution completed: {len(results)} tools executed")
        
        return state
    
    def _route_decision(self, state: AgentState) -> str:
        """Route to next node based on agent decision."""
        # Check iteration limit to prevent infinite loops
        if state.get("iteration_count", 0) >= MAX_ITERATIONS:
            logger.warning(f"Max iterations ({MAX_ITERATIONS}) reached, forcing finalize")
            return "final_answer"
        
        action = state.get("next_action", "final_answer")
        
        # Check for parallel tool execution
        if action == "call_tools_parallel" and state.get("parallel_tasks"):
            independent_tasks = self._detect_parallel_tools(state)
            if len(independent_tasks) >= 2:
                return "parallel_tool_execution"
            # Fall back to sequential if only one task
            elif len(independent_tasks) == 1:
                state["tool_decision"] = independent_tasks[0]
                state["parallel_tasks"] = []
                action = "call_tool"
        
        if action == "call_tool" and "tool_decision" in state:
            tool_name = state["tool_decision"].get("tool_name")
            
            # Strip MCP server prefixes (AlphaVantage:, DeepWiki:) from tool names
            # LLM sometimes adds these prefixes incorrectly
            if ":" in tool_name:
                original_tool_name = tool_name
                tool_name = tool_name.split(":", 1)[1]  # Take everything after the first colon
                logger.info(f"Stripped prefix from tool name: {original_tool_name} -> {tool_name}")
                # Update the tool_decision with the corrected name
                state["tool_decision"]["tool_name"] = tool_name
            
            # Check if it's a local tool
            if tool_name in self.tools:
                return f"tool_{tool_name}"
            
            # Check if it's an AlphaVantage MCP tool
            alphavantage_tools = state.get("alphavantage_tools", [])
            alphavantage_tool_names = [t.get("name") for t in alphavantage_tools]
            if tool_name in alphavantage_tool_names:
                return "mcp_tool_execution"
            
            # Check if it's a DeepWiki MCP tool
            deepwiki_tools = state.get("deepwiki_tools", [])
            deepwiki_tool_names = [t.get("name") for t in deepwiki_tools]
            if tool_name in deepwiki_tool_names:
                return "mcp_tool_execution"
            
            # Tool not found - log error and continue to finalize
            logger.error(f"Unknown tool requested: {tool_name}")
        
        return "final_answer"
    
    def _create_tool_node(self, tool_name: str):
        """Create a tool execution node."""
        async def tool_node(state: AgentState) -> AgentState:
            logger.info(f"Executing tool: {tool_name}")
            
            tool = self.tools[tool_name]
            decision = state.get("tool_decision", {})
            arguments = decision.get("arguments", {})
            
            # Add user_id for file creation tool
            if tool_name == "create_file":
                arguments["user_id"] = state["current_user_id"]
            
            # Execute tool
            try:
                result = await tool.execute(**arguments)
                
                # Record tool call
                tool_call = ToolCall(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result.get("data") if result.get("success") else None,
                    error=result.get("error") if not result.get("success") else None
                )
                state["tools_called"].append(tool_call)
                
                # Add system message
                system_msg = result.get("system_message", f"Tool {tool_name} executed")
                state["messages"].append(SystemMessage(content=system_msg))
                
                logger.info(f"Tool {tool_name} completed: {result.get('success', False)}")
                
            except Exception as e:
                logger.error(f"Tool {tool_name} error: {e}")
                error_msg = f"Error executing {tool_name}: {str(e)}"
                state["messages"].append(SystemMessage(content=error_msg))
                state["tools_called"].append(ToolCall(
                    tool_name=tool_name,
                    arguments=arguments,
                    error=str(e)
                ))
            
            return state
        
        return tool_node
    
    async def _mcp_tool_execution_node(self, state: AgentState) -> AgentState:
        """Execute MCP tool (AlphaVantage or DeepWiki) dynamically."""
        decision = state.get("tool_decision", {})
        tool_name = decision.get("tool_name")
        arguments = decision.get("arguments", {})
        
        logger.info(f"Executing MCP tool: {tool_name} with args: {arguments}")
        
        try:
            # Determine which MCP client to use
            alphavantage_tools = state.get("alphavantage_tools", [])
            deepwiki_tools = state.get("deepwiki_tools", [])
            
            alphavantage_tool_names = [t.get("name") for t in alphavantage_tools]
            deepwiki_tool_names = [t.get("name") for t in deepwiki_tools]
            
            mcp_client = None
            server_name = ""
            
            if tool_name in alphavantage_tool_names:
                mcp_client = self.alphavantage_mcp_client
                server_name = "AlphaVantage"
            elif tool_name in deepwiki_tool_names:
                mcp_client = self.mcp_client
                server_name = "DeepWiki"
            else:
                raise ValueError(f"Tool {tool_name} not found in any MCP server")
            
            # Call the MCP tool
            result = await mcp_client.call_tool(tool_name, arguments)
            
            # Record tool call
            tool_call = ToolCall(
                tool_name=f"{server_name}:{tool_name}",
                arguments=arguments,
                result=result,
                error=None
            )
            state["tools_called"].append(tool_call)
            
            # Format result as system message
            result_str = json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
            system_msg = f"[{server_name} MCP Tool: {tool_name}]\nResult:\n{result_str}"
            state["messages"].append(SystemMessage(content=system_msg))
            
            logger.info(f"MCP tool {tool_name} completed successfully")
            
        except Exception as e:
            logger.error(f"MCP tool {tool_name} error: {e}")
            error_msg = f"Error executing MCP tool {tool_name}: {str(e)}"
            state["messages"].append(SystemMessage(content=error_msg))
            state["tools_called"].append(ToolCall(
                tool_name=tool_name,
                arguments=arguments,
                error=str(e)
            ))
        
        return state
    
    async def _parallel_tool_execution_node(self, state: AgentState) -> AgentState:
        """
        Execute multiple independent MCP tools in parallel for faster response.
        Uses asyncio.gather to run tools concurrently.
        """
        parallel_tasks = state.get("parallel_tasks", [])
        
        if not parallel_tasks:
            logger.warning("Parallel execution node called but no parallel_tasks in state")
            return state
        
        logger.info(f"Parallel execution node: processing {len(parallel_tasks)} tasks")
        
        # Execute tools in parallel using helper function
        results = await execute_parallel_mcp_tools(
            tasks=parallel_tasks,
            alphavantage_tools=state.get("alphavantage_tools", []),
            deepwiki_tools=state.get("deepwiki_tools", []),
            mcp_client=self.alphavantage_mcp_client,
            session_id=state.get("alphavantage_session_id", "")
        )
        
        # Update state with results
        state["parallel_results"] = results
        
        # Record successful tool calls
        for result in results:
            if result.get("success"):
                tool_call = ToolCall(
                    tool_name=result["tool_name"],
                    arguments=result["arguments"],
                    result=result.get("result"),
                    error=None
                )
                state["tools_called"].append(tool_call)
                
                # Add to messages
                tool_msg = f"Tool {result['tool_name']} executed: {str(result.get('result', ''))[:200]}"
                state["messages"].append(AIMessage(content=tool_msg))
        
        # Increment iteration count by number of tools executed
        state["iteration_count"] = state.get("iteration_count", 0) + len(results)
        
        # Clear parallel tasks after execution
        state["parallel_tasks"] = []
        
        logger.info(f"Parallel execution completed: {len([r for r in results if r.get('success')])} successful, {len([r for r in results if not r.get('success')])} failed")
        
        return state
    
    async def _agent_finalize_node(self, state: AgentState) -> AgentState:
        """
        Agent finalize node: Generate final natural language response.
        """
        with record_node_duration("agent_finalize"):
            logger.info(f"Agent finalize node executing [request_id={get_request_id()}]")

        # Build final prompt with memory and tool results
        system_prompt = self._build_system_prompt(state["memory"])

        # Get conversation context
        conversation_history = "\n".join([
            f"{msg.__class__.__name__}: {msg.content}"
            for msg in state["messages"][-10:]  # Last 10 messages
        ])

        # NEW: Build RAG citation reminder if applicable
        rag_reminder = ""
        rag_context = state.get("rag_context", {})
        if rag_context and rag_context.get("has_knowledge", False):
            citations = rag_context.get("citations", [])
            rag_reminder = f"""
IMPORTANT - Retrieved Document Context:
If your response uses information from the retrieved documents, you MUST include citations.
Available citations: {", ".join(citations)}

Example: "According to the documentation [RAG-1], the authentication flow uses JWT tokens [RAG-2]."

If you're not using retrieved knowledge, don't include citations.
"""

        final_prompt = f"""
Generate a natural language response to the user based on the conversation history and any tool results.

{rag_reminder}

Conversation:
{conversation_history}

Important:
- Respond in {state['memory'].preferences.get('language', 'hu')} language
- Be helpful and conversational
- Use information from tool results if available
- Cite sources when using retrieved document knowledge
- Keep the response concise but complete
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=final_prompt)
        ]
        
        # Use instrumented LLM call for metrics collection
        try:
            response = await instrumented_llm_call(
                llm=self.llm,
                messages=messages,
                model="gpt-4-turbo-preview"
            )
        except Exception as e:
            record_error(error_type="llm_error", node="agent_finalize")
            raise
        
        # Add assistant message
        state["messages"].append(AIMessage(content=response.content))
        
        logger.info("Agent finalized response")
        
        return state
    
    def _build_system_prompt(self, memory: Memory) -> str:
        """Build system prompt with memory context."""
        preferences = memory.preferences
        workflow = memory.workflow_state
        
        # Build user info section
        user_info = []
        if preferences.get('name'):
            user_info.append(f"- Name: {preferences['name']}")
        user_info.append(f"- Language: {preferences.get('language', 'hu')}")
        user_info.append(f"- Default city: {preferences.get('default_city', 'Budapest')}")
        
        # Add any other preferences
        for key, value in preferences.items():
            if key not in ['name', 'language', 'default_city']:
                user_info.append(f"- {key.replace('_', ' ').title()}: {value}")
        
        prompt = f"""You are a helpful AI assistant with access to various tools.

User preferences:
{chr(10).join(user_info)}

"""
        
        # Add recent conversation history for context
        if memory.chat_history:
            recent_history = memory.chat_history[-10:]  # Last 10 messages
            history_text = "\n".join([
                f"{msg.role}: {msg.content[:150]}"  # Truncate long messages
                for msg in recent_history
            ])
            prompt += f"\nRecent conversation history:\n{history_text}\n\n"
        
        if workflow.flow:
            prompt += f"\nCurrent workflow: {workflow.flow} (step {workflow.step}/{workflow.total_steps})\n"
        
        # Add personalization instruction
        if preferences.get('name'):
            prompt += f"\nAddress the user by their name ({preferences['name']}) when appropriate.\n"
        
        return prompt
    
    async def run(
        self,
        user_message: str,
        memory: Memory,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Run the agent workflow with RAG support.

        Args:
            user_message: User's input message
            memory: Memory context (preferences, history, workflow state)
            user_id: Current user ID

        Returns:
            Dict containing final_answer, tools_called, updated memory, and RAG context
        """
        logger.info(f"Agent run started for user {user_id} [request_id={get_request_id()}]")

        # Check for special commands that skip RAG
        skip_rag = user_message.lower() == "reset context"

        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_message)],
            "memory": memory,
            "tools_called": [],
            "current_user_id": user_id,
            "next_action": "",
            "iteration_count": 0,
            # NEW: RAG state fields
            "skip_rag": skip_rag,
            "rag_context": {},
            "rag_metrics": {},
            "debug_logs": []  # MCP debug logs
        }
        
        # Add request correlation
        initial_state = add_request_id_to_state(initial_state)
        
        # Run workflow with increased recursion limit for multi-step workflows
        final_state = await self.workflow.ainvoke(
            initial_state,
            {"recursion_limit": 50}
        )
        
        # Extract final answer
        final_answer = ""
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage):
                final_answer = msg.content
                break
        
        logger.info("Agent run completed")

        return {
            "final_answer": final_answer,
            "tools_called": final_state["tools_called"],
            "messages": final_state["messages"],
            "memory": final_state["memory"],
            # NEW: RAG context and metrics
            "rag_context": final_state.get("rag_context", {}),
            "rag_metrics": final_state.get("rag_metrics", {})
        }
