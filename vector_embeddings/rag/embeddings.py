"""
Embedding service for RAG pipeline.

Uses OpenAI embeddings API.
"""

import requests
from typing import List
from rag.config import EmbeddingConfig


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI's API.
    
    Uses raw HTTP requests to demonstrate the underlying API mechanics.
    """
    
    def __init__(self, config: EmbeddingConfig = None):
        """
        Initialize the embedding service.
        
        Args:
            config: Embedding configuration.
        """
        self.config = config or EmbeddingConfig()
        self.api_url = "https://api.openai.com/v1/embeddings"
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.
        
        Args:
            text: Text to embed.
        
        Returns:
            Embedding vector (list of floats).
        
        Raises:
            Exception: If API request fails.
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "input": text
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data["data"][0]["embedding"]
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API request failed: {e}")
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a batch.
        
        Args:
            texts: List of texts to embed.
        
        Returns:
            List of embedding vectors.
        
        Raises:
            Exception: If API request fails.
        """
        if not texts:
            return []
        
        # OpenAI API supports batch requests
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "input": texts
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            # Sort by index to maintain order
            embeddings = sorted(data["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in embeddings]
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API batch request failed: {e}")
    
    def get_dimension(self) -> int:
        """
        Get the dimension of embeddings for the current model.
        
        Returns:
            Embedding dimension.
        """
        # Known dimensions for OpenAI models
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        
        return model_dimensions.get(self.config.model, 1536)
