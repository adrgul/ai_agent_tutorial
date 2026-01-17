import pytest
import json
from unittest.mock import MagicMock, create_autospec

from src.application.nodes import AgentNodes
from src.services.weather import WeatherForecaster
from src.domain.entities import WeatherData, ErrorEntity


@pytest.fixture
def mock_weather_forecaster():
    """Fixture to create a mock WeatherForecaster."""
    return create_autospec(WeatherForecaster, instance=True)


@pytest.fixture
def mock_llm_invoke():
    """Fixture to create a mock LLM invocation function."""
    return MagicMock(return_value="LLM response")


@pytest.fixture
def agent_nodes(mock_weather_forecaster, mock_llm_invoke):
    """Fixture to create AgentNodes with mocked dependencies."""
    return AgentNodes(
        weather_forecaster=mock_weather_forecaster,
        llm_invoke=mock_llm_invoke,
    )


def test_call_llm_node(agent_nodes, mock_llm_invoke):
    """
    Tests that the call_llm node correctly calls the LLM and returns the response.
    """
    initial_state = {"input": "Hello, world!"}
    result_state = agent_nodes.call_llm(initial_state)

    mock_llm_invoke.assert_called_once_with("Hello, world!")
    assert result_state["response"] == "LLM response"


def test_get_weather_info_node_success(agent_nodes, mock_weather_forecaster):
    """
    Tests the get_weather_info node on a successful weather report.
    """
    initial_state = {"input": "What's the weather in London?"}
    mock_weather_data = WeatherData(
        city="London",
        temperature=20.0,
        description="cloudy",
        humidity=80,
        wind_speed=10.0,
    )
    mock_weather_forecaster.get_current_weather_report.return_value = mock_weather_data

    result_state = agent_nodes.get_weather_info(initial_state)

    mock_weather_forecaster.get_current_weather_report.assert_called_once_with("London")
    assert "20.0°C" in result_state["tool_output"]
    assert "cloudy" in result_state["tool_output"]


def test_get_weather_info_node_error(agent_nodes, mock_weather_forecaster):
    """
    Tests the get_weather_info node when the weather service returns an error.
    """
    initial_state = {"input": "What's the weather in FakeCity?"}
    mock_error = ErrorEntity(code="NOT_FOUND", message="City not found")
    mock_weather_forecaster.get_current_weather_report.return_value = mock_error

    result_state = agent_nodes.get_weather_info(initial_state)

    mock_weather_forecaster.get_current_weather_report.assert_called_once_with("FakeCity")
    assert "Error: City not found" in result_state["tool_output"]


@pytest.mark.parametrize(
    "user_input, llm_response_action, expected_decision",
    [
        ("What's the weather in Paris?", "weather", "call_tool_weather"),
        ("Tell me a joke.", "llm", "end_response"),
    ],
)
def test_decide_next_step_node(
    agent_nodes, mock_llm_invoke, user_input, llm_response_action, expected_decision
):
    """
    Tests the logic of the decide_next_step node based on LLM's intent classification.
    """
    initial_state = {"input": user_input}
    mock_llm_invoke.return_value = json.dumps({"action": llm_response_action})

    decision = agent_nodes.decide_next_step(initial_state)
    assert decision == expected_decision

    # The prompt for the LLM is a bit complex, so we'll just check it was called.
    mock_llm_invoke.assert_called_once()
    mock_llm_invoke.reset_mock() # Reset for next parametrization run
