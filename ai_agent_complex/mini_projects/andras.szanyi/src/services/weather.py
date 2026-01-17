from typing import Union

from src.domain.entities import ErrorEntity, WeatherData
from src.domain.interfaces import GeoLocationProviderProtocol, WeatherProviderProtocol


class WeatherForecaster:
    """
    Service for fetching and processing weather-related information.
    This layer contains deterministic business logic and does not make LLM calls.
    """

    def __init__(
        self,
        weather_provider: WeatherProviderProtocol,
        geo_locator: GeoLocationProviderProtocol,
    ):
        self.weather_provider = weather_provider
        self.geo_locator = geo_locator

    def get_current_weather_report(self, city: str) -> Union[WeatherData, ErrorEntity]:
        """
        Retrieves a current weather report for a given city.
        First resolves the city to coordinates, then fetches weather.
        """
        # 1. Get Coordinates
        coords_result = self.geo_locator.get_coordinates(city)
        if isinstance(coords_result, ErrorEntity):
            return coords_result

        # 2. Get Weather
        weather_result = self.weather_provider.get_current_weather(
            lat=coords_result.lat, lon=coords_result.lon
        )
        
        if isinstance(weather_result, WeatherData):
            # 3. Enrich with City Name (since OpenMeteo doesn't provide it)
            weather_result.city = city
            
        return weather_result