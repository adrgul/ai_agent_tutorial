"""HTTP routes for REST API endpoints."""
from fastapi import APIRouter
from app.application.orchestration.graph_factory import GraphFactory
from app.infrastructure.tools.kb_tool import get_all_kb_articles
from app.core.config import config

router = APIRouter(prefix="/api")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": config.MODEL_NAME,
        "has_api_key": config.has_api_key(),
        "max_recursion_limit": config.MAX_RECURSION_LIMIT,
    }


@router.get("/patterns")
async def get_patterns():
    """Get available multi-agent patterns."""
    return {
        "patterns": GraphFactory.get_available_patterns()
    }


@router.get("/demo/kb")
async def get_kb_articles():
    """
    Get all knowledge base articles for demo purposes.
    
    This allows the frontend to show what KB articles are available.
    """
    articles = get_all_kb_articles()
    return {
        "articles": articles,
        "count": len(articles)
    }
