"""Tests for API endpoints."""

import pytest
from fastapi import status


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "kb_documents" in data

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestKBStatsEndpoint:
    """Tests for KB stats endpoint."""

    def test_kb_stats(self, client):
        """Test KB statistics endpoint."""
        response = client.get("/api/v1/kb/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_documents" in data
        assert "embedding_dimension" in data
        assert data["embedding_dimension"] == 1536


class TestTriageEndpoint:
    """Tests for triage endpoint."""

    def test_triage_endpoint_validation(self, client):
        """Test input validation."""
        # Missing required fields
        response = client.post("/api/v1/triage", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Invalid email
        response = client.post(
            "/api/v1/triage",
            json={
                "customer_name": "Test",
                "customer_email": "invalid-email",
                "subject": "Test",
                "message": "Test message",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_triage_response_structure(self, client, sample_ticket):
        """Test response structure (mock test without actual API call)."""
        # This test validates the Pydantic models
        from app.models.schemas import TicketInput, TicketResponse

        # Validate input model
        ticket = TicketInput(**sample_ticket)
        assert ticket.customer_name == "John Doe"
        assert ticket.customer_email == "john.doe@example.com"

        # Note: Full integration test would require OpenAI API key
        # For now, we validate the schema structure

    @pytest.mark.skip(reason="Requires OpenAI API key")
    def test_process_billing_ticket(self, client, sample_ticket):
        """Test processing a billing ticket (requires API key)."""
        response = client.post("/api/v1/triage", json=sample_ticket)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check structure
        assert "ticket_id" in data
        assert "timestamp" in data
        assert "triage" in data
        assert "answer_draft" in data
        assert "citations" in data
        assert "policy_check" in data

        # Check triage
        triage = data["triage"]
        assert triage["priority"] in ["P1", "P2", "P3", "P4"]
        assert triage["sla_hours"] > 0
        assert "category" in triage

        # Check draft
        draft = data["answer_draft"]
        assert "greeting" in draft
        assert "body" in draft
        assert "closing" in draft

        # Check policy
        policy = data["policy_check"]
        assert "compliance" in policy
