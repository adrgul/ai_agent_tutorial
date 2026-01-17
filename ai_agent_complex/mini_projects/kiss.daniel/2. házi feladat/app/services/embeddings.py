"""Embedding service using sentence-transformers."""

import logging
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence-transformers model to use
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self._dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding model loaded, dimension: {self._dimension}")
    
    @property
    def dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.
        
        Returns:
            Embedding vector dimension
        """
        return self._dimension
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Normalized embedding vector as list of floats
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self._dimension
        
        # Generate embedding
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,  # Cosine normalization
            convert_to_numpy=True
        )
        
        return embedding.tolist()
    
    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for multiple texts.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of normalized embedding vectors
        """
        if not texts:
            logger.warning("Empty text list provided for embeddings")
            return []
        
        # Filter out empty texts but maintain indices
        non_empty_indices = [i for i, text in enumerate(texts) if text and text.strip()]
        non_empty_texts = [texts[i] for i in non_empty_indices]
        
        if not non_empty_texts:
            logger.warning("All texts are empty")
            return [[0.0] * self._dimension] * len(texts)
        
        # Generate embeddings
        embeddings = self.model.encode(
            non_empty_texts,
            normalize_embeddings=True,  # Cosine normalization
            convert_to_numpy=True,
            show_progress_bar=False
        )
        
        # Reconstruct full list with empty embeddings where needed
        result = []
        non_empty_idx = 0
        for i in range(len(texts)):
            if i in non_empty_indices:
                result.append(embeddings[non_empty_idx].tolist())
                non_empty_idx += 1
            else:
                result.append([0.0] * self._dimension)
        
        logger.debug(f"Generated {len(result)} embeddings")
        return result
