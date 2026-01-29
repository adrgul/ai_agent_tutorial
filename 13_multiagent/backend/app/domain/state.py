"""Shared state definition with reducers for LangGraph."""
from typing import List, Optional, Annotated
from typing_extensions import TypedDict
from operator import add
from app.domain.events import TraceEvent
from app.domain.ticket import TicketTriage
from pydantic import BaseModel


class AgentAssistOutput(BaseModel):
    """Agent assist output with draft reply, summary, and actions."""
    
    draft_reply: str
    case_summary: List[str]  # bullet points
    next_actions: List[str]  # checklist items


def merge_sources(existing: List[str], new: List[str]) -> List[str]:
    """
    Reducer for sources: merge and deduplicate.
    
    This demonstrates a custom reducer that maintains unique sources
    while preserving order of appearance.
    """
    seen = set(existing)
    result = existing.copy()
    
    for source in new:
        if source not in seen:
            result.append(source)
            seen.add(source)
    
    return result


class SupportState(TypedDict):
    """
    Shared state for support agent workflows.
    
    This state is shared across all nodes in the LangGraph workflow.
    Reducers define how state updates are merged.
    """
    
    # Messages use the 'add' reducer - new messages are appended
    messages: Annotated[List[dict], add]
    
    # Pattern being executed (should not be modified by nodes)
    selected_pattern: Optional[str]
    
    # Active agent (used in handoff pattern)
    active_agent: Optional[str]
    
    # Ticket triage result
    ticket: Optional[TicketTriage]
    
    # Agent assist output
    agent_assist: Optional[AgentAssistOutput]
    
    # Knowledge sources - uses custom merge_sources reducer for deduplication
    sources: Annotated[List[str], merge_sources]
    
    # Trace events - appended chronologically
    trace: Annotated[List[TraceEvent], add]
    
    # Recursion depth tracker (for custom workflow)
    recursion_depth: int
    
    # Customer context (optional)
    customer_id: Optional[str]
    customer_tier: Optional[str]
    
    # Channel (chat, email, etc.)
    channel: str
    
    # Final answer
    final_answer: Optional[str]
    
    # Intermediate results (for routing/subagents patterns)
    routing_decision: Optional[str]
    specialist_results: Optional[dict]
