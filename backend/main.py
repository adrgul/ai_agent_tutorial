"""
API layer - FastAPI application with endpoints and RAG integration.
Following SOLID:
- Single Responsibility - Controllers are thin, delegate to services.
- Dependency Inversion - Controllers depend on service abstractions.
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

# Observability imports
from observability.metrics import init_metrics, get_metrics_content
from observability.config import get_global_config

from domain.models import ChatRequest, ChatResponse, ProfileUpdateRequest
from domain.interfaces import IUserRepository, IConversationRepository
from infrastructure.repositories import FileUserRepository, FileConversationRepository
from infrastructure.tool_clients import (
    OpenMeteoWeatherClient, NominatimGeocodeClient, IPAPIGeolocationClient,
    ExchangeRateHostClient, CoinGeckoCryptoClient, MCPWeatherClient, MCPClient,
    DeepWikiMCPClient
)
from services.tools import (
    WeatherTool, GeocodeTool, IPGeolocationTool, FXRatesTool,
    CryptoPriceTool, FileCreationTool, HistorySearchTool, DeepWikiTool
)
import services.tools_langchain as tools_langchain
from services.agent import AIAgent
from services.chat_service import ChatService

# NEW: Advanced Agent imports
from advanced_agents.advanced_graph import AdvancedAgentGraph
from advanced_agents.state import create_initial_state
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

# NEW: RAG imports
from rag.config import RAGConfig
from rag.embeddings import OpenAIEmbeddingService
from rag.vector_store import ChromaVectorStore
from rag.chunking import OverlappingChunker
from rag.retrieval_service import RetrievalService
from rag.ingestion_service import IngestionService
from rag.rag_graph import create_rag_subgraph

# NEW: Teaching Memory Lab imports
from teaching_memory_lab.api import router as teaching_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ADAPTER CLASS - Makes AdvancedAgentGraph compatible with ChatService
# ============================================================================

class AdvancedAgentAdapter:
    """
    Adapter that wraps AdvancedAgentGraph to provide the interface expected by ChatService.

    ChatService expects:
        async def run(user_message: str, memory: Memory, user_id: str) -> Dict

    AdvancedAgentGraph provides:
        async def run(state: AdvancedAgentState) -> AdvancedAgentState
    """

    def __init__(self, advanced_graph: AdvancedAgentGraph):
        self.graph = advanced_graph

    async def run(self, user_message: str, memory: Any, user_id: str) -> Dict[str, Any]:
        """
        Adapt ChatService's run() interface to AdvancedAgentGraph's run() interface.

        Args:
            user_message: User's message
            memory: Memory context (from ChatService)
            user_id: User identifier

        Returns:
            Dict with keys: final_answer, tools_called, messages, debug_logs
        """
        # Create initial state for Advanced Agent
        initial_state = create_initial_state(
            user_id=user_id,
            message=user_message,
            session_id=user_id  # Use user_id as session_id
        )

        # Add memory context as system message if available
        if memory and memory.preferences:
            memory_context = "User Context:"
            if memory.preferences:
                memory_context += f"\nPreferences: {memory.preferences}"

            # Prepend system message with memory context
            initial_state["messages"].insert(0, SystemMessage(content=memory_context))

        # Run the Advanced Agent graph
        final_state = await self.graph.run(initial_state)

        # Extract and return results in the format ChatService expects
        return {
            "final_answer": final_state.get("final_answer", "I apologize, but I couldn't generate a response."),
            "tools_called": final_state.get("tools_called", []),
            "messages": final_state.get("messages", []),
            "debug_logs": final_state.get("debug_logs", []),
            "rag_context": {},  # Advanced Agent doesn't use RAG yet
            "rag_metrics": {}   # Advanced Agent doesn't use RAG yet
        }

# Global service instances
chat_service: ChatService = None
user_repo: IUserRepository = None
ingestion_service: IngestionService = None  # NEW
vector_store: ChromaVectorStore = None  # NEW


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - initialize services on startup."""
    global chat_service, user_repo, ingestion_service, vector_store

    logger.info("Initializing application...")

    # Initialize observability
    obs_config = get_global_config()
    init_metrics(
        environment=obs_config.environment,
        version=obs_config.version
    )
    logger.info(f"Observability initialized [environment={obs_config.environment}, metrics_enabled={obs_config.enable_metrics}]")

    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set!")
        raise RuntimeError("OPENAI_API_KEY must be set")

    # Initialize repositories
    user_repo = FileUserRepository(data_dir="data/users")
    conversation_repo = FileConversationRepository(data_dir="data/sessions")

    # Initialize tool clients
    geocode_client = NominatimGeocodeClient()
    
    # Use direct OpenMeteo API client (MCP server not configured)
    weather_client = OpenMeteoWeatherClient(geocode_client)
    logger.info("Initialized OpenMeteo Weather client")
    
    # Initialize MCP clients for external tool servers
    mcp_client = MCPClient()
    logger.info("Initialized MCP client for DeepWiki")
    
    alphavantage_mcp_client = MCPClient()
    logger.info("Initialized MCP client for AlphaVantage")
    
    # Initialize DeepWiki MCP client
    deepwiki_client = DeepWikiMCPClient(mcp_client=mcp_client)
    logger.info("Initialized DeepWiki MCP client")
    
    ip_client = IPAPIGeolocationClient()
    fx_client = ExchangeRateHostClient()
    crypto_client = CoinGeckoCryptoClient()

    # Initialize tools
    weather_tool = WeatherTool(weather_client)
    geocode_tool = GeocodeTool(geocode_client)
    ip_tool = IPGeolocationTool(ip_client)
    fx_tool = FXRatesTool(fx_client)
    crypto_tool = CryptoPriceTool(crypto_client)
    file_tool = FileCreationTool(data_dir="data/files")
    history_tool = HistorySearchTool(conversation_repo)
    deepwiki_tool = DeepWikiTool(deepwiki_client)
    logger.info("Initialized DeepWiki tool")
    
    # Initialize LangChain tools for ToolNode
    tools_langchain.initialize_tools(
        weather_client=weather_client,
        geocode_client=geocode_client,
        ip_client=ip_client,
        fx_client=fx_client,
        crypto_client=crypto_client,
        conversation_repo=conversation_repo,
        file_data_dir="data/files",
        deepwiki_client=deepwiki_client
    )
    logger.info("Initialized LangChain tools with DeepWiki support")

    # NEW: Initialize RAG services
    logger.info("Initializing RAG services...")
    rag_subgraph = None
    try:
        # Load RAG configuration
        rag_config = RAGConfig.from_env()

        # Initialize embedding service
        embedding_service = OpenAIEmbeddingService(rag_config.embedding)

        # Initialize vector store
        vector_store = ChromaVectorStore(rag_config.vector_store)

        # Initialize chunker
        chunker = OverlappingChunker(rag_config.chunking)

        # Initialize retrieval service
        retrieval_service = RetrievalService(
            vector_store=vector_store,
            embedding_service=embedding_service,
            config=rag_config.retrieval
        )

        # Initialize ingestion service
        ingestion_service = IngestionService(
            chunker=chunker,
            embedding_service=embedding_service,
            vector_store=vector_store,
            config=rag_config.ingestion
        )

        # Create LLM for RAG nodes (query rewriting)
        from langchain_openai import ChatOpenAI
        rag_llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.3,  # Lower temp for query rewriting
            openai_api_key=openai_api_key
        )

        # Create RAG subgraph
        rag_subgraph = create_rag_subgraph(
            retrieval_service=retrieval_service,
            rag_config=rag_config,
            llm=rag_llm
        )

        logger.info("RAG services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG services: {e}")
        logger.warning("Continuing without RAG support")

    # Initialize LLM for Advanced Agent
    agent_llm = ChatOpenAI(
        model="gpt-4-turbo-preview",
        temperature=0.7,
        openai_api_key=openai_api_key
    )

    # Build tools dictionary for Advanced Agent
    tools_dict = {
        "weather": weather_tool,
        "geocode": geocode_tool,
        "ip_geolocation": ip_tool,
        "fx_rates": fx_tool,
        "crypto_price": crypto_tool,
        "create_file": file_tool,
        "search_history": history_tool
    }

    # Get AlphaVantage API key for MCP connection
    alphavantage_api_key = os.getenv("ALPHAVANTAGE_API_KEY", "demo")
    alphavantage_url = f"https://mcp.alphavantage.co/mcp?apikey={alphavantage_api_key}"
    deepwiki_url = "https://mcp.deepwiki.com/mcp"

    # Initialize Advanced Agent (with RAG if available)
    advanced_graph = AdvancedAgentGraph(
        llm=agent_llm,
        tools=tools_dict,
        enable_checkpointing=False,
        alphavantage_mcp_client=alphavantage_mcp_client,
        deepwiki_mcp_client=mcp_client,  # DeepWiki uses mcp_client
        alphavantage_url=alphavantage_url,
        deepwiki_url=deepwiki_url
    )

    # Wrap Advanced Agent with adapter for ChatService compatibility
    agent = AdvancedAgentAdapter(advanced_graph)

    logger.info("Advanced Agent initialized with MCP integration and adapter")
    
    # Initialize chat service
    chat_service = ChatService(
        user_repository=user_repo,
        conversation_repository=conversation_repo,
        agent=agent
    )
    
    logger.info("Application initialized successfully")
    
    yield
    
    logger.info("Application shutting down...")


# Create FastAPI app
app = FastAPI(
    title="AI Agent Demo",
    description="LangGraph-based AI Agent with tools and memory",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(teaching_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "AI Agent API is running"}


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format for scraping.
    Includes:
    - Agent request metrics (count, latency)
    - LLM usage metrics (tokens, cost)
    - Node execution metrics
    - Tool call metrics
    - Error metrics
    
    Example usage:
        curl http://localhost:8000/metrics
    """
    content, content_type = get_metrics_content()
    return Response(content=content, media_type=content_type)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process chat message.
    
    Handles:
    - Normal chat messages
    - Special 'reset context' command
    - Tool invocations via agent
    - Memory persistence
    """
    try:
        logger.info(f"Chat request from user {request.user_id}")
        response = await chat_service.process_message(request)
        return response
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get conversation history for a session."""
    try:
        history = await chat_service.get_session_history(session_id)
        return history
    except Exception as e:
        logger.error(f"Get session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profile/{user_id}")
async def get_profile(user_id: str):
    """Get user profile."""
    try:
        profile = await user_repo.get_profile(user_id)
        return profile.model_dump(mode='json')
    except Exception as e:
        logger.error(f"Get profile error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/profile/{user_id}")
async def update_profile(user_id: str, request: ProfileUpdateRequest):
    """Update user profile."""
    try:
        updates = request.model_dump(exclude_none=True)
        profile = await user_repo.update_profile(user_id, updates)
        return profile.model_dump(mode='json')
    except Exception as e:
        logger.error(f"Update profile error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history/search")
async def search_history(q: str):
    """Search across all conversation histories."""
    try:
        results = await chat_service.search_history(q)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Search history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RAG Endpoints
# ============================================================================

@app.post("/api/rag/upload")
async def upload_document(file: UploadFile = File(...), user_id: str = Form(...)):
    """
    Upload and ingest a document for RAG.

    Supports: .txt, .md files only
    """
    if ingestion_service is None:
        raise HTTPException(status_code=503, detail="RAG services not available")

    try:
        # Validate file type
        if not file.filename.endswith(('.txt', '.md')):
            raise HTTPException(
                status_code=400,
                detail="Only .txt and .md files are supported"
            )

        # Read file content
        content = await file.read()
        logger.info(f"Received file {file.filename}: {len(content)} bytes, content_type: {file.content_type}")
        
        if len(content) == 0:
            logger.error(f"Received empty file: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} is empty. Please ensure the file has content before uploading."
            )
        
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('latin-1')
            logger.warning(f"File {file.filename} decoded with latin-1")

        # Save to temporary file
        upload_dir = Path(f"data/rag/uploads/{user_id}")
        upload_dir.mkdir(parents=True, exist_ok=True)

        temp_file = upload_dir / file.filename
        temp_file.write_text(text, encoding='utf-8')

        # Ingest
        document = await ingestion_service.ingest_file(
            file_path=temp_file,
            user_id=user_id,
            filename=file.filename
        )

        logger.info(f"Document uploaded: {file.filename} ({document.chunk_count} chunks)")

        return {
            "success": True,
            "document_id": document.doc_id,
            "filename": document.filename,
            "chunk_count": document.chunk_count,
            "size_chars": document.size_chars
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/stats/{user_id}")
async def get_rag_stats(user_id: str):
    """Get RAG statistics for user."""
    if vector_store is None:
        raise HTTPException(status_code=503, detail="RAG services not available")

    try:
        stats = await vector_store.get_stats(user_id)

        return {
            "user_id": user_id,
            "document_count": stats.get("document_count", 0),
            "chunk_count": stats.get("chunk_count", 0),
            "collection_name": stats.get("collection_name", ""),
            "persist_directory": str(stats.get("persist_directory", ""))
        }
    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/documents/{user_id}")
async def list_documents(user_id: str):
    """List all documents for a user."""
    if vector_store is None:
        raise HTTPException(status_code=503, detail="RAG services not available")

    try:
        documents = await vector_store.list_documents(user_id)

        return {
            "user_id": user_id,
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        logger.error(f"List documents error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/rag/documents/{doc_id}")
async def delete_document(doc_id: str, user_id: str):
    """Delete a document and all its chunks."""
    if ingestion_service is None:
        raise HTTPException(status_code=503, detail="RAG services not available")

    try:
        deleted_count = await ingestion_service.delete_document(doc_id, user_id)

        logger.info(f"Document deleted: {doc_id} ({deleted_count} chunks)")

        return {
            "success": True,
            "doc_id": doc_id,
            "deleted_chunks": deleted_count
        }
    except Exception as e:
        logger.error(f"Delete document error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# ADVANCED AGENTS ENDPOINTS (NEW)
# ==============================================================================

@app.post("/api/advanced/parallel-demo")
async def run_parallel_demo(request: Dict[str, Any]):
    """
    Run the parallel execution demo.
    
    Educational endpoint demonstrating:
    - Parallel task execution (fan-out/fan-in)
    - Result aggregation
    - Performance comparison (parallel vs sequential)
    
    Request body:
    {
        "message": "What's the weather in London, USD to EUR rate, and Bitcoin price?" (optional)
    }
    
    Returns:
    {
        "final_answer": "...",
        "execution_time": 2.4,
        "aggregation": {...},
        "debug_logs": [...]
    }
    """
    try:
        from advanced_agents.examples import ParallelExecutionDemo
        from langchain_openai import ChatOpenAI
        
        # Get user message or use default
        user_message = request.get("message")
        
        # Initialize demo
        llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        demo = ParallelExecutionDemo(llm)
        
        # Run demo
        result = await demo.run_demo(user_message)
        
        # Extract state for response
        state = result["state"]
        
        return {
            "final_answer": result["final_answer"],
            "execution_time": result["execution_time"],
            "aggregation": {
                "total_tasks": result["aggregation"].total_tasks,
                "successful_tasks": result["aggregation"].successful_tasks,
                "failed_tasks": result["aggregation"].failed_tasks,
                "aggregated_data": result["aggregation"].aggregated_data
            },
            "debug_logs": state.get("debug_logs", []),
            "parallel_results": state.get("parallel_results", [])
        }
        
    except Exception as e:
        logger.error(f"Parallel demo error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/advanced/plan-execute")
async def plan_and_execute(request: ChatRequest):
    """
    Execute a request using Plan-and-Execute pattern.
    
    Educational endpoint demonstrating:
    - LLM-based plan generation
    - Step-by-step execution
    - Dependency resolution
    - Retry logic
    
    Request body:
    {
        "user_id": "user_123",
        "message": "Find my location and get weather there",
        "session_id": "session_456" (optional)
    }
    
    Returns:
    {
        "plan": {...},
        "execution_results": [...],
        "final_answer": "...",
        "debug_logs": [...]
    }
    """
    try:
        from advanced_agents import AdvancedAgentGraph, create_initial_state
        from langchain_openai import ChatOpenAI
        
        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Get available tools
        tools = {
            "weather": weather_tool,
            "geocode": geocode_tool,
            "ip_geolocation": ip_tool,
            "fx_rates": fx_tool,
            "crypto_price": crypto_tool,
            "create_file": file_tool,
            "search_history": history_tool
        }
        
        # Create advanced graph
        graph = AdvancedAgentGraph(llm=llm, tools=tools)
        
        # Create initial state
        state = create_initial_state(
            user_id=request.user_id,
            message=request.message,
            session_id=request.session_id
        )
        
        # Execute workflow
        final_state = await graph.run(state)
        
        # Extract results
        execution_plan = final_state.get("execution_plan")
        
        return {
            "plan": execution_plan.dict() if execution_plan else None,
            "execution_results": final_state.get("plan_results", []),
            "final_answer": final_state.get("final_answer", "No answer generated"),
            "debug_logs": final_state.get("debug_logs", []),
            "tools_called": final_state.get("tools_called", []),
            "iteration_count": final_state.get("iteration_count", 0)
        }
        
    except Exception as e:
        logger.error(f"Plan-execute error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/advanced/dynamic-route")
async def dynamic_route(request: ChatRequest):
    """
    Execute a request using dynamic routing.
    
    Educational endpoint demonstrating:
    - LLM-based routing decisions
    - Adaptive workflow paths
    - Parallel routing capabilities
    
    Request body:
    {
        "user_id": "user_123",
        "message": "What's the weather and exchange rate?",
        "session_id": "session_456" (optional)
    }
    
    Returns:
    {
        "routing_decisions": [...],
        "final_answer": "...",
        "debug_logs": [...]
    }
    """
    try:
        from advanced_agents import AdvancedAgentGraph, create_initial_state
        from langchain_openai import ChatOpenAI
        
        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.7,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Get available tools
        tools = {
            "weather": weather_tool,
            "geocode": geocode_tool,
            "ip_geolocation": ip_tool,
            "fx_rates": fx_tool,
            "crypto_price": crypto_tool,
            "create_file": file_tool,
            "search_history": history_tool
        }
        
        # Create advanced graph
        graph = AdvancedAgentGraph(llm=llm, tools=tools)
        
        # Create initial state
        state = create_initial_state(
            user_id=request.user_id,
            message=request.message,
            session_id=request.session_id
        )
        
        # Execute workflow
        final_state = await graph.run(state)
        
        return {
            "routing_decision": final_state.get("routing_decision"),
            "next_nodes": final_state.get("next_nodes", []),
            "final_answer": final_state.get("final_answer", "No answer generated"),
            "debug_logs": final_state.get("debug_logs", []),
            "tools_called": final_state.get("tools_called", [])
        }
        
    except Exception as e:
        logger.error(f"Dynamic route error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/advanced/capabilities")
async def get_advanced_capabilities():
    """
    Get information about available advanced orchestration capabilities.
    
    Returns:
    {
        "patterns": [...],
        "examples": [...]
    }
    """
    return {
        "patterns": [
            {
                "name": "Plan-and-Execute",
                "description": "LLM generates execution plan, then executes step-by-step",
                "use_cases": ["Multi-step workflows", "Dependent operations", "Complex tasks"],
                "endpoint": "/api/advanced/plan-execute"
            },
            {
                "name": "Parallel Execution",
                "description": "Run independent tasks concurrently to reduce latency",
                "use_cases": ["Multiple API calls", "Independent queries", "Data gathering"],
                "endpoint": "/api/advanced/parallel-demo"
            },
            {
                "name": "Dynamic Routing",
                "description": "LLM decides at runtime which nodes to execute",
                "use_cases": ["Adaptive workflows", "Complex decision trees", "Context-aware routing"],
                "endpoint": "/api/advanced/dynamic-route"
            }
        ],
        "examples": [
            {
                "name": "Parallel Weather + FX + Crypto",
                "message": "What's the weather in London, USD to EUR rate, and Bitcoin price?",
                "pattern": "parallel"
            },
            {
                "name": "Location-based Weather",
                "message": "Find my location and get weather there",
                "pattern": "plan-execute"
            },
            {
                "name": "Multi-city Weather",
                "message": "What's the weather in London, Paris, and Tokyo?",
                "pattern": "parallel"
            }
        ],
        "documentation": "/docs/ADVANCED_AGENTS.md"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
