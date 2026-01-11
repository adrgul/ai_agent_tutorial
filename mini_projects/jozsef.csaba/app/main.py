"""FastAPI application for Customer Service Triage Agent.

This is the main entry point for the application.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.dependencies import initialize_knowledge_base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    print("Starting Customer Service Triage Agent...")
    print("Initializing knowledge base...")

    try:
        initialize_knowledge_base()
        print("Knowledge base initialized successfully")
    except Exception as e:
        print(f"Warning: Failed to initialize knowledge base: {e}")
        print("The application will start but may not function correctly")

    yield

    # Shutdown
    print("Shutting down Customer Service Triage Agent...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        Customer Service Triage and Response Agent with Knowledge Base

        ## Features
        - **Intent Detection**: Automatically detect problem type and sentiment
        - **Smart Triage**: Classify tickets by category, priority, and SLA
        - **RAG Retrieval**: Find relevant KB articles using vector search
        - **Draft Generation**: Create professional responses with citations
        - **Policy Check**: Validate responses against company policies

        ## Workflow
        1. Submit a ticket via POST /api/v1/triage
        2. System analyzes intent and sentiment
        3. Classifies and prioritizes the ticket
        4. Retrieves relevant KB articles
        5. Generates response draft with citations
        6. Validates against policies
        7. Returns complete structured response
        """,
        lifespan=lifespan,
        debug=settings.debug,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(router, prefix="/api/v1", tags=["triage"])

    @app.get("/", tags=["root"])
    async def root():
        """Root endpoint."""
        return {
            "message": "Customer Service Triage Agent API",
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
