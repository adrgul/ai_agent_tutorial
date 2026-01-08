"""
Service layer - LangGraph agent with ToolNode implementation.
Uses LangGraph's built-in ToolNode for PARALLEL tool execution with custom reducer.
"""
from typing import List, Dict, Any, Optional, Sequence, Annotated
from typing_extensions import TypedDict
import logging
import asyncio
from datetime import datetime
from operator import add

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from domain.models import Memory, ToolCall
import services.tools_langchain as tools_module

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10


# Weather data is now retrieved through the MCP protocol.
# Tool: get_weather
# Server: mcp://weather.openai.com
async def weather_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for weather retrieval via MCP protocol.
    
    This node demonstrates how MCP tool invocation can be integrated
    into a LangGraph workflow. It extracts city/coordinates from state,
    calls the MCP weather client, and returns updated state.
    
    Note: In practice, weather tools are handled via ToolNode with LangChain tools.
    This is a demonstration of explicit MCP integration within LangGraph nodes.
    """
    from domain.interfaces import IMCPWeatherClient
    
    logger.info("Weather node executing (MCP-based)")
    
    # Extract parameters from state
    city = state.get("city")
    lat = state.get("lat")
    lon = state.get("lon")
    
    # Get MCP weather client from state (injected during initialization)
    mcp_weather_client: Optional[IMCPWeatherClient] = state.get("mcp_weather_client")
    
    if not mcp_weather_client:
        logger.error("MCP Weather Tool client not available in state")
        return {
            **state,
            "weather": {"error": "MCP Weather Tool service not configured"}
        }
    
    try:
        # Call MCP weather tool through the client
        result = await mcp_weather_client.get_forecast(city=city, lat=lat, lon=lon)
        
        logger.info(f"MCP Weather Tool node completed successfully")
        return {
            **state,
            "weather": result
        }
        
    except ConnectionError as e:
        # MCP server not reachable
        logger.error(f"MCP Weather Tool server not reachable: {e}")
        return {
            **state,
            "weather": {"error": f"MCP server not reachable: {str(e)}"}
        }
    except NotImplementedError as e:
        # Tool not available
        logger.error(f"MCP Weather Tool not available: {e}")
        return {
            **state,
            "weather": {"error": f"Weather tool not available: {str(e)}"}
        }
    except ValueError as e:
        # Invalid arguments
        logger.error(f"MCP Weather Tool invalid arguments: {e}")
        return {
            **state,
            "weather": {"error": f"Invalid arguments: {str(e)}"}
        }
    except Exception as e:
        # General error
        logger.error(f"MCP Weather Tool unexpected error: {e}")
        return {
            **state,
            "weather": {"error": f"Unexpected error: {str(e)}"}
        }


class AgentState(TypedDict, total=False):
    """State object for LangGraph agent with RAG support and parallel tool execution."""
    messages: Sequence[BaseMessage]
    memory: Memory
    tools_called: Annotated[List[ToolCall], add]  # Reducer: concatenate results
    current_user_id: str
    iteration_count: int
    rag_context: Dict[str, Any]
    rag_metrics: Dict[str, Any]
    skip_rag: bool
    # Parallel execution tracking
    tool_errors: Annotated[List[Dict[str, Any]], add]  # Reducer: collect errors
    tool_metrics: Dict[str, Any]  # Metrics from tool execution
    # DeepWiki MCP tools
    deepwiki_tools: List[Dict[str, Any]]  # Tools fetched from DeepWiki MCP server


class AIAgentWithToolNode:
    """
    LangGraph agent using built-in ToolNode with PARALLEL execution and custom reducer.
    
    Features:
    - Parallel tool execution when multiple tools are requested
    - Custom reducer for aggregating tool results
    - Separate error tracking and metrics collection
    
    Flow: RAG → Agent (with tools bound) → ToolNode (parallel) → Reducer → Agent → Finalize
    """

    def __init__(
        self,
        openai_api_key: str,
        tools: list,
        rag_subgraph: Optional[Any] = None,
        mcp_client: Optional[Any] = None
    ):
        # Create LLM with tools bound
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            openai_api_key=openai_api_key
        )
        
        self.tools = tools
        self.llm_with_tools = self.llm.bind_tools(tools)
        
        # Create ToolNode with all tools (supports parallel execution)
        self.tool_node = ToolNode(tools)
        
        self.rag_subgraph = rag_subgraph
        self.mcp_client = mcp_client  # MCP client for fetching DeepWiki tools
        self.workflow = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph workflow using ToolNode with parallel execution.
        
        Structure:
        - rag_pipeline (optional) → agent → tools (parallel) → tool_reducer → agent → finalize
        """
        workflow = StateGraph(AgentState)

        # Add RAG pipeline if configured
        if self.rag_subgraph is not None:
            workflow.add_node("rag_pipeline", self.rag_subgraph)
            logger.info("RAG pipeline integrated")

        # Add DeepWiki tools fetching node (before agent decision)
        workflow.add_node("fetch_deepwiki_tools", self._fetch_deepwiki_tools_node)
        
        # Add agent nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self.tool_node)  # ToolNode (executes tools in parallel)
        workflow.add_node("tool_reducer", self._tool_reducer_node)  # Reducer for aggregating results
        workflow.add_node("finalize", self._finalize_node)

        # Set entry point and connect nodes
        if self.rag_subgraph is not None:
            workflow.set_entry_point("rag_pipeline")
            workflow.add_edge("rag_pipeline", "fetch_deepwiki_tools")
        else:
            workflow.set_entry_point("fetch_deepwiki_tools")
        
        # DeepWiki tools are fetched before agent decision
        workflow.add_edge("fetch_deepwiki_tools", "agent")

        # Conditional routing from agent
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",      # Has tool calls → execute tools in parallel
                "finalize": "finalize"  # No tool calls → generate final answer
            }
        )

        # After tools execute, go to reducer, then back to agent
        workflow.add_edge("tools", "tool_reducer")
        workflow.add_edge("tool_reducer", "agent")
        
        # Finalize goes to end
        workflow.add_edge("finalize", END)

        return workflow.compile()
    
    async def _fetch_deepwiki_tools_node(self, state: AgentState) -> AgentState:
        """
        Fetch available tools from DeepWiki MCP server before agent decision.
        
        This node:
        1. Connects to DeepWiki MCP server
        2. Fetches all available tools
        3. Stores them in state for agent to use
        4. The agent will then select relevant tools based on user prompt
        """
        logger.info("Fetching tools from DeepWiki MCP server")
        
        deepwiki_tools = []
        
        if self.mcp_client is None:
            logger.warning("No MCP client configured, skipping DeepWiki tools fetch")
            state["deepwiki_tools"] = []
            return state
        
        try:
            # Ensure connection to DeepWiki MCP server
            if not hasattr(self.mcp_client, 'connected') or not self.mcp_client.connected:
                logger.info("Connecting to DeepWiki MCP server: https://mcp.deepwiki.com/mcp")
                await self.mcp_client.connect("https://mcp.deepwiki.com/mcp")
            
            # List all available tools from DeepWiki
            deepwiki_tools = await self.mcp_client.list_tools()
            logger.info(f"Successfully fetched {len(deepwiki_tools)} tools from DeepWiki MCP server")
            
            # Log tool names for debugging
            tool_names = [tool.get("name", "unknown") for tool in deepwiki_tools]
            logger.info(f"Available DeepWiki tools: {tool_names}")
            
        except ConnectionError as e:
            logger.error(f"Failed to connect to DeepWiki MCP server: {e}")
        except Exception as e:
            logger.error(f"Error fetching DeepWiki tools: {e}")
        
        # Store tools in state for agent to use
        state["deepwiki_tools"] = deepwiki_tools
        
        return state
    
    async def _tool_reducer_node(self, state: AgentState) -> AgentState:
        """
        Reducer node: Aggregates results from parallel tool executions.
        
        Responsibilities:
        1. Tool results aggregation (already in messages via ToolNode)
        2. Error tracking and separation
        3. Metrics collection (execution time, success rate, etc.)
        4. State merge logic
        """
        logger.info("Tool reducer node executing")
        
        # Initialize metrics if not present
        if "tool_metrics" not in state:
            state["tool_metrics"] = {}
        
        # Initialize error list if not present
        if "tool_errors" not in state:
            state["tool_errors"] = []
        
        # Find all ToolMessages added in this iteration
        tool_messages = [msg for msg in state["messages"] if isinstance(msg, ToolMessage)]
        recent_tool_messages = tool_messages[-len(state.get("tools_called", [])):] if state.get("tools_called") else []
        
        # Metrics collection
        total_tools = len(recent_tool_messages)
        successful_tools = 0
        failed_tools = 0
        
        # Process each tool result
        for i, tool_msg in enumerate(recent_tool_messages):
            # Check if tool execution was successful
            if "error" in tool_msg.content.lower() or "failed" in tool_msg.content.lower():
                failed_tools += 1
                
                # Error tracking: collect error details
                error_info = {
                    "tool_call_id": tool_msg.tool_call_id if hasattr(tool_msg, "tool_call_id") else None,
                    "error_message": tool_msg.content,
                    "timestamp": datetime.now().isoformat(),
                    "iteration": state.get("iteration_count", 0)
                }
                
                # Update tools_called with error info
                if i < len(state.get("tools_called", [])):
                    state["tools_called"][-(total_tools - i)].error = tool_msg.content
                
                # Add to error list (reducer will concatenate)
                state["tool_errors"] = state.get("tool_errors", []) + [error_info]
                
                logger.warning(f"Tool execution failed: {error_info}")
            else:
                successful_tools += 1
                
                # Update tools_called with result
                if i < len(state.get("tools_called", [])):
                    state["tools_called"][-(total_tools - i)].result = tool_msg.content
        
        # Update metrics
        state["tool_metrics"] = {
            **state.get("tool_metrics", {}),
            "total_executions": state["tool_metrics"].get("total_executions", 0) + total_tools,
            "successful_executions": state["tool_metrics"].get("successful_executions", 0) + successful_tools,
            "failed_executions": state["tool_metrics"].get("failed_executions", 0) + failed_tools,
            "last_execution_count": total_tools,
            "last_success_rate": (successful_tools / total_tools * 100) if total_tools > 0 else 0,
            "parallel_execution": total_tools > 1,
            "last_update": datetime.now().isoformat()
        }
        
        logger.info(f"Tool execution metrics: {total_tools} total, {successful_tools} successful, {failed_tools} failed")
        
        return state
        
        # Finalize goes to end
        workflow.add_edge("finalize", END)

        return workflow.compile()
    
    async def _agent_node(self, state: AgentState) -> AgentState:
        """
        Agent node: LLM decides whether to use tools or answer directly.
        Uses tool calling instead of manual JSON parsing.
        """
        logger.info("Agent node executing")
        
        # Check iteration limit
        if state.get("iteration_count", 0) >= MAX_ITERATIONS:
            logger.warning(f"Max iterations reached")
            # Force finalize by not calling tools
            state["iteration_count"] = state.get("iteration_count", 0) + 1
            return state
        
        # Build system prompt
        system_prompt = self._build_system_prompt(state["memory"])
        
        # Add RAG context if available
        rag_context = state.get("rag_context", {})
        if rag_context and rag_context.get("has_knowledge", False):
            system_prompt += f"\n\nKNOWLEDGE BASE:\n{rag_context.get('context_text', '')}"
        
        # Create messages for LLM (system + conversation history)
        messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
        
        # Call LLM with tools bound
        response = await self.llm_with_tools.ainvoke(messages)
        
        # Add AI response to state
        state["messages"] = list(state["messages"]) + [response]
        
        # Track tool calls if any
        if response.tool_calls:
            state["iteration_count"] = state.get("iteration_count", 0) + 1
            logger.info(f"LLM requested {len(response.tool_calls)} tool calls - will execute in PARALLEL")
            
            # Record tool calls in our custom format (reducer will aggregate)
            new_tool_calls = []
            for tool_call in response.tool_calls:
                tc = ToolCall(
                    tool_name=tool_call["name"],
                    arguments=tool_call["args"],
                    result=None,  # Will be filled by reducer after parallel execution
                    error=None
                )
                new_tool_calls.append(tc)
            
            # Use reducer pattern: append to existing list
            state["tools_called"] = state.get("tools_called", []) + new_tool_calls
        
        return state
    
    def _should_continue(self, state: AgentState) -> str:
        """
        Routing function: decide if we should call tools or finalize.
        """
        last_message = state["messages"][-1]
        
        # Check iteration limit
        if state.get("iteration_count", 0) >= MAX_ITERATIONS:
            return "finalize"
        
        # If last message has tool calls, execute them
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        # Otherwise, finalize
        return "finalize"
    
    async def _finalize_node(self, state: AgentState) -> AgentState:
        """
        Generate final natural language response.
        """
        logger.info("Finalize node executing")
        
        # If the last message is already an AI message without tool calls, we're done
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and not hasattr(last_message, "tool_calls"):
            return state
        
        # Otherwise, ask LLM to generate final response
        system_prompt = "You are a helpful AI assistant. Provide a final answer to the user based on the conversation and tool results."
        messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
        
        response = await self.llm.ainvoke(messages)
        state["messages"] = list(state["messages"]) + [response]
        
        return state
    
    def _build_system_prompt(self, memory: Memory) -> str:
        """Build system prompt with memory context."""
        lang = memory.preferences.get("language", "en")
        default_city = memory.preferences.get("default_city", "")
        
        base_prompt = "You are a helpful AI assistant with access to various tools."
        
        if lang == "hu":
            base_prompt = "Hasznos AI asszisztens vagy, különböző eszközökkel."
        
        if default_city:
            base_prompt += f" User's default city: {default_city}."
        
        # Add conversation context
        if memory.chat_history:
            recent = memory.chat_history[-5:]
            context = "\n".join([f"{m.role}: {m.content[:100]}" for m in recent])
            base_prompt += f"\n\nRecent conversation:\n{context}"
        
        return base_prompt
    
    async def run(self, state: AgentState) -> Dict[str, Any]:
        """Run the agent workflow with parallel tool execution and metrics."""
        result = await self.workflow.ainvoke(state)
        
        # Extract final answer
        final_message = None
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and not hasattr(msg, "tool_calls"):
                final_message = msg.content
                break
        
        return {
            "final_answer": final_message or "I couldn't generate a response.",
            "tools_called": result.get("tools_called", []),
            "messages": result.get("messages", []),
            "tool_metrics": result.get("tool_metrics", {}),  # Metrics from reducer
            "tool_errors": result.get("tool_errors", [])     # Errors from reducer
        }
