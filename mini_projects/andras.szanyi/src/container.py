from src.infrastructure.config import AppSettings
from src.infrastructure.llm import GroqLLMClient
from src.infrastructure.external import OpenWeatherMapGeoLocator, OpenMeteoWeatherClient
from src.services.weather import WeatherForecaster
from src.application.nodes import AgentNodes
from src.application.graph import AgentGraph


class Container:
    """
    The Composition Root for wiring all application components.
    Handles dependency injection manually.
    """

    def __init__(self):
        # Configuration
        self.settings = AppSettings.load()

        # Infrastructure Layer
        self.llm_client = GroqLLMClient(settings=self.settings)
        self.geo_locator = OpenWeatherMapGeoLocator(settings=self.settings)
        self.weather_client = OpenMeteoWeatherClient()

        # Services Layer
        self.weather_forecaster = WeatherForecaster(
            weather_provider=self.weather_client,
            geo_locator=self.geo_locator
        )

        # Application Layer
        self.agent_nodes = AgentNodes(
            weather_forecaster=self.weather_forecaster,
            llm_invoke=self.llm_client.invoke,
        )
        self.agent_graph = AgentGraph(agent_nodes=self.agent_nodes).build()

    def get_agent_graph(self):
        return self.agent_graph

    def get_settings(self):
        return self.settings