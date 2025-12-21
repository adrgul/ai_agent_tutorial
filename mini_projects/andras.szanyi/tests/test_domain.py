from src.domain.state import AgentState
from src.domain.entities import WeatherData, ErrorEntity


def test_agent_state_creation():
    """
    Tests that AgentState can be created as a dictionary.
    """
    state: AgentState = {
        "input": "test input",
        "chat_history": [],
        "intermediate_steps": [],
        "tool_output": "",
        "response": "",
    }
    assert state["input"] == "test input"


def test_weather_data_creation():
    """
    Tests that WeatherData can be created with the expected fields.
    """
    weather_data = WeatherData(
        city="Test City",
        temperature=25.5,
        description="clear sky",
        humidity=60,
        wind_speed=5.5,
    )
    assert weather_data.city == "Test City"
    assert weather_data.temperature == 25.5


def test_error_entity_creation():
    """
    Tests that ErrorEntity can be created with the expected fields.
    """
    error_entity = ErrorEntity(code="TEST_ERROR", message="This is a test error.")
    assert error_entity.code == "TEST_ERROR"
    assert error_entity.message == "This is a test error."
