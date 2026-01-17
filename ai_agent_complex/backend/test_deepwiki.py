"""
Test script for DeepWiki MCP integration.
Demonstrates how to use DeepWiki tools in the agent.
"""
import asyncio
import logging
from infrastructure.tool_clients import MCPClient, DeepWikiMCPClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_deepwiki_connection():
    """Test basic DeepWiki MCP connection."""
    print("\n=== Testing DeepWiki MCP Connection ===\n")
    
    # Initialize clients
    mcp_client = MCPClient()
    deepwiki_client = DeepWikiMCPClient(mcp_client=mcp_client)
    
    try:
        # Test 1: List available tools
        print("Test 1: Listing available tools from DeepWiki MCP server...")
        await mcp_client.connect("https://mcp.deepwiki.com/mcp")
        tools = await mcp_client.list_tools()
        
        print(f"✓ Connected successfully!")
        print(f"✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.get('name')}: {tool.get('description', 'No description')}")
        
        print("\n" + "="*50 + "\n")
        
        # Test 2: Ask a question
        print("Test 2: Asking a question about LangChain...")
        result = await deepwiki_client.ask_question(
            question="What is LangChain?",
            repo_url="https://github.com/langchain-ai/langchain"
        )
        
        if result.get("success"):
            print(f"✓ Question answered successfully!")
            print(f"  Answer: {result.get('answer', 'No answer')[:200]}...")
        else:
            print(f"✗ Error: {result.get('error')}")
        
        print("\n" + "="*50 + "\n")
        
        # Test 3: Read wiki structure
        print("Test 3: Reading wiki structure for LangChain...")
        result = await deepwiki_client.read_wiki_structure(
            repo_url="https://github.com/langchain-ai/langchain"
        )
        
        if result.get("success"):
            print(f"✓ Wiki structure retrieved!")
            print(f"  Structure: {str(result.get('structure', {}))[:200]}...")
        else:
            print(f"✗ Error: {result.get('error')}")
        
        print("\n" + "="*50 + "\n")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
    finally:
        await mcp_client.disconnect()


async def test_deepwiki_tools():
    """Test DeepWiki tools in isolation."""
    print("\n=== Testing DeepWiki Tools ===\n")
    
    from services.tools import DeepWikiTool
    
    # Initialize
    mcp_client = MCPClient()
    deepwiki_client = DeepWikiMCPClient(mcp_client=mcp_client)
    deepwiki_tool = DeepWikiTool(deepwiki_client)
    
    try:
        # Test ask_question action
        print("Testing DeepWiki Tool with ask_question action...")
        result = await deepwiki_tool.execute(
            action="ask_question",
            question="How do I install LangChain?",
            repo_url="https://github.com/langchain-ai/langchain"
        )
        
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('system_message', 'No message')}")
        if result.get('data'):
            print(f"Answer: {str(result['data'].get('answer', 'No answer'))[:200]}...")
        
        print("\n" + "="*50 + "\n")
        
    except Exception as e:
        print(f"✗ Tool test failed: {e}")
        logger.error(f"Tool test error: {e}", exc_info=True)
    finally:
        await mcp_client.disconnect()


async def test_langchain_tools():
    """Test LangChain-compatible DeepWiki tools."""
    print("\n=== Testing LangChain Tools ===\n")
    
    import services.tools_langchain as tools_langchain
    from infrastructure.tool_clients import DeepWikiMCPClient, MCPClient
    
    # Initialize
    mcp_client = MCPClient()
    deepwiki_client = DeepWikiMCPClient(mcp_client=mcp_client)
    
    # Initialize tools
    tools_langchain.initialize_tools(
        weather_client=None,  # Not needed for this test
        geocode_client=None,
        ip_client=None,
        fx_client=None,
        crypto_client=None,
        conversation_repo=None,
        deepwiki_client=deepwiki_client
    )
    
    try:
        # Test deepwiki_ask_question
        print("Testing deepwiki_ask_question LangChain tool...")
        result = await tools_langchain.deepwiki_ask_question(
            question="What are the main features of LangChain?",
            repo_url="https://github.com/langchain-ai/langchain"
        )
        
        print(f"Result: {result[:200]}...")
        print("\n" + "="*50 + "\n")
        
    except Exception as e:
        print(f"✗ LangChain tool test failed: {e}")
        logger.error(f"LangChain tool test error: {e}", exc_info=True)
    finally:
        await mcp_client.disconnect()


async def main():
    """Run all tests."""
    print("\n" + "="*70)
    print(" DeepWiki MCP Integration Tests")
    print("="*70)
    
    # Run tests
    await test_deepwiki_connection()
    await test_deepwiki_tools()
    await test_langchain_tools()
    
    print("\n" + "="*70)
    print(" All Tests Completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
