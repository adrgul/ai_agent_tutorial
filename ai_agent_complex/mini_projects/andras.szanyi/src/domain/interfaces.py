from abc import ABC, abstractmethod
from typing import Protocol, Union

from src.domain.entities import Coordinates, ErrorEntity, WeatherData


class GeoLocationProviderProtocol(Protocol):
    """
    Defines the interface for a geolocation provider.
    """

    @abstractmethod
    def get_coordinates(self, city: str) -> Union[Coordinates, ErrorEntity]:
        """
        Retrieves coordinates for a given city.
        """
        ...


class WeatherProviderProtocol(Protocol):
    """
    Defines the interface for a weather data provider.
    """

    @abstractmethod
    def get_current_weather(
        self, lat: float, lon: float
    ) -> Union[WeatherData, ErrorEntity]:
        """
        Retrieves current weather data for a given location.
        """
        ...


class LLMClientProtocol(Protocol):
    """
    Defines the interface for an LLM client.
    """

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """
        Invokes the LLM with a given prompt.
        """
        ...
