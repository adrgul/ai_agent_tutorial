"""
MCP Integration Nodes for Advanced Agent.

This module provides nodes for:
- Fetching available tools from MCP servers
- Executing single MCP tools
- Executing multiple MCP tools in parallel

WHY These Nodes?
- Integrates MCP server capabilities into Advanced Agent
- Follows same pattern as Main Agent but with Advanced Agent's state
- Enables dynamic tool discovery and execution
- Supports both sequential and parallel MCP tool execution
"""

import logging
from typing import Dict, Any, List
import asyncio

from langchain_core.messages import SystemMessage

from .state import AdvancedAgentState
from services.parallel_execution import execute_parallel_mcp_tools

logger = logging.getLogger(__name__)


class MCPToolFetcherNode:
    """
    Node for fetching available tools from MCP servers.

    This node:
    1. Connects to configured MCP servers
    2. Fetches list of available tools
    3. Stores tools in state for router/planner to use
    """

    def __init__(self, mcp_client, server_name: str, server_url: str):
        """
        Initialize MCP tool fetcher.

        Args:
            mcp_client: MCP client instance
            server_name: Name of the server (e.g., "AlphaVantage", "DeepWiki")
            server_url: URL of the MCP server
        """
        self.mcp_client = mcp_client
        self.server_name = server_name
        self.server_url = server_url

    async def __call__(self, state: AdvancedAgentState) -> Dict[str, Any]:
        """
        Fetch tools from MCP server (caches in state to avoid re-fetching).

        Args:
            state: Current agent state

        Returns:
            State updates with fetched tools
        """
        # Store tools in state with server-specific key
        tool_key = f"{self.server_name.lower()}_tools"
        
        # Check if tools already fetched (avoid re-fetching on every workflow iteration)
        existing_tools = state.get(tool_key)
        if existing_tools:
            logger.info(f"[MCP] Using cached {len(existing_tools)} tools from {self.server_name} (skip fetch)")
            return {}  # No state updates needed, tools already present
        
        logger.info(f"[MCP] Fetching tools from {self.server_name} server: {self.server_url}")

        # Initialize debug logs if not present
        debug_logs = state.get("debug_logs", [])

        try:
            # Connect to MCP server
            await self.mcp_client.connect(self.server_url)
            debug_logs.append(f"[MCP] ✓ Connected to {self.server_name}")

            # List available tools
            tools = await self.mcp_client.list_tools()
            debug_logs.append(f"[MCP] ✓ Fetched {len(tools)} tools from {self.server_name}")

            logger.info(f"[MCP] Successfully fetched {len(tools)} tools from {self.server_name}")

            return {
                tool_key: tools,
                "debug_logs": debug_logs
            }

        except Exception as e:
            error_msg = f"[MCP] ✗ Failed to fetch tools from {self.server_name}: {e}"
            logger.error(error_msg)
            debug_logs.append(error_msg)

            # Return empty tools list on error
            return {
                f"{self.server_name.lower()}_tools": [],
                "debug_logs": debug_logs
            }


class MCPToolExecutionNode:
    """
    Node for executing a single MCP tool.

    This node:
    1. Identifies which MCP server has the requested tool
    2. Calls the tool with provided arguments
    3. Returns result as a message
    """

    def __init__(self, alphavantage_client, deepwiki_client):
        """
        Initialize MCP tool execution node.

        Args:
            alphavantage_client: AlphaVantage MCP client
            deepwiki_client: DeepWiki MCP client
        """
        self.alphavantage_client = alphavantage_client
        self.deepwiki_client = deepwiki_client

    async def __call__(self, state: AdvancedAgentState) -> Dict[str, Any]:
        """
        Execute MCP tool based on routing decision.

        Args:
            state: Current agent state

        Returns:
            State updates with tool result
        """
        routing_decision = state.get("routing_decision", {})
        tool_name = routing_decision.get("tool_name")
        tool_arguments = routing_decision.get("tool_arguments", {})

        if not tool_name:
            logger.warning("[MCP] No tool_name in routing_decision")
            return {
                "messages": [SystemMessage(content="Error: No tool specified for execution")],
                "debug_logs": state.get("debug_logs", []) + ["[MCP] ✗ No tool specified"]
            }

        logger.info(f"[MCP] Executing tool: {tool_name} with args: {tool_arguments}")

        debug_logs = state.get("debug_logs", [])
        tools_called = state.get("tools_called", [])

        try:
            # Determine which MCP client to use
            alphavantage_tools = state.get("alphavantage_tools", [])
            deepwiki_tools = state.get("deepwiki_tools", [])

            # Check if tool is from AlphaVantage
            if any(t.get("name") == tool_name for t in alphavantage_tools):
                result = await self.alphavantage_client.call_tool(tool_name, tool_arguments)
                server_name = "AlphaVantage"
            # Check if tool is from DeepWiki
            elif any(t.get("name") == tool_name for t in deepwiki_tools):
                result = await self.deepwiki_client.call_tool(tool_name, tool_arguments)
                server_name = "DeepWiki"
            else:
                error_msg = f"Tool '{tool_name}' not found in any MCP server"
                logger.error(f"[MCP] {error_msg}")
                return {
                    "messages": [SystemMessage(content=f"Error: {error_msg}")],
                    "debug_logs": debug_logs + [f"[MCP] ✗ {error_msg}"]
                }

            # Extract content from result
            content = result.get("content", result) if isinstance(result, dict) else result

            # Record tool call
            tools_called.append({
                "tool_name": f"{server_name}:{tool_name}",
                "arguments": tool_arguments,
                "success": True
            })

            debug_logs.append(f"[MCP] ✓ Executed {server_name}:{tool_name}")

            logger.info(f"[MCP] Successfully executed {server_name}:{tool_name}")

            return {
                "messages": [SystemMessage(content=f"Tool result: {content}")],
                "tools_called": tools_called,
                "debug_logs": debug_logs
            }

        except Exception as e:
            error_msg = f"MCP tool execution failed: {e}"
            logger.error(f"[MCP] {error_msg}")

            tools_called.append({
                "tool_name": tool_name,
                "arguments": tool_arguments,
                "success": False,
                "error": str(e)
            })

            return {
                "messages": [SystemMessage(content=f"Error: {error_msg}")],
                "tools_called": tools_called,
                "debug_logs": debug_logs + [f"[MCP] ✗ {error_msg}"]
            }


class MCPParallelExecutionNode:
    """
    Node for executing multiple MCP tools in parallel.

    This node:
    1. Takes list of parallel tasks from state
    2. Executes them concurrently using asyncio.gather()
    3. Aggregates results
    """

    def __init__(self, alphavantage_client, deepwiki_client):
        """
        Initialize parallel MCP execution node.

        Args:
            alphavantage_client: AlphaVantage MCP client
            deepwiki_client: DeepWiki MCP client
        """
        self.alphavantage_client = alphavantage_client
        self.deepwiki_client = deepwiki_client

    async def __call__(self, state: AdvancedAgentState) -> Dict[str, Any]:
        """
        Execute multiple MCP tools in parallel.

        Args:
            state: Current agent state

        Returns:
            State updates with parallel results
        """
        parallel_tasks = state.get("parallel_tasks", [])

        if not parallel_tasks:
            logger.warning("[MCP] No parallel_tasks in state")
            return {
                "debug_logs": state.get("debug_logs", []) + ["[MCP] ✗ No parallel tasks"]
            }

        logger.info(f"[MCP] Executing {len(parallel_tasks)} tools in parallel")

        alphavantage_tools = state.get("alphavantage_tools", [])
        deepwiki_tools = state.get("deepwiki_tools", [])
        session_id = state.get("session_id", "default")

        try:
            # Use helper function from parallel_execution.py
            results = await execute_parallel_mcp_tools(
                tasks=parallel_tasks,
                alphavantage_tools=alphavantage_tools,
                deepwiki_tools=deepwiki_tools,
                mcp_client=self.alphavantage_client,  # Use AlphaVantage client as primary
                session_id=session_id
            )

            # Record successful tool calls
            tools_called = state.get("tools_called", [])
            for result in results:
                if result.get("success"):
                    tools_called.append({
                        "tool_name": f"MCP:{result.get('tool_name')}",
                        "arguments": result.get("arguments", {}),
                        "success": True
                    })

            debug_logs = state.get("debug_logs", [])
            debug_logs.append(f"[MCP] ✓ Parallel execution: {len(results)} tools completed")

            logger.info(f"[MCP] Parallel execution completed: {len(results)} results")

            return {
                "parallel_results": results,
                "tools_called": tools_called,
                "debug_logs": debug_logs
            }

        except Exception as e:
            error_msg = f"Parallel MCP execution failed: {e}"
            logger.error(f"[MCP] {error_msg}")

            return {
                "debug_logs": state.get("debug_logs", []) + [f"[MCP] ✗ {error_msg}"]
            }
