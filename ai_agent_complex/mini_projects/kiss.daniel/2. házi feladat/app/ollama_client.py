"""Ollama client for generating text embeddings."""

import httpx
from typing import List
import logging

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama's embedding API."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        """
        Initialize the Ollama client.
        
        Args:
            base_url: Base URL for the Ollama API
            model: Name of the embedding model to use
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)
        logger.info(f"Initialized Ollama client with base_url={base_url}, model={model}")
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            httpx.HTTPError: If the request to Ollama fails
        """
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            embedding = result.get("embedding", [])
            
            if not embedding:
                raise ValueError("Ollama returned empty embedding")
            
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get embedding from Ollama: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting embedding: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
