"""Pydantic models for the Customer Service Triage Agent.

Following SOLID principles:
- Single Responsibility: Each model represents one concept
- Interface Segregation: Models are focused and minimal
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ProblemType(str, Enum):
    """Types of customer problems."""

    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"


class Sentiment(str, Enum):
    """Customer sentiment levels."""

    FRUSTRATED = "frustrated"
    NEUTRAL = "neutral"
    SATISFIED = "satisfied"


class Priority(str, Enum):
    """Ticket priority levels."""

    P1 = "P1"  # Critical - 4 hours
    P2 = "P2"  # High - 24 hours
    P3 = "P3"  # Medium - 3 days
    P4 = "P4"  # Low - 1 week


class Tone(str, Enum):
    """Response tone options."""

    EMPATHETIC_PROFESSIONAL = "empathetic_professional"
    FORMAL = "formal"
    FRIENDLY = "friendly"
    APOLOGETIC = "apologetic"


# Input Models


class TicketInput(BaseModel):
    """Input model for incoming customer tickets."""

    customer_name: str = Field(..., min_length=1, description="Customer's name")
    customer_email: str = Field(..., description="Customer's email address")
    subject: str = Field(..., min_length=1, description="Ticket subject")
    message: str = Field(..., min_length=10, description="Customer's message")
    ticket_id: Optional[str] = Field(None, description="External ticket ID")

    @field_validator("customer_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Basic email validation."""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v.lower()


# Domain Models


class IntentDetectionResult(BaseModel):
    """Result of intent detection analysis."""

    problem_type: ProblemType = Field(..., description="Detected problem category")
    sentiment: Sentiment = Field(..., description="Customer sentiment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(..., description="Explanation of detection")


class TriageResult(BaseModel):
    """Result of ticket triage classification."""

    category: str = Field(..., description="Main category (e.g., 'Billing - Invoice Issue')")
    subcategory: str = Field(..., description="Specific subcategory")
    priority: Priority = Field(..., description="Priority level")
    sla_hours: int = Field(..., gt=0, description="SLA response time in hours")
    suggested_team: str = Field(..., description="Recommended team for handling")
    sentiment: Sentiment = Field(..., description="Customer sentiment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")


class Citation(BaseModel):
    """Knowledge base citation."""

    doc_id: str = Field(..., description="Document identifier")
    chunk_id: str = Field(..., description="Specific chunk identifier")
    title: str = Field(..., description="Document title")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    url: str = Field(..., description="URL to the knowledge base article")
    content: Optional[str] = Field(None, description="Snippet of relevant content")


class AnswerDraft(BaseModel):
    """Generated answer draft."""

    greeting: str = Field(..., description="Personalized greeting")
    body: str = Field(..., description="Main response body with citations")
    closing: str = Field(..., description="Professional closing")
    tone: Tone = Field(..., description="Response tone")


class PolicyCheck(BaseModel):
    """Policy compliance validation."""

    refund_promise: bool = Field(..., description="Whether refund was promised")
    sla_mentioned: bool = Field(..., description="Whether SLA was mentioned")
    escalation_needed: bool = Field(..., description="Whether escalation is required")
    compliance: str = Field(..., description="Overall compliance status")
    warnings: List[str] = Field(default_factory=list, description="Policy warnings")


# Output Models


class TicketResponse(BaseModel):
    """Complete ticket processing response."""

    ticket_id: str = Field(..., description="Unique ticket identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    triage: TriageResult = Field(..., description="Triage classification results")
    answer_draft: AnswerDraft = Field(..., description="Generated response draft")
    citations: List[Citation] = Field(..., description="Knowledge base citations")
    policy_check: PolicyCheck = Field(..., description="Policy compliance check")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "ticket_id": "TKT-2025-01-10-0001",
                "timestamp": "2025-01-10T14:32:00Z",
                "triage": {
                    "category": "Billing - Invoice Issue",
                    "subcategory": "Duplicate Charge",
                    "priority": "P2",
                    "sla_hours": 24,
                    "suggested_team": "Finance Team",
                    "sentiment": "frustrated",
                    "confidence": 0.92,
                },
                "answer_draft": {
                    "greeting": "Dear John,",
                    "body": "Thank you for reaching out...",
                    "closing": "Best regards,\\nSupport Team",
                    "tone": "empathetic_professional",
                },
                "citations": [],
                "policy_check": {
                    "refund_promise": False,
                    "sla_mentioned": True,
                    "escalation_needed": False,
                    "compliance": "passed",
                    "warnings": [],
                },
            }
        }


# Knowledge Base Models


class KBArticle(BaseModel):
    """Knowledge base article structure."""

    doc_id: str = Field(..., description="Unique document ID")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Full article content")
    category: str = Field(..., description="Article category")
    url: str = Field(..., description="Article URL")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class KBChunk(BaseModel):
    """Chunked knowledge base content for vector storage."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Parent document ID")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Chunk content")
    chunk_index: int = Field(..., description="Chunk position in document")
    url: str = Field(..., description="Source URL")
    category: str = Field(..., description="Document category")


# Workflow State Models


class WorkflowState(BaseModel):
    """State object for LangGraph workflow."""

    ticket_input: TicketInput
    intent_result: Optional[IntentDetectionResult] = None
    triage_result: Optional[TriageResult] = None
    search_queries: Optional[List[str]] = None
    retrieved_docs: Optional[List[Citation]] = None
    reranked_docs: Optional[List[Citation]] = None
    answer_draft: Optional[AnswerDraft] = None
    policy_check: Optional[PolicyCheck] = None
    ticket_id: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
