from typing import Callable, Union
import json
from langchain_core.prompts import PromptTemplate

from src.domain.state import AgentState
from src.domain.entities import ErrorEntity
from src.services.weather import WeatherForecaster


class AgentNodes:
    """
    Contains the nodes (functions) that the LangGraph graph will call.
    These nodes interact with services and the LLM.
    """

    def __init__(
        self,
        weather_forecaster: WeatherForecaster,
        llm_invoke: Callable,
    ):
        self.weather_forecaster = weather_forecaster
        self.llm_invoke = llm_invoke

    def call_llm(self, state: AgentState) -> AgentState:
        """
        Invokes the LLM with the current input and returns the response.
        """
        print("---CALLING LLM---")
        response_content = self.llm_invoke(state["input"])
        return {"response": response_content}

    def get_weather_info(self, state: AgentState) -> AgentState:
        """
        Extracts city from the input and uses the weather forecaster to get weather info.
        """
        print("---GETTING WEATHER INFO---")
        # In a real scenario, you'd parse the city from the input using an LLM tool or regex
        # For simplicity, let's assume the input directly contains the city name for now.
        city = state["input"].split("in")[-1].strip().replace("?", "")

        weather_result = self.weather_forecaster.get_current_weather_report(city)

        if isinstance(weather_result, ErrorEntity):
            tool_output = f"Error: {weather_result.message}"
        else:
            tool_output = (
                f"The current temperature in {weather_result.city} is "
                f"{weather_result.temperature}°C with {weather_result.description}. "
                f"Humidity: {weather_result.humidity}%, Wind Speed: {weather_result.wind_speed} m/s."
            )
        return {"tool_output": tool_output, "intermediate_steps": [tool_output]}

    def decide_next_step(self, state: AgentState) -> str:
        """
        Decides whether to call a tool or directly respond based on the input.
        This uses an LLM to classify the intent.
        """
        print("---DECIDING NEXT STEP WITH LLM---")
        prompt = PromptTemplate.from_template(
            """Given the user query, decide whether to:
            1. Call the weather tool to get current weather information.
            2. Respond directly using the LLM.

            Return your decision as a JSON object with a single key 'action' and one of the following values: 'weather' or 'llm'.

            User query: {query}
            JSON:"""
        )
        chain = prompt | self.llm_invoke
        response = chain.invoke({"query": state["input"]})

        try:
            decision = json.loads(response)["action"]
            if decision == "weather":
                return "call_tool_weather"
            else:
                return "end_response"
        except json.JSONDecodeError:
            print(f"Warning: LLM returned invalid JSON for decision: {response}. Defaulting to LLM.")
            return "end_response"
        except KeyError:
            print(f"Warning: LLM returned JSON without 'action' key: {response}. Defaulting to LLM.")
            return "end_response"
