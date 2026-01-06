"""LLM service using Groq API."""

import httpx
import logging
from typing import Optional

from app.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Groq API."""
    
    def __init__(
        self,
        api_key: str = GROQ_API_KEY,
        model: str = GROQ_MODEL,
        timeout: float = 60.0
    ):
        """
        Initialize the LLM service.
        
        Args:
            api_key: Groq API key
            model: Model name to use
            timeout: Request timeout in seconds
        """
        if not api_key:
            raise ValueError("GROQ_API_KEY must be set in environment variables")
        
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
        self.client = httpx.AsyncClient(timeout=timeout)
        logger.info(f"Initialized Groq LLM service with model={model}")
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            system_prompt: System prompt to set context
            user_prompt: User prompt/question
            temperature: Sampling temperature (default: 0.2)
            max_tokens: Maximum tokens to generate (default: 1024)
            
        Returns:
            Generated text response
            
        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            logger.debug(f"Calling Groq API with user_prompt: {user_prompt[:100]}...")
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content:
                raise ValueError("Groq API returned empty response")
            
            logger.debug(f"Groq API response: {content[:100]}...")
            return content
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to generate response from Groq API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
