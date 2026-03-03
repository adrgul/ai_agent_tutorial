"""
Vector store implementations.

Single Responsibility: This module is responsible for storing and
retrieving embeddings from a vector database.
"""

from typing import List, Tuple
import chromadb
from chromadb.config import Settings

from app.interfaces import VectorStore


class ChromaVectorStore(VectorStore):
    """
    Concrete implementation of VectorStore using ChromaDB.
    
    Follows Liskov Substitution Principle: can be used anywhere a
    VectorStore is expected without breaking behavior.
    """
    
    def __init__(self, db_path: str, collection_name: str):
        """
        Initialize the ChromaDB vector store.
        
        Args:
            db_path: Path to the ChromaDB persistence directory.
            collection_name: Name of the collection to use.
        """
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        # Collection for cosine similarity
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        # Collection for Euclidean distance (k-NN)
        self.knn_collection = self.client.get_or_create_collection(
            name=f"{collection_name}_knn",
            metadata={"hnsw:space": "l2"}  # Use Euclidean distance
        )
    
    def add(self, id: str, text: str, embedding: List[float]) -> None:
        """
        Add a text and its embedding to the ChromaDB collection.
        
        Args:
            id: Unique identifier for this entry.
            text: The original text content.
            embedding: The embedding vector.
        """
        # Add to both collections
        self.collection.add(
            ids=[id],
            documents=[text],
            embeddings=[embedding]
        )
        self.knn_collection.add(
            ids=[id],
            documents=[text],
            embeddings=[embedding]
        )
    
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
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k
        )
        
        # Extract and format results
        if not results['ids'] or not results['ids'][0]:
            return []
        
        output = []
        for i in range(len(results['ids'][0])):
            doc_id = results['ids'][0][i]
            distance = results['distances'][0][i]
            # Convert cosine distance to cosine similarity
            # Cosine distance = 1 - cosine similarity
            similarity = 1.0 - distance
            text = results['documents'][0][i]
            output.append((doc_id, distance, similarity, text))
        
        return output
    
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
        results = self.knn_collection.query(
            query_embeddings=[embedding],
            n_results=k
        )
        
        # Extract and format results
        if not results['ids'] or not results['ids'][0]:
            return []
        
        output = []
        for i in range(len(results['ids'][0])):
            doc_id = results['ids'][0][i]
            euclidean_distance = results['distances'][0][i]
            text = results['documents'][0][i]
            output.append((doc_id, euclidean_distance, text))
        
        return output
