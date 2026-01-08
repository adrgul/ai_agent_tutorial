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
from pydantic import BaseModel

from domain.models import ChatRequest, ChatResponse, ProfileUpdateRequest
from domain.interfaces import IUserRepository, IConversationRepository
from infrastructure.repositories import FileUserRepository, FileConversationRepository
from infrastructure.tool_clients import (
    OpenMeteoWeatherClient, NominatimGeocodeClient, IPAPIGeolocationClient,
    ExchangeRateHostClient, CoinGeckoCryptoClient, MCPWeatherClient, MCPClient
)
from services.tools import (
    WeatherTool, GeocodeTool, IPGeolocationTool, FXRatesTool,
    CryptoPriceTool, FileCreationTool, HistorySearchTool
)
from services.agent import AIAgent
from services.chat_service import ChatService

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

    # Initialize agent (with RAG if available)
    agent = AIAgent(
        openai_api_key=openai_api_key,
        weather_tool=weather_tool,
        geocode_tool=geocode_tool,
        ip_tool=ip_tool,
        fx_tool=fx_tool,
        crypto_tool=crypto_tool,
        file_tool=file_tool,
        history_tool=history_tool,
        rag_subgraph=rag_subgraph,  # NEW: Pass RAG subgraph
        mcp_client=mcp_client,  # NEW: Pass MCP client for DeepWiki tools
        alphavantage_mcp_client=alphavantage_mcp_client  # NEW: Pass MCP client for AlphaVantage
    )
    
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
