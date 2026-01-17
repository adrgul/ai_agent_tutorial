"""
Pytest configuration and shared fixtures.
"""
import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    # Reset postgres_client pool
    from infrastructure.postgres_client import postgres_client
    postgres_client.pool = None
    postgres_client._initializing = False
    
    yield
    
    # Cleanup after test
    postgres_client.pool = None
    postgres_client._initializing = False
