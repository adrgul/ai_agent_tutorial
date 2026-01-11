"""
FastAPI Application for RAG-based Document Storage and Chat

This application provides:
- Document storage with automatic chunking and embedding (via LangGraph)
- RAG-based chat with query rewriting and context retrieval (via LangGraph)

SETUP INSTRUCTIONS:
1. Install dependencies:
   pip install -r requirements.txt

2. Ensure Ollama is running:
   - Install from https://ollama.ai
   - Pull the model: ollama pull qwen2.5:14b-instruct
   - Pull embedding model (optional, for local embedding): ollama pull nomic-embed-text
   - Ollama should be running on http://localhost:11434

3. Ensure Qdrant is running:
   - Install from https://qdrant.tech/documentation/quick-start/
   - Or run with Docker: docker run -p 6333:6333 qdrant/qdrant
   - Qdrant should be accessible at http://localhost:6333

4. Run the application:
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

5. Access API docs:
   http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.models import StoreRequest, StoreResponse, ChatRequest, ChatResponse
from app.services.llm import LLMService
from app.services.embeddings import EmbeddingService
from app.services.qdrant_client import QdrantService
from app.graphs.store_graph import create_store_graph
from app.graphs.chat_graph import create_chat_graph
from app.config import TOP_K, MAX_CONTEXT_CHARS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global services and graphs
llm_service: LLMService = None
embedding_service: EmbeddingService = None
qdrant_service: QdrantService = None
store_graph = None
chat_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: initialize and cleanup resources."""
    global llm_service, embedding_service, qdrant_service, store_graph, chat_graph
    
    # Startup
    logger.info("Starting up RAG application...")
    
    # Initialize services
    llm_service = LLMService()
    embedding_service = EmbeddingService()
    
    # Initialize Qdrant with correct vector size
    qdrant_service = QdrantService(vector_size=embedding_service.dimension)
    qdrant_service.ensure_collection()
    
    # Create LangGraph workflows
    store_graph = create_store_graph(embedding_service, qdrant_service)
    chat_graph = create_chat_graph(
        llm_service,
        embedding_service,
        qdrant_service,
        top_k=TOP_K,
        max_context_chars=MAX_CONTEXT_CHARS
    )
    
    logger.info("Initialization complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await llm_service.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="RAG Application with LangGraph",
    description="Document storage and RAG-based chat with LangGraph orchestration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "RAG Application",
        "status": "running",
        "version": "1.0.0"
    }


@app.post("/store", response_model=StoreResponse)
async def store_document(request: StoreRequest):
    """
    Store a document by chunking its text and creating embeddings.
    
    Uses a LangGraph workflow with nodes:
    1. cleaning - Clean OCR text
    2. chunk - Split into sentence-based chunks
    3. embedding - Generate embeddings and store in Qdrant
    4. response - Build response
    """
    try:
        logger.info(f"Storing document {request.document_id} for tenant {request.tenant}")
        
        # Initialize state
        initial_state = {
            "tenant": request.tenant,
            "document_id": request.document_id,
            "ocr_text": request.ocr_text
        }
        
        # Run LangGraph workflow
        try:
            result = store_graph.invoke(initial_state)
        except Exception as e:
            logger.error(f"Store graph execution failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow execution failed: {str(e)}"
            )
        
        # Extract response
        response_data = result.get("response", {})
        
        if not response_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workflow did not produce a response"
            )
        
        logger.info(f"Successfully stored document {request.document_id}")
        
        return StoreResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /store: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Perform RAG-based chat query.
    
    Uses a LangGraph workflow with nodes:
    1. cleaning - Extract and rewrite user query
    2. search - Retrieve relevant chunks from Qdrant
    3. answer - Generate answer based on context
    """
    try:
        logger.info(f"Processing chat request for tenant {request.tenant}, user {request.user_id}")
        
        # Initialize state
        initial_state = {
            "tenant": request.tenant,
            "user_id": request.user_id,
            "messages": request.messages
        }
        
        # Run LangGraph workflow
        try:
            result = await chat_graph.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"Chat graph execution failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Workflow execution failed: {str(e)}"
            )
        
        # Extract response
        answer = result.get("answer", "")
        document_ids = result.get("document_ids", [])
        
        if not answer:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workflow did not produce an answer"
            )
        
        logger.info(f"Generated answer using {len(document_ids)} documents")
        
        return ChatResponse(answer=answer, document_ids=document_ids)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
