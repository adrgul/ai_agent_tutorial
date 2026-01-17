"""
Abstract interfaces for the embedding and vector store components.

This module defines the core abstractions following the Dependency Inversion Principle.
High-level modules depend on these abstractions, not on concrete implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple


class EmbeddingService(ABC):
    """
    Abstract interface for embedding generation services.
    
    Follows the Interface Segregation Principle by exposing only
    the minimal required functionality.
    """
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.
        
        Args:
            text: The input text to embed.
            
        Returns:
            A list of floats representing the embedding vector.
        """
        pass


class VectorStore(ABC):
    """
    Abstract interface for vector database operations.
    
    Provides a minimal, focused interface for storing and searching embeddings.
    """
    
    @abstractmethod
    def add(self, id: str, text: str, embedding: List[float]) -> None:
        """
        Add a text and its embedding to the vector store.
        
        Args:
            id: Unique identifier for this entry.
            text: The original text content.
            embedding: The embedding vector.
        """
        pass
    
    @abstractmethod
    def similarity_search(
        self, 
        embedding: List[float], 
        k: int = 3
    ) -> List[Tuple[str, float, float, str]]:
        """
        Find the k most similar entries to the given embedding.
        
        Args:
            embedding: The query embedding vector.
            k: Number of nearest neighbors to return.
            
        Returns:
            List of tuples (id, distance, similarity, text) ordered by similarity.
            Distance is the cosine distance (lower is better).
            Similarity is cosine similarity (higher is better, range 0-1).
        """
        pass
    
    @abstractmethod
    def knn_search(
        self, 
        embedding: List[float], 
        k: int = 3
    ) -> List[Tuple[str, float, str]]:
        """
        Find the k nearest neighbors using Euclidean distance.
        
        Args:
            embedding: The query embedding vector.
            k: Number of nearest neighbors to return.
            
        Returns:
            List of tuples (id, euclidean_distance, text) ordered by distance.
            Lower distance means higher similarity.
        """
        pass
