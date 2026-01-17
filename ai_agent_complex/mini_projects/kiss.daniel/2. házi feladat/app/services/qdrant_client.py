"""Qdrant vector database client with multi-tenant support."""

import logging
from typing import List, Dict, Any
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app.config import QDRANT_URL, QDRANT_COLLECTION

logger = logging.getLogger(__name__)


class QdrantService:
    """Service for interacting with Qdrant vector database."""
    
    def __init__(
        self,
        url: str = QDRANT_URL,
        collection_name: str = QDRANT_COLLECTION,
        vector_size: int = 1024  # Default for BAAI/bge-m3
    ):
        """
        Initialize the Qdrant service.
        
        Args:
            url: Qdrant server URL
            collection_name: Name of the collection to use
            vector_size: Dimension of embedding vectors
        """
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.vector_size = vector_size
        logger.info(f"Initialized Qdrant client at {url}, collection: {collection_name}")
    
    def ensure_collection(self) -> None:
        """
        Ensure that the collection exists.
        Creates the collection if it doesn't exist.
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.debug(f"Collection {self.collection_name} already exists")
                
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    def upsert_chunks(
        self,
        tenant: str,
        document_id: str,
        chunks: List[Dict[str, Any]]
    ) -> int:
        """
        Upsert document chunks with their embeddings into Qdrant.
        
        Args:
            tenant: Tenant identifier
            document_id: Document identifier
            chunks: List of chunk dictionaries with fields:
                    - text: chunk text
                    - embedding: embedding vector
                    - chunk_index: index of chunk in document
            
        Returns:
            Number of chunks stored
        """
        if not chunks:
            logger.warning("No chunks to upsert")
            return 0
        
        points = []
        for chunk in chunks:
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=chunk["embedding"],
                payload={
                    "tenant": tenant,
                    "document_id": document_id,
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"]
                }
            )
            points.append(point)
        
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Upserted {len(points)} chunks for document {document_id}, tenant {tenant}")
            return len(points)
            
        except Exception as e:
            logger.error(f"Error upserting chunks to Qdrant: {e}")
            raise
    
    def search(
        self,
        tenant: str,
        query_vector: List[float],
        top_k: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in the collection, filtered by tenant.
        
        Args:
            tenant: Tenant identifier to filter by
            query_vector: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of search results with payload and score
        """
        try:
            # Create filter for tenant
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="tenant",
                        match=MatchValue(value=tenant)
                    )
                ]
            )
            
            # Perform search using query_points method
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k
            )
            
            search_results = []
            for result in results.points:
                search_results.append({
                    "document_id": result.payload["document_id"],
                    "chunk_index": result.payload["chunk_index"],
                    "text": result.payload["text"],
                    "score": result.score
                })
            
            logger.info(f"Search returned {len(search_results)} results for tenant {tenant}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching Qdrant: {e}")
            raise
