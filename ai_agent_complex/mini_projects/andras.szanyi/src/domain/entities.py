from pydantic import BaseModel
from typing import Optional


class Coordinates(BaseModel):
    """
    Represents geographic coordinates.
    """

    lat: float
    lon: float


class WeatherData(BaseModel):
    """
    Represents standardized weather information.
    """

    city: str
    temperature: float
    description: str
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None


class ErrorEntity(BaseModel):
    """
    Represents a standardized error response.
    """

    code: str
    message: str
