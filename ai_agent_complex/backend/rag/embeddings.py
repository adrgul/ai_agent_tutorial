"""
Embedding service for RAG using OpenAI text-embedding-3-small.

Provides abstraction layer for embedding generation with:
- Batch processing
- Retry logic
- Error handling
- Interface for future embedding providers
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import List
import openai
from openai import OpenAI

from .config import EmbeddingConfig

logger = logging.getLogger(__name__)


class IEmbeddingService(ABC):
    """Interface for embedding services."""

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each vector is List[float])
        """
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a single query.

        Args:
            query: Query text to embed

        Returns:
            Embedding vector as List[float]
        """
        pass


class OpenAIEmbeddingService(IEmbeddingService):
    """
    OpenAI embedding service using text-embedding-3-small.

    Features:
    - 1536 dimensions
    - Batch processing up to 100 texts per API call
    - Exponential backoff retry logic
    - Cost-effective and fast
    """

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.client = OpenAI(api_key=config.api_key)
        self.model = config.model_name

        logger.info(f"Initialized OpenAI embedding service with model: {self.model}")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batching.

        Processes texts in batches to respect API limits.
        """
        if not texts:
            return []

        all_embeddings = []
        batch_size = self.config.batch_size

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await self._embed_batch(batch)
            all_embeddings.extend(batch_embeddings)

        logger.info(f"Generated {len(all_embeddings)} embeddings")
        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for single query."""
        embeddings = await self.embed_texts([query])
        return embeddings[0] if embeddings else []

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts with retry logic.

        Implements exponential backoff for rate limiting.
        """
        for attempt in range(self.config.max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                    timeout=self.config.timeout_seconds
                )

                # Extract embeddings in order
                embeddings = [item.embedding for item in response.data]

                logger.debug(f"Successfully embedded batch of {len(texts)} texts")
                return embeddings

            except openai.RateLimitError as e:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(
                    f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{self.config.max_retries})"
                )
                if attempt < self.config.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    logger.error(f"Max retries reached for embedding batch")
                    raise

            except openai.APIError as e:
                logger.error(f"OpenAI API error: {e}")
                if attempt < self.config.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                else:
                    raise

            except Exception as e:
                logger.error(f"Unexpected error in embedding: {e}")
                raise

        return []


class MockEmbeddingService(IEmbeddingService):
    """
    Mock embedding service for testing.

    Returns random vectors of correct dimension.
    """

    def __init__(self, embedding_dim: int = 1536):
        self.embedding_dim = embedding_dim
        logger.info("Initialized mock embedding service (for testing only)")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Return mock embeddings."""
        import random
        return [[random.random() for _ in range(self.embedding_dim)] for _ in texts]

    async def embed_query(self, query: str) -> List[float]:
        """Return mock embedding."""
        import random
        return [random.random() for _ in range(self.embedding_dim)]
