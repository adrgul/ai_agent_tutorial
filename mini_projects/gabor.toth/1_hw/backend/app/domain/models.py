from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class Coordinates(BaseModel):
    lat: float
    lon: float


class DateContext(BaseModel):
    year: int
    month: int
    day: int
    weekday: str  # e.g., "Monday"


class POI(BaseModel):
    type: str  # "park", "museum", "cafe", "viewpoint", "drinking_water", "other"
    name: str
    distance_m: int
    walking_minutes: int
    lat: float
    lon: float


class Activity(BaseModel):
    name: str
    description: str
    type: str


class CityFact(BaseModel):
    title: str
    content: str


class Briefing(BaseModel):
    paragraph: str


class CityBriefingResponse(BaseModel):
    city: str
    coordinates: Coordinates
    date_context: DateContext
    recommended_activities: List[Activity]
    city_facts: List[CityFact]
    briefing: Briefing
    nearby_places: List[POI] = []
    fallback_message: Optional[str] = None
    metadata: Optional[dict] = None
