"""
Service layer - LangGraph agent tools using LangChain @tool decorator.
These are LangChain-compatible tools for use with ToolNode.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from langchain_core.tools import tool

from domain.interfaces import (
    IWeatherClient, IGeocodeClient, IIPGeolocationClient,
    IFXRatesClient, ICryptoPriceClient, IConversationRepository
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


def initialize_tools(
    weather_client: IWeatherClient,
    geocode_client: IGeocodeClient,
    ip_client: IIPGeolocationClient,
    fx_client: IFXRatesClient,
    crypto_client: ICryptoPriceClient,
    conversation_repo: IConversationRepository,
    file_data_dir: str = "data/files"
):
    """Initialize tool dependencies."""
    global _weather_client, _geocode_client, _ip_client, _fx_client, _crypto_client, _conversation_repo, _file_data_dir
    _weather_client = weather_client
    _geocode_client = geocode_client
    _ip_client = ip_client
    _fx_client = fx_client
    _crypto_client = crypto_client
    _conversation_repo = conversation_repo
    _file_data_dir = file_data_dir


@tool
async def get_weather(city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> str:
    """Get weather forecast for a city or coordinates. Use when user asks about weather, temperature, or forecast.
    
    Args:
        city: City name to get weather for
        lat: Latitude coordinate (alternative to city)
        lon: Longitude coordinate (alternative to city)
        
    Returns:
        Weather forecast summary with current temperature and tomorrow's forecast
    """
    logger.info(f"MCP Weather Tool called: city={city}, lat={lat}, lon={lon}")
    if _weather_client is None:
        return "MCP Weather Tool service not available"
        
    result = await _weather_client.get_forecast(city=city, lat=lat, lon=lon)
    
    if "error" not in result:
        current_temp = result.get("current_temperature", "N/A")
        hourly = result.get("hourly_forecast", {})
        
        # Extract tomorrow's data
        tomorrow_temps = hourly.get("temperature_2m", [])[24:48] if len(hourly.get("temperature_2m", [])) > 24 else []
        if tomorrow_temps:
            tomorrow_avg = sum(tomorrow_temps) / len(tomorrow_temps)
            tomorrow_min = min(tomorrow_temps)
            tomorrow_max = max(tomorrow_temps)
            summary = f"Current temperature: {current_temp}°C. Tomorrow's forecast: Min {tomorrow_min:.1f}°C, Max {tomorrow_max:.1f}°C, Avg {tomorrow_avg:.1f}°C."
        else:
            summary = f"Current temperature: {current_temp}°C."
        return summary
    else:
        return f"Failed to fetch weather via MCP Weather Tool: {result['error']}"


@tool
async def geocode_location(address: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> str:
    """Convert address to coordinates or coordinates to address. Use for location lookups.
    
    Args:
        address: Address or place name to geocode
        lat: Latitude for reverse geocoding
        lon: Longitude for reverse geocoding
        
    Returns:
        Location information with coordinates or address
    """
    logger.info(f"Geocode tool called: address={address}, lat={lat}, lon={lon}")
    if _geocode_client is None:
        return "Geocoding service not available"
        
    if address:
        result = await _geocode_client.geocode(address)
    elif lat is not None and lon is not None:
        result = await _geocode_client.reverse_geocode(lat, lon)
    else:
        return "Either address or coordinates required"
    
    if "error" not in result:
        return f"Location: {result.get('display_name', 'Unknown')}, Coordinates: ({result.get('latitude')}, {result.get('longitude')})"
    else:
        return f"Geocoding failed: {result['error']}"


@tool
async def get_ip_location(ip_address: str) -> str:
    """Get geographic location from IP address. Use when user provides or asks about IP addresses.
    
    Args:
        ip_address: IP address to lookup
        
    Returns:
        Geographic location information for the IP
    """
    logger.info(f"IP geolocation tool called: ip={ip_address}")
    if _ip_client is None:
        return "IP geolocation service not available"
        
    result = await _ip_client.get_location(ip_address)
    
    if "error" not in result:
        location_str = f"{result.get('city', 'Unknown')}, {result.get('country', 'Unknown')}"
        return f"IP {ip_address} is located in {location_str} (Coordinates: {result.get('latitude')}, {result.get('longitude')})"
    else:
        return f"IP geolocation failed: {result['error']}"


@tool
async def get_exchange_rate(base: str, target: str, date: Optional[str] = None) -> str:
    """Get foreign exchange rates between currencies. Use for currency conversion questions.
    
    Args:
        base: Base currency code (e.g., USD, EUR)
        target: Target currency code (e.g., GBP, JPY)
        date: Optional date in YYYY-MM-DD format for historical rates
        
    Returns:
        Exchange rate information
    """
    logger.info(f"FX rates tool called: {base} -> {target}, date={date}")
    if _fx_client is None:
        return "FX rates service not available"
        
    result = await _fx_client.get_rate(base, target, date)
    
    if "error" not in result:
        rate = result.get("rate")
        return f"1 {base} equals {rate} {target} (as of {result.get('date')})"
    else:
        return f"FX rate lookup failed: {result['error']}"


@tool
async def get_crypto_price(symbol: str, fiat: str = "USD") -> str:
    """Get current cryptocurrency prices. Use when user asks about Bitcoin, Ethereum, or other crypto prices.
    
    Args:
        symbol: Cryptocurrency symbol (e.g., BTC, ETH, DOGE)
        fiat: Fiat currency to price in (default: USD)
        
    Returns:
        Current price and 24h change information
    """
    logger.info(f"Crypto price tool called: {symbol} in {fiat}")
    if _crypto_client is None:
        return "Crypto price service not available"
        
    result = await _crypto_client.get_price(symbol, fiat)
    
    if "error" not in result:
        price = result.get("price")
        change = result.get("change_24h", 0)
        return f"{symbol} price is {price} {fiat} with a 24h change of {change:+.2f}%"
    else:
        return f"Crypto price lookup failed: {result['error']}"


@tool
async def create_file(filename: str, content: str, user_id: str = "default") -> str:
    """Save text content to a file. Use when user wants to save notes, plans, or documents.
    
    Args:
        filename: Name of the file to create
        content: Text content to save
        user_id: User identifier (injected by system)
        
    Returns:
        Confirmation message with file path
    """
    logger.info(f"File creation tool called: user={user_id}, filename={filename}")
    
    try:
        data_dir = Path(_file_data_dir)
        user_dir = data_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = user_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Saved content to {file_path} ({len(content)} characters)"
    except Exception as e:
        logger.error(f"File creation error: {e}")
        return f"Failed to create file: {e}"


@tool
async def search_history(query: str) -> str:
    """Search through past conversation history. Use when user asks to remember or find previous discussions.
    
    Args:
        query: Search query text
        
    Returns:
        Summary of matching conversation snippets
    """
    logger.info(f"History search tool called: query='{query}'")
    if _conversation_repo is None:
        return "History search not available"
        
    try:
        results = await _conversation_repo.search_messages(query)
        
        if not results:
            return f"No messages found matching '{query}'"
        
        # Format top 5 results
        formatted = []
        for r in results[:5]:
            formatted.append(f"[{r.timestamp.strftime('%Y-%m-%d %H:%M')}] {r.role}: {r.snippet}")
        
        return f"Found {len(results)} messages matching '{query}':\n" + "\n".join(formatted)
    except Exception as e:
        logger.error(f"History search error: {e}")
        return f"History search failed: {e}"


def get_all_tools():
    """Get list of all LangChain tools."""
    return [
        get_weather,
        geocode_location,
        get_ip_location,
        get_exchange_rate,
        get_crypto_price,
        create_file,
        search_history
    ]
