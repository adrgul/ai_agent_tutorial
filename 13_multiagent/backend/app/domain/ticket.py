"""Ticket triage models for classification and routing."""
from typing import Optional, List, Literal
from pydantic import BaseModel


TicketCategory = Literal[
    "Billing",
    "Technical",
    "Account",
    "Refund",
    "Shipping",
    "Other"
]

TicketPriority = Literal["P0", "P1", "P2", "P3"]

Sentiment = Literal["positive", "neutral", "negative"]


class TicketTriage(BaseModel):
    """Ticket triage result with classification and routing."""
    
    category: TicketCategory
    priority: TicketPriority
    sentiment: Optional[Sentiment] = "neutral"
    routing_team: str  # e.g., "Billing Team", "Tech Support", "Account Team"
    assignee_group: Optional[str] = None
    tags: List[str] = []
    confidence: float = 0.0  # 0.0 to 1.0
    
    def __str__(self) -> str:
        return (
            f"Category: {self.category} | "
            f"Priority: {self.priority} | "
            f"Team: {self.routing_team} | "
            f"Tags: {', '.join(self.tags) if self.tags else 'None'}"
        )
