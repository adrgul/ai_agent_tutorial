"""Pytest configuration and fixtures."""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before imports
os.environ["OPENAI_API_KEY"] = "test-api-key-for-testing"

from app.core.config import Settings
from app.main import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provide test settings."""
    return Settings(
        openai_api_key="test-api-key",
        llm_model="gpt-4-turbo-preview",
        embedding_model="text-embedding-3-large",
        faiss_index_path="./data/test_faiss_index",
        debug=True,
    )


@pytest.fixture(scope="module")
def test_app() -> Generator:
    """Provide test FastAPI application."""
    app = create_app()
    yield app


@pytest.fixture(scope="module")
def client(test_app) -> Generator:
    """Provide test client."""
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture
def sample_ticket():
    """Provide sample ticket data."""
    return {
        "customer_name": "John Doe",
        "customer_email": "john.doe@example.com",
        "subject": "Duplicate charge on my invoice",
        "message": "I noticed I was charged twice for the same transaction on December 5th. The amount is $49.99. Can you please help me get a refund?",
    }


@pytest.fixture
def sample_billing_ticket():
    """Provide sample billing ticket."""
    return {
        "customer_name": "Jane Smith",
        "customer_email": "jane.smith@example.com",
        "subject": "Refund request",
        "message": "I want to cancel my subscription and get a refund for this month.",
    }


@pytest.fixture
def sample_technical_ticket():
    """Provide sample technical ticket."""
    return {
        "customer_name": "Bob Johnson",
        "customer_email": "bob.johnson@example.com",
        "subject": "API timeout errors",
        "message": "I'm getting timeout errors when calling your API. Error code TIMEOUT-500. It's been happening for the past hour.",
    }
