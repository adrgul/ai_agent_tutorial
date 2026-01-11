"""FastAPI routes for the Customer Service Triage Agent.

Following SOLID principles:
- Single Responsibility: Each endpoint handles one operation
- Dependency Inversion: Uses dependency injection
"""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.dependencies import get_workflow, get_vector_store
from app.models.schemas import TicketInput, TicketResponse
from app.workflows.langgraph_workflow import TriageWorkflow
from app.utils.vector_store import FAISSVectorStore

router = APIRouter()


@router.post(
    "/triage",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Process customer ticket",
    description="Process a customer service ticket through triage, RAG retrieval, and draft generation",
)
async def process_ticket(
    ticket: TicketInput,
    workflow: TriageWorkflow = Depends(get_workflow),
) -> TicketResponse:
    """Process a customer ticket.

    Args:
        ticket: Customer ticket input
        workflow: Injected workflow instance

    Returns:
        Complete ticket response with triage, draft, and citations

    Raises:
        HTTPException: If processing fails
    """
    try:
        response = workflow.process_ticket(ticket)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing ticket: {str(e)}",
        )


@router.get(
    "/health",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the API is healthy and KB is initialized",
)
async def health_check(
    vector_store: FAISSVectorStore = Depends(get_vector_store),
    settings: Settings = Depends(get_settings),
) -> Dict[str, str]:
    """Health check endpoint.

    Args:
        vector_store: Injected vector store instance
        settings: Application settings

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "kb_documents": str(vector_store.num_documents),
    }


@router.get(
    "/kb/stats",
    response_model=Dict[str, int],
    status_code=status.HTTP_200_OK,
    summary="Knowledge base statistics",
    description="Get statistics about the knowledge base",
)
async def kb_stats(
    vector_store: FAISSVectorStore = Depends(get_vector_store),
) -> Dict[str, int]:
    """Get knowledge base statistics.

    Args:
        vector_store: Injected vector store instance

    Returns:
        KB statistics
    """
    return {
        "total_documents": vector_store.num_documents,
        "embedding_dimension": vector_store.embedding_dimension,
    }
