"""Triage Classification Service.

Following SOLID principles:
- Single Responsibility: Only handles ticket triage and prioritization
- Dependency Inversion: Depends on LLM abstraction
"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.models.schemas import (
    IntentDetectionResult,
    Priority,
    Sentiment,
    TicketInput,
    TriageResult,
)


class TriageService:
    """Service for ticket triage and classification."""

    # SLA mapping
    SLA_HOURS = {
        Priority.P1: 4,
        Priority.P2: 24,
        Priority.P3: 72,
        Priority.P4: 168,
    }

    def __init__(self, settings: Settings):
        """Initialize triage service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.temperature,
            openai_api_key=settings.openai_api_key,
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert customer service triage specialist. Based on the ticket information and detected intent, classify the ticket with:

1. Category: Main category (e.g., "Billing - Invoice Issue", "Technical - API Error")
2. Subcategory: Specific issue type
3. Priority: P1 (Critical-4h), P2 (High-24h), P3 (Medium-3d), P4 (Low-1w)
4. Suggested Team: Which team should handle this

Priority guidelines:
- P1: Payment failures, security issues, system down, data loss
- P2: Billing errors, account locked, feature broken, refunds
- P3: General technical issues, feature questions, documentation
- P4: Feature requests, general inquiries, feedback

Return ONLY a valid JSON object:
{{
    "category": "Category - Specific Issue",
    "subcategory": "More specific description",
    "priority": "P1|P2|P3|P4",
    "suggested_team": "Team Name",
    "confidence": 0.95
}}"""),
            ("user", """Ticket Information:
Subject: {subject}
Message: {message}
Customer: {customer_name}

Intent Analysis:
Problem Type: {problem_type}
Sentiment: {sentiment}
Reasoning: {reasoning}

Provide triage classification as JSON.""")
        ])

        self.parser = JsonOutputParser()

    async def classify_ticket(
        self,
        ticket: TicketInput,
        intent_result: IntentDetectionResult,
    ) -> TriageResult:
        """Classify ticket and assign priority.

        Args:
            ticket: Customer ticket input
            intent_result: Intent detection result

        Returns:
            Triage classification result
        """
        # Create chain
        chain = self.prompt | self.llm | self.parser

        # Invoke LLM
        result = await chain.ainvoke({
            "subject": ticket.subject,
            "message": ticket.message,
            "customer_name": ticket.customer_name,
            "problem_type": intent_result.problem_type.value,
            "sentiment": intent_result.sentiment.value,
            "reasoning": intent_result.reasoning,
        })

        # Parse priority and get SLA
        priority = Priority(result["priority"])
        sla_hours = self.SLA_HOURS[priority]

        return TriageResult(
            category=result["category"],
            subcategory=result["subcategory"],
            priority=priority,
            sla_hours=sla_hours,
            suggested_team=result["suggested_team"],
            sentiment=intent_result.sentiment,
            confidence=float(result["confidence"]),
        )

    def classify_ticket_sync(
        self,
        ticket: TicketInput,
        intent_result: IntentDetectionResult,
    ) -> TriageResult:
        """Synchronous version of ticket classification.

        Args:
            ticket: Customer ticket input
            intent_result: Intent detection result

        Returns:
            Triage classification result
        """
        # Create chain
        chain = self.prompt | self.llm | self.parser

        # Invoke LLM
        result = chain.invoke({
            "subject": ticket.subject,
            "message": ticket.message,
            "customer_name": ticket.customer_name,
            "problem_type": intent_result.problem_type.value,
            "sentiment": intent_result.sentiment.value,
            "reasoning": intent_result.reasoning,
        })

        # Parse priority and get SLA
        priority = Priority(result["priority"])
        sla_hours = self.SLA_HOURS[priority]

        return TriageResult(
            category=result["category"],
            subcategory=result["subcategory"],
            priority=priority,
            sla_hours=sla_hours,
            suggested_team=result["suggested_team"],
            sentiment=intent_result.sentiment,
            confidence=float(result["confidence"]),
        )
