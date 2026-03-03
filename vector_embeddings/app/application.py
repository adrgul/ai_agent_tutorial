"""
Application orchestrator.

Single Responsibility: Coordinates the embedding and vector store
components to process user queries.

Follows Dependency Inversion Principle: depends on abstractions
(EmbeddingService, VectorStore) not concrete implementations.
"""

import uuid
from typing import List, Tuple, Dict

from app.interfaces import EmbeddingService, VectorStore


class EmbeddingApp:
    """
    High-level application logic for processing text queries.
    
    This class orchestrates the workflow of:
    1. Generating embeddings
    2. Storing them in a vector database
    3. Retrieving similar entries
    
    Follows Open/Closed Principle: open for extension (can use any
    EmbeddingService or VectorStore implementation) but closed for
    modification (the workflow logic remains stable).
    """
    
    def __init__(
        self, 
        embedding_service: EmbeddingService, 
        vector_store: VectorStore
    ):
        """
        Initialize the application with injected dependencies.
        
        Args:
            embedding_service: Service for generating embeddings.
            vector_store: Store for persisting and searching embeddings.
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
    
    def process_query(
        self, 
        text: str, 
        k: int = 3
    ) -> Tuple[str, Dict[str, List]]:
        """
        Process a user query: embed, store, and search using both methods.
        
        Args:
            text: The user's input text.
            k: Number of nearest neighbors to retrieve.
            
        Returns:
            Tuple of (generated_id, search_results) where search_results
            is a dict with 'cosine' and 'knn' keys containing their respective results.
        """
        # Generate unique ID for this query
        query_id = str(uuid.uuid4())
        
        # Generate embedding
        embedding = self.embedding_service.get_embedding(text)
        
        # Store in vector database
        self.vector_store.add(query_id, text, embedding)
        
        # Search for similar entries using both methods
        cosine_results = self.vector_store.similarity_search(embedding, k=k)
        knn_results = self.vector_store.knn_search(embedding, k=k)
        
        results = {
            'cosine': cosine_results,
            'knn': knn_results
        }
        
        return query_id, results
