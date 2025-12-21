import pytest
from unittest.mock import patch
from langgraph.graph.state import CompiledStateGraph
from src.container import Container


@pytest.fixture
def mock_settings():
    """Fixture to mock AppSettings to avoid raising SystemExit."""
    with patch("src.infrastructure.config.AppSettings.load") as mock_load:
        mock_load.return_value.GROQ_API_KEY = "test_groq_key"
        mock_load.return_value.OPENWEATHER_API_KEY = "test_weather_key"
        yield mock_load


def test_container_initialization(mock_settings):
    """
    Tests that the Container can be initialized without errors.
    """
    try:
        container = Container()
        assert container is not None, "Container should not be None"
        assert container.settings is not None, "Settings should not be None"
        assert container.llm_client is not None, "LLM client should not be None"
        assert (
            container.geo_locator is not None
        ), "Geo Locator should not be None"
        assert (
            container.weather_client is not None
        ), "Weather client should not be None"
        assert (
            container.weather_forecaster is not None
        ), "Weather forecaster should not be None"
        assert container.agent_nodes is not None, "Agent nodes should not be None"
        assert isinstance(
            container.agent_graph, CompiledStateGraph
        ), "Agent graph should be an instance of a compiled LangGraph"
    except Exception as e:
        pytest.fail(f"Container initialization failed: {e}")