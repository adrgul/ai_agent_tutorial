"""
Embedding service implementations.

Single Responsibility: This module is responsible for generating
embeddings using external APIs.
"""

import json
from typing import List
import requests

from app.interfaces import EmbeddingService


class OpenAIEmbeddingService(EmbeddingService):
    """
    Concrete implementation of EmbeddingService using OpenAI's API.
    
    Follows Liskov Substitution Principle: can be used anywhere an
    EmbeddingService is expected without breaking behavior.
    
    Uses raw HTTP requests instead of the OpenAI library to demonstrate
    the underlying API mechanics.
    """
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """
        Initialize the OpenAI embedding service.
        
        Args:
            api_key: OpenAI API key.
            model: Name of the embedding model to use.
        """
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.openai.com/v1/embeddings"
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding using OpenAI's API via raw HTTP request.
        
        This method demonstrates the underlying API mechanics:
        1. Constructs the HTTP headers with authentication
        2. Builds the JSON payload with model and input text
        3. Makes a POST request to OpenAI's embeddings endpoint
        4. Parses the JSON response to extract the embedding vector
        
        Args:
            text: The input text to embed.
            
        Returns:
            A list of floats representing the embedding vector.
            
        Raises:
            Exception: If the API call fails (error is logged and re-raised).
        """
        try:
            # Prepare HTTP headers
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Prepare request payload
            payload = {
                "input": text,
                "model": self.model
            }
            
            print(f"  → Making API request to: {self.api_url}")
            print(f"  → Model: {self.model}")
            print(f"  → Input text length: {len(text)} characters")
            
            # Make the HTTP POST request
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            response_data = response.json()
            
            # Extract embedding from response structure
            # Response format: {"data": [{"embedding": [...], "index": 0}], "model": "...", "usage": {...}}
            embedding = response_data["data"][0]["embedding"]
            
            print(f"  ✓ Received embedding vector of dimension: {len(embedding)}")
            print(f"  ✓ Token usage: {response_data.get('usage', {})}")
            
            return embedding
            
        except requests.exceptions.RequestException as e:
            print(f"Error generating embedding (HTTP request failed): {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            raise
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Error parsing API response: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error generating embedding: {e}")
            raise
