"""Guardrails and handoff policy rules."""
from typing import List, Optional
from pydantic import BaseModel


class HandoffPolicy(BaseModel):
    """Policy for determining when to handoff to human."""
    
    trigger: str
    reason: str
    priority: str = "P1"


# Policy trigger keywords and patterns
ESCALATION_KEYWORDS = {
    "refund_dispute": ["refund", "dispute", "chargeback", "fraudulent"],
    "legal_threat": ["lawyer", "legal action", "sue", "court"],
    "account_takeover": ["hacked", "unauthorized access", "compromised", "stolen account"],
    "payment_fraud": ["fraud", "unauthorized charge", "didn't authorize"],
    "high_value": ["enterprise", "business account", "premium"],
}


def check_handoff_policy(message: str, sentiment: Optional[str] = None) -> Optional[HandoffPolicy]:
    """
    Check if message triggers human handoff based on policy rules.
    
    Args:
        message: User message text
        sentiment: Detected sentiment (positive/neutral/negative)
        
    Returns:
        HandoffPolicy if handoff triggered, None otherwise
    """
    message_lower = message.lower()
    
    # Check for refund disputes
    if any(kw in message_lower for kw in ESCALATION_KEYWORDS["refund_dispute"]):
        if "dispute" in message_lower or "chargeback" in message_lower:
            return HandoffPolicy(
                trigger="refund_dispute",
                reason="Refund dispute requires human review",
                priority="P1"
            )
    
    # Check for legal threats
    if any(kw in message_lower for kw in ESCALATION_KEYWORDS["legal_threat"]):
        return HandoffPolicy(
            trigger="legal_threat",
            reason="Legal threat detected - immediate escalation required",
            priority="P0"
        )
    
    # Check for account takeover
    if any(kw in message_lower for kw in ESCALATION_KEYWORDS["account_takeover"]):
        return HandoffPolicy(
            trigger="account_takeover",
            reason="Potential account security issue",
            priority="P0"
        )
    
    # Check for payment fraud
    if any(kw in message_lower for kw in ESCALATION_KEYWORDS["payment_fraud"]):
        return HandoffPolicy(
            trigger="payment_fraud",
            reason="Payment fraud concern requires investigation",
            priority="P0"
        )
    
    # Check for high negative sentiment + urgency
    if sentiment == "negative":
        urgent_keywords = ["urgent", "immediately", "asap", "emergency", "now"]
        if any(kw in message_lower for kw in urgent_keywords):
            return HandoffPolicy(
                trigger="high_urgency_negative",
                reason="High urgency negative sentiment",
                priority="P1"
            )
    
    return None


def generate_case_brief(message: str, context: dict) -> str:
    """
    Generate a case brief for human agent when handoff occurs.
    
    Args:
        message: Original user message
        context: Additional context (category, sources, etc.)
        
    Returns:
        Formatted case brief
    """
    category = context.get("category", "Unknown")
    sources = context.get("sources", [])
    
    brief = f"""
CASE BRIEF - HUMAN HANDOFF
==========================

Customer Message:
{message}

Classification:
- Category: {category}
- Priority: {context.get('priority', 'P2')}
- Sentiment: {context.get('sentiment', 'neutral')}

Handoff Reason:
{context.get('handoff_reason', 'Policy trigger')}

Relevant Knowledge Base Articles:
{chr(10).join(f'- {src}' for src in sources[:3]) if sources else '- None'}

Suggested Next Steps:
1. Review customer account history
2. Verify customer identity
3. Assess eligibility based on policy
4. Provide personalized resolution

IMMEDIATE ACTION REQUIRED
"""
    return brief.strip()
