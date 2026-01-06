"""Qdrant client for vector database operations with multi-tenant support."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Any
import logging
import uuid

logger = logging.getLogger(__name__)


class QdrantManager:
    """Manager for Qdrant vector database operations with multi-tenant support."""
    
    def __init__(self, url: str = "http://localhost:6333", vector_size: int = 768):
        """
        Initialize the Qdrant manager.
        
        Args:
            url: URL of the Qdrant server
            vector_size: Dimension of the embedding vectors (default: 768 for nomic-embed-text)
        """
        self.client = QdrantClient(url=url)
        self.vector_size = vector_size
        logger.info(f"Initialized Qdrant client at {url} with vector_size={vector_size}")
    
    def get_collection_name(self, tenant: str) -> str:
        """
        Get the collection name for a specific tenant.
        
        Args:
            tenant: Tenant identifier
            
        Returns:
            Collection name for the tenant
        """
        return f"documents_{tenant}"
    
    def ensure_collection_exists(self, tenant: str):
        """
        Ensure that a collection exists for the given tenant.
        Creates the collection if it doesn't exist.
        
        Args:
            tenant: Tenant identifier
        """
        collection_name = self.get_collection_name(tenant)
        
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if collection_name not in collection_names:
                logger.info(f"Creating collection: {collection_name}")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection {collection_name} created successfully")
            else:
                logger.debug(f"Collection {collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    def store_chunks(
        self,
        tenant: str,
        document_id: str,
        chunks: List[str],
        embeddings: List[List[float]]
    ) -> int:
        """
        Store document chunks with their embeddings in Qdrant.
        
        Args:
            tenant: Tenant identifier
            document_id: Document identifier
            chunks: List of text chunks
            embeddings: List of embedding vectors corresponding to chunks
            
        Returns:
            Number of chunks stored
        """
        collection_name = self.get_collection_name(tenant)
        
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks count ({len(chunks)}) != embeddings count ({len(embeddings)})")
        
        points = []
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "chunk_index": idx,
                    "text": chunk_text
                }
            )
            points.append(point)
        
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Stored {len(points)} chunks for document {document_id} in {collection_name}")
            return len(points)
            
        except Exception as e:
            logger.error(f"Error storing chunks in Qdrant: {e}")
            raise
    
    def search(
        self,
        tenant: str,
        query_vector: List[float],
        limit: int,
        score_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the tenant's collection.
        
        Args:
            tenant: Tenant identifier
            query_vector: Query embedding vector
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score (note: for cosine distance, lower is better)
            
        Returns:
            List of search results with document_id, chunk_index, and score
        """
        collection_name = self.get_collection_name(tenant)
        
        try:
            # For cosine distance, score_threshold is the maximum distance allowed
            # (lower distance = higher similarity)
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )
            
            search_results = []
            for result in results:
                search_results.append({
                    "document_id": result.payload["document_id"],
                    "chunk_index": result.payload["chunk_index"],
                    "score": result.score,
                    "text": result.payload.get("text", "")
                })
            
            logger.info(f"Search returned {len(search_results)} results from {collection_name}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching Qdrant: {e}")
            raise
