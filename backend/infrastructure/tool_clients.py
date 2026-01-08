"""
Infrastructure layer - External API client implementations.
Following SOLID: Single Responsibility - each client handles one external service.
Open/Closed Principle - easy to add new tool clients without modifying existing ones.
"""
import httpx
from typing import Dict, Any, Optional
from domain.interfaces import (
    IWeatherClient, IGeocodeClient, IIPGeolocationClient, 
    IFXRatesClient, ICryptoPriceClient, IMCPClient, IMCPWeatherClient
)
import logging

logger = logging.getLogger(__name__)


class OpenMeteoWeatherClient(IWeatherClient):
    """Open-Meteo weather API client."""
    
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    
    def __init__(self, geocode_client: IGeocodeClient):
        self.geocode_client = geocode_client
    
    async def get_forecast(self, city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """Get weather forecast."""
        try:
            # If city is provided, geocode it first
            if city and (lat is None or lon is None):
                geo_result = await self.geocode_client.geocode(city)
                if "error" in geo_result:
                    return geo_result
                lat = geo_result["latitude"]
                lon = geo_result["longitude"]
            
            if lat is None or lon is None:
                return {"error": "Either city or coordinates must be provided"}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,weathercode",
                        "hourly": "temperature_2m,weathercode",
                        "forecast_days": 2
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"Fetched weather for coords ({lat}, {lon})")
                
                return {
                    "location": {"latitude": lat, "longitude": lon},
                    "current_temperature": data["current"]["temperature_2m"],
                    "hourly_forecast": data["hourly"],
                    "units": data.get("hourly_units", {})
                }
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return {"error": str(e)}
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        return await self.get_forecast(**kwargs)


class NominatimGeocodeClient(IGeocodeClient):
    """OpenStreetMap Nominatim geocoding client."""
    
    GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
    REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
    
    async def geocode(self, address: str) -> Dict[str, Any]:
        """Convert address to coordinates."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.GEOCODE_URL,
                    params={"q": address, "format": "json", "limit": 1},
                    headers={"User-Agent": "AI-Agent-Demo/1.0"}
                )
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    return {"error": f"Location not found: {address}"}
                
                result = data[0]
                logger.info(f"Geocoded '{address}' to ({result['lat']}, {result['lon']})")
                
                return {
                    "latitude": float(result["lat"]),
                    "longitude": float(result["lon"]),
                    "display_name": result["display_name"]
                }
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return {"error": str(e)}
    
    async def reverse_geocode(self, lat: float, lon: float) -> Dict[str, Any]:
        """Convert coordinates to address."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.REVERSE_URL,
                    params={"lat": lat, "lon": lon, "format": "json"},
                    headers={"User-Agent": "AI-Agent-Demo/1.0"}
                )
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"Reverse geocoded ({lat}, {lon})")
                
                return {
                    "display_name": data["display_name"],
                    "address": data.get("address", {})
                }
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return {"error": str(e)}
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        if "address" in kwargs:
            return await self.geocode(kwargs["address"])
        elif "lat" in kwargs and "lon" in kwargs:
            return await self.reverse_geocode(kwargs["lat"], kwargs["lon"])
        return {"error": "Either address or lat/lon required"}


class IPAPIGeolocationClient(IIPGeolocationClient):
    """ipapi.co IP geolocation client."""
    
    BASE_URL = "https://ipapi.co"
    
    async def get_location(self, ip_address: str) -> Dict[str, Any]:
        """Get location from IP address."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.BASE_URL}/{ip_address}/json/")
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    return {"error": data["reason"]}
                
                logger.info(f"Resolved IP {ip_address} to {data.get('city')}, {data.get('country_name')}")
                
                return {
                    "ip": ip_address,
                    "city": data.get("city"),
                    "region": data.get("region"),
                    "country": data.get("country_name"),
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude")
                }
        except Exception as e:
            logger.error(f"IP geolocation error: {e}")
            return {"error": str(e)}
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        return await self.get_location(kwargs.get("ip_address", ""))


class ExchangeRateHostClient(IFXRatesClient):
    """ExchangeRate.host API client - using frankfurter.app (free, no API key needed)."""
    
    BASE_URL = "https://api.frankfurter.app"
    
    async def get_rate(self, base: str, target: str, date: Optional[str] = None) -> Dict[str, Any]:
        """Get exchange rate."""
        try:
            # Frankfurter uses date in URL path or 'latest'
            endpoint = f"{self.BASE_URL}/{date if date else 'latest'}"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    endpoint,
                    params={"from": base, "to": target}
                )
                response.raise_for_status()
                data = response.json()
                
                # Check if we got a valid response
                if "rates" not in data or target not in data["rates"]:
                    return {"error": f"Exchange rate not available for {base} to {target}"}
                
                rate = data["rates"][target]
                logger.info(f"FX rate: 1 {base} = {rate} {target}")
                
                return {
                    "base": base,
                    "target": target,
                    "rate": rate,
                    "date": data.get("date")
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"FX rate HTTP error: {e}")
            return {"error": f"Currency not supported: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"FX rate error: {e}")
            return {"error": str(e)}
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        return await self.get_rate(
            kwargs.get("base", "EUR"),
            kwargs.get("target", "USD"),
            kwargs.get("date")
        )


class CoinGeckoCryptoClient(ICryptoPriceClient):
    """CoinGecko cryptocurrency price client."""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    async def get_price(self, symbol: str, fiat: str = "USD") -> Dict[str, Any]:
        """Get crypto price."""
        try:
            # Convert symbol to CoinGecko ID (simplified mapping)
            coin_map = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "USDT": "tether",
                "BNB": "binancecoin",
                "SOL": "solana",
                "ADA": "cardano",
                "XRP": "ripple",
                "DOT": "polkadot"
            }
            coin_id = coin_map.get(symbol.upper(), symbol.lower())
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/simple/price",
                    params={
                        "ids": coin_id,
                        "vs_currencies": fiat.lower(),
                        "include_24hr_change": "true"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if coin_id not in data:
                    return {"error": f"Cryptocurrency {symbol} not found"}
                
                price = data[coin_id][fiat.lower()]
                change_24h = data[coin_id].get(f"{fiat.lower()}_24h_change", 0)
                
                logger.info(f"Crypto price: {symbol} = {price} {fiat}")
                
                return {
                    "symbol": symbol,
                    "fiat": fiat,
                    "price": price,
                    "change_24h": round(change_24h, 2)
                }
        except Exception as e:
            logger.error(f"Crypto price error: {e}")
            return {"error": str(e)}
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        return await self.get_price(
            kwargs.get("symbol", "BTC"),
            kwargs.get("fiat", "USD")
        )


class MCPClient(IMCPClient):
    """
    Base MCP (Model Context Protocol) client implementation.
    Connects to HTTP-based MCP servers via REST API.
    Supports both DeepWiki and AlphaVantage MCP servers.
    """
    
    def __init__(self):
        self.server_url: Optional[str] = None
        self.connected: bool = False
        
    async def connect(self, server_url: str) -> None:
        """Connect to HTTP-based MCP server."""
        try:
            self.server_url = server_url
            
            # For HTTP-based MCP servers, just verify the URL is valid
            # and test connectivity with a simple request
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try to list tools as a connectivity test
                try:
                    response = await client.post(
                        f"{server_url}/list_tools",
                        json={}
                    )
                    if response.status_code == 200:
                        self.connected = True
                        logger.info(f"Connected to MCP server: {server_url}")
                    else:
                        logger.warning(f"MCP server responded with status {response.status_code}")
                        self.connected = True  # Still mark as connected to try operations
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP error during connection test: {e}")
                    self.connected = True  # Still mark as connected
                except Exception as e:
                    logger.warning(f"Connection test failed: {e}, marking as connected anyway")
                    self.connected = True  # Optimistically mark as connected
                    
        except Exception as e:
            logger.error(f"MCP connection error: {e}")
            self.connected = False
            raise
    
    async def list_tools(self) -> list:
        """List all available tools from the MCP server via HTTP."""
        if not self.connected:
            raise ConnectionError("MCP client not connected to server")
        
        try:
            logger.info("Listing tools from MCP server")
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.server_url}/list_tools",
                    json={}
                )
                response.raise_for_status()
                result = response.json()
                
                # Handle different response formats
                tools = result.get('tools', []) if isinstance(result, dict) else []
                logger.info(f"Found {len(tools)} tools from MCP server")
                
                return [{
                    "name": tool.get('name', ''),
                    "description": tool.get('description', ''),
                    "inputSchema": tool.get('inputSchema', {})
            } for tool in tools]
        except Exception as e:
            logger.error(f"MCP list_tools error: {e}")
            raise
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server via HTTP."""
        if not self.connected:
            raise ConnectionError("MCP client not connected to server")
        
        try:
            logger.info(f"MCP tool call: {name} with args {arguments}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.server_url}/call_tool",
                    json={"name": name, "arguments": arguments}
                )
                response.raise_for_status()
                result = response.json()
                return result.get('content', result)
        except Exception as e:
            logger.error(f"MCP tool call error: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self.connected:
            try:
                self.connected = False
                logger.info(f"Disconnected from MCP server: {self.server_url}")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")


class MCPWeatherClient(IMCPWeatherClient):
    """
    # DeepWiki knowledge retrieval through the MCP protocol.
    # Tools: ask_question, read_wiki_structure
    # Server: https://mcp.deepwiki.com/mcp
    
    MCP-based DeepWiki service client.
    Retrieves knowledge from DeepWiki through MCP protocol.
    """
    
    MCP_SERVER_URL = "https://mcp.deepwiki.com/mcp"
    TOOL_NAME = "ask_question"
    
    def __init__(self, geocode_client: IGeocodeClient, mcp_client: Optional[IMCPClient] = None):
        self.geocode_client = geocode_client
        self.mcp_client = mcp_client or MCPClient()
        self._connected = False
    
    async def _ensure_connected(self) -> None:
        """Ensure MCP client is connected to the deepwiki server."""
        if not self._connected:
            try:
                await self.mcp_client.connect(self.MCP_SERVER_URL)
                self._connected = True
            except Exception as e:
                logger.error(f"Failed to connect to MCP DeepWiki server: {e}")
                raise ConnectionError(f"MCP DeepWiki server not reachable: {e}")
    
    async def get_forecast(self, city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> Dict[str, Any]:
        """
        Get information via DeepWiki MCP protocol.
        
        Handles:
        - MCP server not reachable
        - Tool not available
        - Invalid arguments
        """
        try:
            # If city is provided, geocode it first
            if city and (lat is None or lon is None):
                logger.info(f"Geocoding city for DeepWiki location query: {city}")
                geo_result = await self.geocode_client.geocode(city)
                if "error" in geo_result:
                    logger.error(f"DeepWiki geocoding failed: {geo_result['error']}")
                    return geo_result
                lat = geo_result["latitude"]
                lon = geo_result["longitude"]
            
            if lat is None or lon is None:
                error_msg = "Either city or coordinates must be provided"
                logger.error(f"DeepWiki invalid arguments: {error_msg}")
                return {"error": error_msg}
            
            # Ensure MCP connection
            try:
                await self._ensure_connected()
            except ConnectionError as e:
                return {"error": f"MCP server not reachable: {str(e)}"}
            
            # Call MCP deepwiki tool - ask about weather information from knowledge base
            try:
                query = f"What is the weather like at coordinates {lat}, {lon}" if not city else f"What is the weather like in {city}"
                logger.info(f"Calling DeepWiki MCP Tool with query: {query}")
                result = await self.mcp_client.call_tool(
                    name=self.TOOL_NAME,
                    arguments={"question": query}
                )
                
                # Transform MCP result to expected format
                logger.info(f"DeepWiki MCP Tool returned data")
                return {
                    "location": {"latitude": lat, "longitude": lon},
                    "current_temperature": result.get("answer", "N/A"),
                    "hourly_forecast": {},
                    "units": {},
                    "deepwiki_answer": result.get("answer", "No information available")
                }
                
            except NotImplementedError as e:
                # Tool not available or not implemented
                logger.error(f"DeepWiki Tool not available: {e}")
                return {"error": f"DeepWiki tool not available: {str(e)}"}
            except KeyError as e:
                # Invalid response format
                logger.error(f"DeepWiki Tool invalid response: {e}")
                return {"error": f"Invalid arguments or response from DeepWiki tool: {str(e)}"}
            except Exception as e:
                # General tool execution error
                logger.error(f"DeepWiki Tool execution error: {e}")
                return {"error": f"DeepWiki tool error: {str(e)}"}
                
        except Exception as e:
            logger.error(f"DeepWiki Tool error: {e}")
            return {"error": str(e)}
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute weather forecast via MCP."""
        return await self.get_forecast(**kwargs)
