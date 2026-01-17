"""Pydantic models for API requests and responses."""

from typing import List, Literal
from pydantic import BaseModel, Field


class StoreRequest(BaseModel):
    """Request model for storing a document."""
    tenant: str = Field(..., description="Tenant identifier")
    document_id: str = Field(..., description="Document identifier")
    ocr_text: str = Field(..., description="Raw OCR text of the document")


class StoreResponse(BaseModel):
    """Response model for document storage."""
    success: Literal["ok"] = Field(..., description="Status message")
    chunks_count: int = Field(..., description="Number of chunks stored")


class ChatMessage(BaseModel):
    """Individual chat message."""
    role: str = Field(..., description="Role (system, user, assistant)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    tenant: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="User identifier")
    messages: List[ChatMessage] = Field(..., description="Conversation history")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    answer: str = Field(..., description="Generated answer")
    document_ids: List[str] = Field(..., description="Document IDs used for context")
