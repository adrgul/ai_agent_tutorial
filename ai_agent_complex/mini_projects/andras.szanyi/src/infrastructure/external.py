import requests
from typing import Union

from src.domain.entities import Coordinates, ErrorEntity, WeatherData
from src.domain.interfaces import GeoLocationProviderProtocol, WeatherProviderProtocol
from src.infrastructure.config import AppSettings


class OpenWeatherMapGeoLocator(GeoLocationProviderProtocol):
    """
    Concrete implementation of GeoLocationProviderProtocol using OpenWeatherMap Geocoding API.
    """

    def __init__(self, settings: AppSettings):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = "http://api.openweathermap.org/geo/1.0/direct"

    def get_coordinates(self, city: str) -> Union[Coordinates, ErrorEntity]:
        """
        Retrieves coordinates for a given city using OpenWeatherMap Geocoding API.
        """
        params = {"q": city, "limit": 1, "appid": self.api_key}
        try:
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if not data:
                return ErrorEntity(code="NOT_FOUND", message=f"City '{city}' not found.")

            # The API returns a list of locations
            location = data[0]
            return Coordinates(lat=location["lat"], lon=location["lon"])

        except requests.exceptions.RequestException as req_err:
            return ErrorEntity(
                code="REQUEST_ERROR",
                message=f"GeoLocation request failed: {req_err}",
            )


class OpenMeteoWeatherClient(WeatherProviderProtocol):
    """
    Concrete implementation of WeatherProviderProtocol for Open-Meteo.
    """

    def __init__(self):
        # Open-Meteo does not require an API key for non-commercial use
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    def get_current_weather(
        self, lat: float, lon: float
    ) -> Union[WeatherData, ErrorEntity]:
        """
        Retrieves current weather data for a given location from Open-Meteo.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
        }
        try:
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            if "current_weather" not in data:
                return ErrorEntity(
                    code="PARSE_ERROR",
                    message="Failed to parse weather data: 'current_weather' missing",
                )

            current_weather = data["current_weather"]
            
            # Mapping WMO Weather interpretation codes to description
            # Simplified mapping for demonstration
            wmo_code = current_weather.get("weathercode", 0)
            description = self._get_wmo_description(wmo_code)

            weather_data = WeatherData(
                city="Unknown Location", # OpenMeteo doesn't provide city name
                temperature=current_weather["temperature"],
                description=description,
                humidity=None, # Current weather endpoint might not provide humidity in the simple block
                wind_speed=current_weather["windspeed"],
            )
            return weather_data

        except requests.exceptions.RequestException as req_err:
            return ErrorEntity(
                code="REQUEST_ERROR",
                message=f"Weather request failed: {req_err}",
            )
    
    def _get_wmo_description(self, code: int) -> str:
        """Helper to map WMO codes to text."""
        # https://open-meteo.com/en/docs
        if code == 0: return "Clear sky"
        if code in [1, 2, 3]: return "Mainly clear, partly cloudy, and overcast"
        if code in [45, 48]: return "Fog and depositing rime fog"
        if code in [51, 53, 55]: return "Drizzle: Light, moderate, and dense intensity"
        if code in [61, 63, 65]: return "Rain: Slight, moderate and heavy intensity"
        if code in [71, 73, 75]: return "Snow fall: Slight, moderate, and heavy intensity"
        if code in [95, 96, 99]: return "Thunderstorm"
        return "Unknown weather code"