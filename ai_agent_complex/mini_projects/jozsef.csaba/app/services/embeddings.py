"""Embedding service for text vectorization.

Following SOLID principles:
- Single Responsibility: Handles only text embedding
- Dependency Inversion: Can be extended with different embedding providers
"""

from typing import List

import numpy as np
from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self, settings: Settings):
        """Initialize embedding service.

        Args:
            settings: Application settings with API keys
        """
        self.settings = settings
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key,
        )

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            Numpy array of embedding vector
        """
        embedding = self.embeddings.embed_query(text)
        return np.array(embedding)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            Numpy array of embeddings (n_texts x embedding_dim)
        """
        embeddings = self.embeddings.embed_documents(texts)
        return np.array(embeddings)

    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        # text-embedding-3-large has 1536 dimensions
        # text-embedding-3-small has 512 dimensions
        if "large" in self.settings.embedding_model:
            return 1536
        elif "small" in self.settings.embedding_model:
            return 512
        else:
            return 1536  # default
