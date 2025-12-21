import pytest
from unittest.mock import patch, Mock
from src.infrastructure.external import OpenWeatherMapGeoLocator, OpenMeteoWeatherClient
from src.infrastructure.config import AppSettings
from src.domain.entities import Coordinates, WeatherData, ErrorEntity


@pytest.fixture
def mock_settings():
    settings = Mock(spec=AppSettings)
    settings.OPENWEATHER_API_KEY = "test_key"
    return settings


class TestOpenWeatherMapGeoLocator:
    @patch("requests.get")
    def test_get_coordinates_success(self, mock_get, mock_settings):
        # Setup
        locator = OpenWeatherMapGeoLocator(mock_settings)
        
        mock_response = Mock()
        mock_response.json.return_value = [{"lat": 51.5074, "lon": -0.1278}]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Execute
        result = locator.get_coordinates("London")

        # Assert
        assert isinstance(result, Coordinates)
        assert result.lat == 51.5074
        assert result.lon == -0.1278
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["q"] == "London"
        assert kwargs["params"]["appid"] == "test_key"

    @patch("requests.get")
    def test_get_coordinates_not_found(self, mock_get, mock_settings):
        locator = OpenWeatherMapGeoLocator(mock_settings)
        
        mock_response = Mock()
        mock_response.json.return_value = [] # Empty list
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = locator.get_coordinates("Nowhere")

        assert isinstance(result, ErrorEntity)
        assert result.code == "NOT_FOUND"


class TestOpenMeteoWeatherClient:
    @patch("requests.get")
    def test_get_current_weather_success(self, mock_get):
        client = OpenMeteoWeatherClient()
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "current_weather": {
                "temperature": 12.5,
                "windspeed": 10.0,
                "weathercode": 0
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = client.get_current_weather(lat=52.52, lon=13.41)

        assert isinstance(result, WeatherData)
        assert result.temperature == 12.5
        assert result.description == "Clear sky"

    @patch("requests.get")
    def test_get_current_weather_parse_error(self, mock_get):
        client = OpenMeteoWeatherClient()
        
        mock_response = Mock()
        mock_response.json.return_value = {} # Missing current_weather
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = client.get_current_weather(lat=52.52, lon=13.41)

        assert isinstance(result, ErrorEntity)
        assert result.code == "PARSE_ERROR"