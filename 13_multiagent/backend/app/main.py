"""FastAPI main application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.presentation.api.ws_chat import router as ws_router
from app.presentation.api.http_routes import router as http_router
from app.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Customer Support Agent API",
    description="Multi-agent customer support system with 5 LangGraph patterns",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(http_router)
app.include_router(ws_router, prefix="/ws")


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Starting AI Customer Support Agent API")
    logger.info(f"API docs available at http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Shutting down AI Customer Support Agent API")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Customer Support Agent API",
        "docs": "/docs",
        "websocket": "/ws/chat",
        "patterns": "/api/patterns",
    }
