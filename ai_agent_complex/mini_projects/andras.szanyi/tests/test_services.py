import pytest
from unittest.mock import MagicMock

from src.services.weather import WeatherForecaster
from src.domain.interfaces import WeatherProviderProtocol, GeoLocationProviderProtocol
from src.domain.entities import WeatherData, ErrorEntity, Coordinates


@pytest.fixture
def mock_weather_provider():
    """Fixture to create a mock weather provider."""
    return MagicMock(spec=WeatherProviderProtocol)


@pytest.fixture
def mock_geo_locator():
    """Fixture to create a mock geo locator."""
    return MagicMock(spec=GeoLocationProviderProtocol)


@pytest.fixture
def weather_forecaster(mock_weather_provider, mock_geo_locator):
    """Fixture to create a WeatherForecaster with mocked dependencies."""
    return WeatherForecaster(
        weather_provider=mock_weather_provider, geo_locator=mock_geo_locator
    )


def test_get_current_weather_report_success(
    weather_forecaster, mock_weather_provider, mock_geo_locator
):
    """
    Tests that the forecaster correctly orchestrates geo-lookup and weather fetch.
    """
    # Setup Mocks
    mock_coords = Coordinates(lat=51.5074, lon=-0.1278)
    mock_geo_locator.get_coordinates.return_value = mock_coords

    mock_weather_data = WeatherData(
        city="Unknown", temperature=15.0, description="cloudy", wind_speed=5.0
    )
    mock_weather_provider.get_current_weather.return_value = mock_weather_data

    # Execute
    result = weather_forecaster.get_current_weather_report("London")

    # Assertions
    mock_geo_locator.get_coordinates.assert_called_once_with("London")
    mock_weather_provider.get_current_weather.assert_called_once_with(
        lat=51.5074, lon=-0.1278
    )
    
    assert isinstance(result, WeatherData)
    assert result.city == "London"  # Should be enriched
    assert result.temperature == 15.0


def test_get_current_weather_report_geo_error(
    weather_forecaster, mock_weather_provider, mock_geo_locator
):
    """
    Tests that if geolocation fails, the error is propagated and weather is not fetched.
    """
    mock_error = ErrorEntity(code="NOT_FOUND", message="City not found")
    mock_geo_locator.get_coordinates.return_value = mock_error

    result = weather_forecaster.get_current_weather_report("FakeCity")

    assert result == mock_error
    mock_geo_locator.get_coordinates.assert_called_once_with("FakeCity")
    mock_weather_provider.get_current_weather.assert_not_called()


def test_get_current_weather_report_weather_error(
    weather_forecaster, mock_weather_provider, mock_geo_locator
):
    """
    Tests that if weather fetch fails, the error is returned.
    """
    mock_coords = Coordinates(lat=51.5, lon=-0.1)
    mock_geo_locator.get_coordinates.return_value = mock_coords

    mock_error = ErrorEntity(code="API_ERROR", message="Service down")
    mock_weather_provider.get_current_weather.return_value = mock_error

    result = weather_forecaster.get_current_weather_report("London")

    assert result == mock_error
    mock_geo_locator.get_coordinates.assert_called_once()
    mock_weather_provider.get_current_weather.assert_called_once()