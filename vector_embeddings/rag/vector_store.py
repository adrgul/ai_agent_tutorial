"""
Persistent vector store with multi-tenant support.

Uses ChromaDB for vector storage and similarity search.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Tuple, Optional
import json
from pathlib import Path

from rag.models import Chunk, RetrievalResult
from rag.config import StorageConfig


class VectorStore:
    """
    Vector store for dense retrieval using ChromaDB.
    
    Implements multi-tenant isolation by using separate collections per tenant.
    """
    
    def __init__(self, tenant_id: str, config: StorageConfig = None):
        """
        Initialize vector store for a specific tenant.
        
        Args:
            tenant_id: Tenant ID for isolation.
            config: Storage configuration.
        """
        self.tenant_id = tenant_id
        self.config = config or StorageConfig()
        
        # Get tenant-specific path
        db_path = str(self.config.get_vector_store_path(tenant_id))
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Create or get collection for this tenant
        self.collection = self.client.get_or_create_collection(
            name=f"chunks_{tenant_id}",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_chunk(self, chunk: Chunk, embedding: List[float]) -> None:
        """
        Add a chunk with its embedding to the vector store.
        
        Args:
            chunk: Chunk object with text and metadata.
            embedding: Embedding vector.
        """
        # Prepare metadata (ChromaDB requires string/int/float values)
        metadata = {
            "doc_id": chunk.doc_id,
            "tenant_id": chunk.tenant_id,
            "chunk_index": chunk.chunk_index,
            "start_offset": chunk.start_offset,
            "end_offset": chunk.end_offset,
            "checksum": chunk.checksum
        }
        
        # Add additional metadata
        for key, value in chunk.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                metadata[key] = value
        
        # Add to collection
        self.collection.add(
            ids=[chunk.chunk_id],
            embeddings=[embedding],
            documents=[chunk.text],
            metadatas=[metadata]
        )
    
    def add_chunks_batch(
        self,
        chunks: List[Chunk],
        embeddings: List[List[float]]
    ) -> None:
        """
        Add multiple chunks in a batch.
        
        Args:
            chunks: List of chunks.
            embeddings: List of embedding vectors (same order as chunks).
        """
        if not chunks or not embeddings:
            return
        
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")
        
        ids = []
        documents = []
        metadatas = []
        embedding_list = []
        
        for chunk, embedding in zip(chunks, embeddings):
            ids.append(chunk.chunk_id)
            documents.append(chunk.text)
            
            metadata = {
                "doc_id": chunk.doc_id,
                "tenant_id": chunk.tenant_id,
                "chunk_index": chunk.chunk_index,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "checksum": chunk.checksum
            }
            
            for key, value in chunk.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    metadata[key] = value
            
            metadatas.append(metadata)
            embedding_list.append(embedding)
        
        # Batch add
        self.collection.add(
            ids=ids,
            embeddings=embedding_list,
            documents=documents,
            metadatas=metadatas
        )
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        Search for similar chunks using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector.
            top_k: Number of results to return.
        
        Returns:
            List of RetrievalResult objects with scores.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results["ids"] or not results["ids"][0]:
            return []
        
        retrieval_results = []
        
        for i in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][i]
            text = results["documents"][0][i]
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i]
            
            # Convert distance to similarity score (cosine similarity)
            # ChromaDB returns cosine distance (1 - similarity)
            score = 1.0 - distance
            
            # Reconstruct chunk object
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=metadata.get("doc_id", ""),
                tenant_id=metadata.get("tenant_id", self.tenant_id),
                text=text,
                start_offset=metadata.get("start_offset", 0),
                end_offset=metadata.get("end_offset", 0),
                chunk_index=metadata.get("chunk_index", 0),
                metadata={
                    k: v for k, v in metadata.items()
                    if k not in ["doc_id", "tenant_id", "chunk_index",
                                "start_offset", "end_offset", "checksum"]
                }
            )
            
            retrieval_results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=score,
                    dense_score=score
                )
            )
        
        return retrieval_results
    
    def delete_by_doc_id(self, doc_id: str) -> None:
        """
        Delete all chunks for a specific document.
        
        Args:
            doc_id: Document ID.
        """
        # Query to find all chunks for this document
        results = self.collection.get(
            where={"doc_id": doc_id}
        )
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
    
    def count(self) -> int:
        """
        Get total number of chunks in the store.
        
        Returns:
            Number of chunks.
        """
        return self.collection.count()
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """
        Get a chunk by its ID.
        
        Args:
            chunk_id: Chunk ID.
        
        Returns:
            Chunk object or None if not found.
        """
        results = self.collection.get(
            ids=[chunk_id],
            include=["documents", "metadatas"]
        )
        
        if not results["ids"]:
            return None
        
        text = results["documents"][0]
        metadata = results["metadatas"][0]
        
        return Chunk(
            chunk_id=chunk_id,
            doc_id=metadata.get("doc_id", ""),
            tenant_id=metadata.get("tenant_id", self.tenant_id),
            text=text,
            start_offset=metadata.get("start_offset", 0),
            end_offset=metadata.get("end_offset", 0),
            chunk_index=metadata.get("chunk_index", 0),
            metadata={
                k: v for k, v in metadata.items()
                if k not in ["doc_id", "tenant_id", "chunk_index",
                            "start_offset", "end_offset", "checksum"]
            }
        )
