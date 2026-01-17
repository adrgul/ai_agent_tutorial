"""
Parallel execution helper methods for the agent.
Separated for clarity and maintainability.
"""
import logging
import asyncio
from typing import Dict, List, Any

from domain.models import ToolCall

logger = logging.getLogger(__name__)


async def execute_parallel_mcp_tools(
    tasks: List[Dict[str, Any]],
    alphavantage_tools: List[Dict[str, Any]],
    deepwiki_tools: List[Dict[str, Any]],
    mcp_client,
    session_id: str
) -> List[Dict[str, Any]]:
    """
    Execute multiple MCP tools in parallel using asyncio.gather.
    
    Args:
        tasks: List of {tool_name, arguments} dicts
        alphavantage_tools: Available AlphaVantage tools
        deepwiki_tools: Available DeepWiki tools
        mcp_client: MCP client instance
        session_id: Session ID for MCP calls
        
    Returns:
        List of results: [{tool_name, arguments, result/error, success}]
    """
    # Filter for independent MCP tools only
    alphavantage_names = {t.get("name") for t in alphavantage_tools}
    deepwiki_names = {t.get("name") for t in deepwiki_tools}
    
    independent_tasks = []
    for task in tasks:
        tool_name = task.get("tool_name", "")
        # Strip prefix if present
        if ":" in tool_name:
            tool_name = tool_name.split(":", 1)[1]
            task["tool_name"] = tool_name
        
        # Only MCP tools can be parallelized
        if tool_name in alphavantage_names or tool_name in deepwiki_names:
            independent_tasks.append(task)
    
    if not independent_tasks:
        logger.warning("No independent MCP tools found for parallel execution")
        return []
    
    logger.info(f"Executing {len(independent_tasks)} MCP tools in parallel")
    
    # Create coroutine for each tool
    async def execute_single_tool(task: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = task.get("tool_name")
        arguments = task.get("arguments", {})
        
        try:
            logger.info(f"Parallel execution: {tool_name} with args {arguments}")
            result = await mcp_client.call_tool(
                name=tool_name,
                arguments=arguments
            )
            
            # MCP result can be a dict or a list
            content = None
            if isinstance(result, dict):
                content = result.get("content")
            elif isinstance(result, list):
                content = result
            else:
                content = result
            
            return {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": content,
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
    results = await asyncio.gather(*[execute_single_tool(task) for task in independent_tasks])
    
    logger.info(f"Parallel execution completed: {len(results)} tools executed")
    return results
