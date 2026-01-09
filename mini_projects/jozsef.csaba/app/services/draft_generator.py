"""Draft Generator Service.

Following SOLID principles:
- Single Responsibility: Generates response drafts
- Dependency Inversion: Depends on LLM abstraction
"""

from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.models.schemas import (
    AnswerDraft,
    Citation,
    Sentiment,
    TicketInput,
    Tone,
    TriageResult,
)


class DraftGeneratorService:
    """Service for generating customer response drafts."""

    def __init__(self, settings: Settings):
        """Initialize draft generator service.

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
            ("system", """You are an expert customer service response writer. Create a professional, empathetic response draft.

Guidelines:
- Address customer by name
- Acknowledge their concern
- Provide clear, actionable information
- Include citations to KB articles using [DOC-ID] format
- Match tone to customer sentiment
- Be concise but thorough
- Never make promises outside policy

Tone guidelines:
- frustrated → empathetic_professional (acknowledge frustration, apologize if appropriate)
- neutral → friendly (professional but warm)
- satisfied → friendly (maintain positive tone)

Return ONLY valid JSON:
{{
    "greeting": "Dear [Name],",
    "body": "Response with [KB-1234] citations embedded naturally...",
    "closing": "Best regards,\\nSupport Team",
    "tone": "empathetic_professional|formal|friendly|apologetic"
}}"""),
            ("user", """Ticket:
From: {customer_name}
Subject: {subject}
Message: {message}

Classification:
Category: {category}
Priority: {priority}
SLA: {sla_hours} hours
Sentiment: {sentiment}

Knowledge Base Articles:
{kb_articles}

Generate response draft as JSON.""")
        ])

        self.parser = JsonOutputParser()

    async def generate_draft(
        self,
        ticket: TicketInput,
        triage_result: TriageResult,
        citations: List[Citation],
    ) -> AnswerDraft:
        """Generate response draft with KB citations.

        Args:
            ticket: Customer ticket
            triage_result: Triage classification
            citations: Retrieved KB articles

        Returns:
            Generated answer draft
        """
        # Format KB articles
        kb_text = self._format_kb_articles(citations)

        # Create chain
        chain = self.prompt | self.llm | self.parser

        # Invoke LLM
        result = await chain.ainvoke({
            "customer_name": ticket.customer_name,
            "subject": ticket.subject,
            "message": ticket.message,
            "category": triage_result.category,
            "priority": triage_result.priority.value,
            "sla_hours": triage_result.sla_hours,
            "sentiment": triage_result.sentiment.value,
            "kb_articles": kb_text,
        })

        return AnswerDraft(
            greeting=result["greeting"],
            body=result["body"],
            closing=result["closing"],
            tone=Tone(result["tone"]),
        )

    def generate_draft_sync(
        self,
        ticket: TicketInput,
        triage_result: TriageResult,
        citations: List[Citation],
    ) -> AnswerDraft:
        """Synchronous version of draft generation.

        Args:
            ticket: Customer ticket
            triage_result: Triage classification
            citations: Retrieved KB articles

        Returns:
            Generated answer draft
        """
        # Format KB articles
        kb_text = self._format_kb_articles(citations)

        # Create chain
        chain = self.prompt | self.llm | self.parser

        # Invoke LLM
        result = chain.invoke({
            "customer_name": ticket.customer_name,
            "subject": ticket.subject,
            "message": ticket.message,
            "category": triage_result.category,
            "priority": triage_result.priority.value,
            "sla_hours": triage_result.sla_hours,
            "sentiment": triage_result.sentiment.value,
            "kb_articles": kb_text,
        })

        return AnswerDraft(
            greeting=result["greeting"],
            body=result["body"],
            closing=result["closing"],
            tone=Tone(result["tone"]),
        )

    def _format_kb_articles(self, citations: List[Citation]) -> str:
        """Format KB articles for prompt.

        Args:
            citations: List of citations

        Returns:
            Formatted KB articles text
        """
        if not citations:
            return "No specific KB articles found. Provide general guidance."

        formatted = []
        for citation in citations:
            formatted.append(
                f"[{citation.doc_id}] {citation.title}\n"
                f"URL: {citation.url}\n"
                f"Content: {citation.content[:500]}..."
            )

        return "\n\n".join(formatted)
