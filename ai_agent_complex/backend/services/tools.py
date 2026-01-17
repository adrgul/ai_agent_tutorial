"""
Service layer - LangGraph agent tools implementation using LangChain tool format.
Following SOLID: Single Responsibility - each tool wrapper has one clear purpose.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime
import logging

from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

# Observability imports
from observability.metrics import record_tool_call

from domain.interfaces import (
    IWeatherClient, IGeocodeClient, IIPGeolocationClient,
    IFXRatesClient, ICryptoPriceClient, IConversationRepository,
    IDeepWikiMCPClient
)

logger = logging.getLogger(__name__)


# Tool dependency holders (for injection)
_weather_client: Optional[IWeatherClient] = None
_geocode_client: Optional[IGeocodeClient] = None
_ip_client: Optional[IIPGeolocationClient] = None
_fx_client: Optional[IFXRatesClient] = None
_crypto_client: Optional[ICryptoPriceClient] = None
_conversation_repo: Optional[IConversationRepository] = None
_file_data_dir: str = "data/files"


class WeatherTool:
    """Weather forecast tool using MCP Weather Tool."""
    
    def __init__(self, client: IWeatherClient):
        self.client = client
        self.name = "weather"
        self.description = "Get weather forecast for a city or coordinates. Useful when user asks about weather, temperature, or forecast."
    
    async def execute(self, city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """Get weather forecast via MCP Weather Tool."""
        with record_tool_call("weather"):
            logger.info(f"MCP Weather Tool called: city={city}, lat={lat}, lon={lon}")
            result = await self.client.get_forecast(city=city, lat=lat, lon=lon)
        
        if "error" not in result:
            # Format result for agent with today and tomorrow summary
            current_temp = result.get("current_temperature", "N/A")
            hourly = result.get("hourly_forecast", {})
            
            # Extract tomorrow's data (hours 24-47 in the forecast)
            tomorrow_temps = hourly.get("temperature_2m", [])[24:48] if len(hourly.get("temperature_2m", [])) > 24 else []
            tomorrow_avg = sum(tomorrow_temps) / len(tomorrow_temps) if tomorrow_temps else None
            tomorrow_min = min(tomorrow_temps) if tomorrow_temps else None
            tomorrow_max = max(tomorrow_temps) if tomorrow_temps else None
            
            # Format summary
            summary = f"Current temperature: {current_temp}°C. "
            if tomorrow_avg:
                summary += f"Tomorrow's forecast: Min {tomorrow_min:.1f}°C, Max {tomorrow_max:.1f}°C, Avg {tomorrow_avg:.1f}°C."
            
            return {
                "success": True,
                "message": summary,
                "data": {
                    **result,
                    "tomorrow": {
                        "min_temp": tomorrow_min,
                        "max_temp": tomorrow_max,
                        "avg_temp": tomorrow_avg
                    } if tomorrow_avg else None
                },
                "system_message": f"Fetched weather forecast via MCP Weather Tool for location ({result['location']['latitude']}, {result['location']['longitude']}). {summary}"
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "system_message": f"Failed to fetch weather via MCP Weather Tool: {result['error']}"
            }


class GeocodeTool:
    """Geocoding and reverse geocoding tool."""
    
    def __init__(self, client: IGeocodeClient):
        self.client = client
        self.name = "geocode"
        self.description = "Convert address to coordinates or coordinates to address. Useful for location lookups."
    
    async def execute(self, address: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """Geocode or reverse geocode."""
        with record_tool_call("geocode"):
            logger.info(f"Geocode tool called: address={address}, lat={lat}, lon={lon}")
        
            if address:
                result = await self.client.geocode(address)
            elif lat is not None and lon is not None:
                result = await self.client.reverse_geocode(lat, lon)
            else:
                return {
                    "success": False,
                    "error": "Either address or coordinates required",
                    "system_message": "Geocoding failed: missing parameters"
                }
            
            if "error" not in result:
                return {
                    "success": True,
                    "data": result,
                    "system_message": f"Geocoded location: {result.get('display_name', 'Unknown')}"
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "system_message": f"Geocoding failed: {result['error']}"
                }


class IPGeolocationTool:
    """IP geolocation tool."""
    
    def __init__(self, client: IIPGeolocationClient):
        self.client = client
        self.name = "ip_geolocation"
        self.description = "Get geographic location from IP address. Can auto-detect user's current location if no IP provided. Useful for detecting user location."
    
    async def execute(self, ip_address: str = "") -> Dict[str, Any]:
        """Get location from IP. If ip_address is empty, auto-detects user's location."""
        logger.info(f"IP geolocation tool called: ip={ip_address or 'auto-detect'}")
        result = await self.client.get_location(ip_address)
        
        if "error" not in result:
            location_str = f"{result.get('city', 'Unknown')}, {result.get('country', 'Unknown')}"
            ip_str = result.get('ip', ip_address or 'auto-detected')
            return {
                "success": True,
                "data": result,
                "city": result.get('city'),  # Make city easily accessible for dependencies
                "country": result.get('country'),
                "latitude": result.get('latitude'),
                "longitude": result.get('longitude'),
                "system_message": f"Resolved IP {ip_str} to {location_str} (lat: {result.get('latitude')}, lon: {result.get('longitude')})"
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "system_message": f"IP geolocation failed: {result['error']}"
            }


class FXRatesTool:
    """Foreign exchange rates tool."""
    
    def __init__(self, client: IFXRatesClient):
        self.client = client
        self.name = "fx_rates"
        self.description = "Get foreign exchange rates between currencies. Useful for currency conversion questions."
    
    async def execute(self, base: str, target: str, date: Optional[str] = None) -> Dict[str, Any]:
        """Get exchange rate."""
        logger.info(f"FX rates tool called: {base} -> {target}, date={date}")
        result = await self.client.get_rate(base, target, date)
        
        if "error" not in result:
            rate = result.get("rate")
            return {
                "success": True,
                "data": result,
                "system_message": f"1 {base} equals {rate} {target} (as of {result.get('date')})"
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "system_message": f"FX rate lookup failed: {result['error']}"
            }


class CryptoPriceTool:
    """Cryptocurrency price tool."""
    
    def __init__(self, client: ICryptoPriceClient):
        self.client = client
        self.name = "crypto_price"
        self.description = "Get current cryptocurrency prices ONLY (Bitcoin, Ethereum, Dogecoin, etc.). DO NOT use for stock prices (AAPL, MSFT, GOOGL, TSLA, etc.) - use AlphaVantage tools for stocks."
    
    async def execute(self, symbol: str, fiat: str = "USD") -> Dict[str, Any]:
        """Get crypto price."""
        logger.info(f"Crypto price tool called: {symbol} in {fiat}")
        result = await self.client.get_price(symbol, fiat)
        
        if "error" not in result:
            price = result.get("price")
            change = result.get("change_24h", 0)
            return {
                "success": True,
                "data": result,
                "system_message": f"{symbol} price is {price} {fiat} with a 24h change of {change:+.2f}%"
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "system_message": f"Crypto price lookup failed: {result['error']}"
            }


class FileCreationTool:
    """File creation tool for saving user notes/documents."""
    
    def __init__(self, data_dir: str = "data/files"):
        self.data_dir = Path(data_dir)
        self.name = "create_file"
        self.description = "Save text content to a file. Useful when user wants to save notes, plans, or documents."
    
    async def execute(self, user_id: str, filename: str, content: str) -> Dict[str, Any]:
        """Create a file."""
        logger.info(f"File creation tool called: user={user_id}, filename={filename}")
        
        try:
            user_dir = self.data_dir / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = user_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "data": {"path": str(file_path), "size": len(content)},
                "system_message": f"Saved content to {file_path}"
            }
        except Exception as e:
            logger.error(f"File creation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "system_message": f"Failed to create file: {e}"
            }


class HistorySearchTool:
    """History search tool for searching past conversations."""
    
    def __init__(self, repository: IConversationRepository):
        self.repository = repository
        self.name = "search_history"
        self.description = "Search through past conversation history. Useful when user asks to remember or find previous discussions."
    
    async def execute(self, query: str) -> Dict[str, Any]:
        """Search conversation history."""
        logger.info(f"History search tool called: query='{query}'")
        
        try:
            results = await self.repository.search_messages(query)
            
            # Format results
            formatted_results = [
                {
                    "session": r.session_id,
                    "snippet": r.snippet,
                    "timestamp": r.timestamp.isoformat(),
                    "role": r.role
                }
                for r in results[:10]  # Limit to 10 results
            ]
            
            return {
                "success": True,
                "data": {"results": formatted_results, "count": len(results)},
                "system_message": f"Found {len(results)} messages matching '{query}'"
            }
        except Exception as e:
            logger.error(f"History search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "system_message": f"History search failed: {e}"
            }


class DeepWikiTool:
    """
    DeepWiki MCP tool for GitHub repository knowledge retrieval.
    
    Provides access to:
    - Repository wiki structure reading
    - Wiki page content retrieval
    - Question answering about repositories
    """
    
    def __init__(self, client: IDeepWikiMCPClient):
        self.client = client
        self.name = "deepwiki"
        self.description = (
            "Access GitHub repository wikis and ask questions about repositories. "
            "Can read wiki structure, get wiki page content, or answer questions about a repo. "
            "Useful when user asks about GitHub repositories, their documentation, or wiki content."
        )
    
    async def execute(
        self, 
        question: Optional[str] = None,
        repo_url: Optional[str] = None,
        page_title: Optional[str] = None,
        action: str = "ask_question"
    ) -> Dict[str, Any]:
        """
        Execute DeepWiki tool.
        
        Args:
            question: Question to ask about the repository
            repo_url: GitHub repository URL
            page_title: Wiki page title (for get_wiki_content action)
            action: Action to perform (ask_question, read_wiki_structure, get_wiki_content)
        """
        logger.info(f"DeepWiki tool called: action={action}, repo={repo_url}, question={question}")
        
        try:
            if action == "read_wiki_structure" and repo_url:
                result = await self.client.read_wiki_structure(repo_url)
            elif action == "get_wiki_content" and repo_url and page_title:
                result = await self.client.get_wiki_content(repo_url, page_title)
            elif action == "ask_question" and question:
                result = await self.client.ask_question(question, repo_url)
            else:
                return {
                    "success": False,
                    "error": "Invalid arguments. For 'ask_question' provide 'question', for 'read_wiki_structure' provide 'repo_url', for 'get_wiki_content' provide both 'repo_url' and 'page_title'.",
                    "system_message": "DeepWiki tool invocation failed: invalid arguments"
                }
            
            if result.get("success"):
                # Format success response
                if action == "ask_question":
                    message = f"DeepWiki answered: {result.get('answer', 'No answer')}"
                elif action == "read_wiki_structure":
                    message = f"Retrieved wiki structure for {repo_url}"
                else:
                    message = f"Retrieved wiki page '{page_title}' from {repo_url}"
                
                return {
                    "success": True,
                    "data": result,
                    "system_message": message
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "system_message": f"DeepWiki tool failed: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            logger.error(f"DeepWiki tool error: {e}")
            return {
                "success": False,
                "error": str(e),
                "system_message": f"DeepWiki tool execution error: {e}"
            }
