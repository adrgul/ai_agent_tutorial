"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AnswerDraft,
    Citation,
    IntentDetectionResult,
    KBArticle,
    KBChunk,
    PolicyCheck,
    Priority,
    ProblemType,
    Sentiment,
    TicketInput,
    Tone,
    TriageResult,
)


class TestTicketInput:
    """Tests for TicketInput model."""

    def test_valid_ticket_input(self):
        """Test valid ticket input."""
        ticket = TicketInput(
            customer_name="John Doe",
            customer_email="john@example.com",
            subject="Test Subject",
            message="This is a test message with enough characters.",
        )

        assert ticket.customer_name == "John Doe"
        assert ticket.customer_email == "john@example.com"
        assert ticket.subject == "Test Subject"

    def test_invalid_email(self):
        """Test invalid email validation."""
        with pytest.raises(ValidationError):
            TicketInput(
                customer_name="John Doe",
                customer_email="invalid-email",
                subject="Test",
                message="Test message with enough text.",
            )

    def test_message_too_short(self):
        """Test message minimum length validation."""
        with pytest.raises(ValidationError):
            TicketInput(
                customer_name="John Doe",
                customer_email="john@example.com",
                subject="Test",
                message="Short",
            )

    def test_email_normalization(self):
        """Test email is normalized to lowercase."""
        ticket = TicketInput(
            customer_name="John Doe",
            customer_email="John@Example.COM",
            subject="Test",
            message="Test message here.",
        )

        assert ticket.customer_email == "john@example.com"


class TestIntentDetectionResult:
    """Tests for IntentDetectionResult model."""

    def test_valid_intent_result(self):
        """Test valid intent detection result."""
        result = IntentDetectionResult(
            problem_type=ProblemType.BILLING,
            sentiment=Sentiment.FRUSTRATED,
            confidence=0.95,
            reasoning="Clear billing issue mentioned",
        )

        assert result.problem_type == ProblemType.BILLING
        assert result.sentiment == Sentiment.FRUSTRATED
        assert result.confidence == 0.95

    def test_confidence_validation(self):
        """Test confidence score validation."""
        # Valid confidence
        result = IntentDetectionResult(
            problem_type=ProblemType.BILLING,
            sentiment=Sentiment.NEUTRAL,
            confidence=0.5,
            reasoning="Test",
        )
        assert result.confidence == 0.5

        # Invalid confidence (too high)
        with pytest.raises(ValidationError):
            IntentDetectionResult(
                problem_type=ProblemType.BILLING,
                sentiment=Sentiment.NEUTRAL,
                confidence=1.5,
                reasoning="Test",
            )

        # Invalid confidence (negative)
        with pytest.raises(ValidationError):
            IntentDetectionResult(
                problem_type=ProblemType.BILLING,
                sentiment=Sentiment.NEUTRAL,
                confidence=-0.1,
                reasoning="Test",
            )


class TestTriageResult:
    """Tests for TriageResult model."""

    def test_valid_triage_result(self):
        """Test valid triage result."""
        result = TriageResult(
            category="Billing - Invoice Issue",
            subcategory="Duplicate Charge",
            priority=Priority.P2,
            sla_hours=24,
            suggested_team="Finance Team",
            sentiment=Sentiment.FRUSTRATED,
            confidence=0.92,
        )

        assert result.priority == Priority.P2
        assert result.sla_hours == 24
        assert result.suggested_team == "Finance Team"

    def test_invalid_sla_hours(self):
        """Test SLA hours validation."""
        with pytest.raises(ValidationError):
            TriageResult(
                category="Test",
                subcategory="Test",
                priority=Priority.P2,
                sla_hours=0,  # Must be > 0
                suggested_team="Test Team",
                sentiment=Sentiment.NEUTRAL,
                confidence=0.9,
            )


class TestCitation:
    """Tests for Citation model."""

    def test_valid_citation(self):
        """Test valid citation."""
        citation = Citation(
            doc_id="KB-1234",
            chunk_id="c-45",
            title="Test Article",
            score=0.89,
            url="https://kb.example.com/article",
        )

        assert citation.doc_id == "KB-1234"
        assert citation.chunk_id == "c-45"
        assert citation.score == 0.89

    def test_optional_content(self):
        """Test optional content field."""
        citation = Citation(
            doc_id="KB-1234",
            chunk_id="c-45",
            title="Test Article",
            score=0.89,
            url="https://kb.example.com/article",
            content="Article content here",
        )

        assert citation.content == "Article content here"


class TestAnswerDraft:
    """Tests for AnswerDraft model."""

    def test_valid_answer_draft(self):
        """Test valid answer draft."""
        draft = AnswerDraft(
            greeting="Dear John,",
            body="Thank you for contacting us...",
            closing="Best regards,\nSupport Team",
            tone=Tone.EMPATHETIC_PROFESSIONAL,
        )

        assert draft.greeting == "Dear John,"
        assert draft.tone == Tone.EMPATHETIC_PROFESSIONAL


class TestPolicyCheck:
    """Tests for PolicyCheck model."""

    def test_valid_policy_check(self):
        """Test valid policy check."""
        policy = PolicyCheck(
            refund_promise=False,
            sla_mentioned=True,
            escalation_needed=False,
            compliance="passed",
            warnings=["Minor warning"],
        )

        assert policy.compliance == "passed"
        assert len(policy.warnings) == 1

    def test_empty_warnings(self):
        """Test empty warnings list."""
        policy = PolicyCheck(
            refund_promise=False,
            sla_mentioned=True,
            escalation_needed=False,
            compliance="passed",
        )

        assert policy.warnings == []


class TestKBModels:
    """Tests for KB models."""

    def test_kb_article(self):
        """Test KB article model."""
        article = KBArticle(
            doc_id="KB-1234",
            title="Test Article",
            content="Article content here",
            category="Billing",
            url="https://kb.example.com/article",
        )

        assert article.doc_id == "KB-1234"
        assert article.category == "Billing"

    def test_kb_chunk(self):
        """Test KB chunk model."""
        chunk = KBChunk(
            chunk_id="c-45",
            doc_id="KB-1234",
            title="Test Article",
            content="Chunk content",
            chunk_index=0,
            url="https://kb.example.com/article",
            category="Billing",
        )

        assert chunk.chunk_id == "c-45"
        assert chunk.chunk_index == 0
