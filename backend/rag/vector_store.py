"""
ChromaDB vector store implementation for RAG.

Provides repository pattern abstraction over ChromaDB with:
- Single collection with user_id metadata filtering
- CRUD operations for chunks
- Vector similarity search
- Multi-tenant isolation
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings

from .models import Chunk, RetrievalResult
from .config import VectorStoreConfig

logger = logging.getLogger(__name__)


class IVectorStore(ABC):
    """Interface for vector store operations."""

    @abstractmethod
    async def add_chunks(
        self,
        chunks: List[Chunk],
        embeddings: List[List[float]]
    ) -> None:
        """Add chunks with their embeddings to the store."""
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        user_id: str,
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """Search for similar chunks filtered by user_id."""
        pass

    @abstractmethod
    async def delete_document(self, doc_id: str, user_id: str) -> int:
        """Delete all chunks for a document. Returns count of deleted chunks."""
        pass

    @abstractmethod
    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for user's documents."""
        pass

    @abstractmethod
    async def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """List all documents for a user."""
        pass


class ChromaVectorStore(IVectorStore):
    """
    ChromaDB implementation of vector store.

    Uses single collection with user_id metadata filtering for multi-tenancy.
    """

    def __init__(self, config: VectorStoreConfig):
        self.config = config

        # Initialize ChromaDB client
        settings = Settings(
            persist_directory=str(config.persist_directory),
            anonymized_telemetry=False
        )

        self.client = chromadb.Client(settings)

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=config.collection_name,
            metadata={"hnsw:space": config.distance_function}
        )

        logger.info(
            f"Initialized ChromaDB vector store: {config.collection_name} "
            f"at {config.persist_directory}"
        )

    async def add_chunks(
        self,
        chunks: List[Chunk],
        embeddings: List[List[float]]
    ) -> None:
        """
        Add chunks with embeddings to ChromaDB.

        Each chunk is stored with metadata including user_id for filtering.
        """
        if not chunks or not embeddings:
            logger.warning("No chunks or embeddings to add")
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks and embeddings length mismatch: {len(chunks)} vs {len(embeddings)}"
            )

        # Prepare data for ChromaDB
        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        metadatas = []

        for chunk in chunks:
            metadata = {
                self.config.user_id_metadata_key: chunk.user_id,
                "doc_id": chunk.doc_id,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "filename": chunk.metadata.get("filename", ""),
                "created_at": chunk.created_at.isoformat(),
            }

            # Add section heading if present
            if "section_heading" in chunk.metadata:
                metadata["section_heading"] = chunk.metadata["section_heading"]

            metadatas.append(metadata)

        # Add to collection
        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Added {len(chunks)} chunks to ChromaDB")

        except Exception as e:
            logger.error(f"Error adding chunks to ChromaDB: {e}")
            raise

    async def search(
        self,
        query_embedding: List[float],
        user_id: str,
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """
        Search for similar chunks filtered by user_id.

        Returns chunks sorted by similarity (most similar first).
        """
        try:
            # Query with user_id filter
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={self.config.user_id_metadata_key: user_id}
            )

            # Convert to RetrievalResult objects
            retrieval_results = []

            if not results['ids'] or not results['ids'][0]:
                logger.info(f"No results found for user: {user_id}")
                return []

            # Chromadb returns lists of lists (for multiple queries)
            ids = results['ids'][0]
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0]

            for idx, (chunk_id, text, metadata, distance) in enumerate(
                zip(ids, documents, metadatas, distances)
            ):
                # Convert distance to similarity score (0-1, higher is better)
                # ChromaDB uses L2 distance, convert to similarity
                similarity_score = 1 / (1 + distance)

                # Reconstruct Chunk object
                chunk = Chunk(
                    chunk_id=chunk_id,
                    doc_id=metadata.get("doc_id", ""),
                    user_id=user_id,
                    text=text,
                    chunk_index=metadata.get("chunk_index", 0),
                    token_count=metadata.get("token_count", 0),
                    metadata={
                        "filename": metadata.get("filename", ""),
                        "section_heading": metadata.get("section_heading", "")
                    }
                )

                result = RetrievalResult(
                    chunk=chunk,
                    score=similarity_score,
                    dense_score=similarity_score,
                    rank=idx + 1
                )

                retrieval_results.append(result)

            logger.info(f"Retrieved {len(retrieval_results)} chunks for user: {user_id}")
            return retrieval_results

        except Exception as e:
            logger.error(f"Error searching ChromaDB: {e}")
            raise

    async def delete_document(self, doc_id: str, user_id: str) -> int:
        """
        Delete all chunks for a document.

        Returns count of deleted chunks.
        """
        try:
            # Get all chunk IDs for this document
            results = self.collection.get(
                where={
                    "$and": [
                        {"doc_id": doc_id},
                        {self.config.user_id_metadata_key: user_id}
                    ]
                }
            )

            if not results['ids']:
                logger.info(f"No chunks found for document: {doc_id}")
                return 0

            chunk_ids = results['ids']

            # Delete chunks
            self.collection.delete(ids=chunk_ids)

            logger.info(f"Deleted {len(chunk_ids)} chunks for document: {doc_id}")
            return len(chunk_ids)

        except Exception as e:
            logger.error(f"Error deleting document from ChromaDB: {e}")
            raise

    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics for user's documents.

        Returns document count, chunk count, etc.
        """
        try:
            # Get all chunks for user
            results = self.collection.get(
                where={self.config.user_id_metadata_key: user_id}
            )

            if not results['ids']:
                return {
                    "document_count": 0,
                    "chunk_count": 0,
                    "collection_name": self.config.collection_name,
                    "persist_directory": str(self.config.persist_directory)
                }

            # Count unique documents
            doc_ids = set()
            for metadata in results['metadatas']:
                doc_ids.add(metadata.get("doc_id", ""))

            return {
                "document_count": len(doc_ids),
                "chunk_count": len(results['ids']),
                "collection_name": self.config.collection_name,
                "persist_directory": str(self.config.persist_directory)
            }

        except Exception as e:
            logger.error(f"Error getting stats from ChromaDB: {e}")
            raise

    async def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all documents for a user with metadata.

        Returns list of document info dictionaries.
        """
        try:
            # Get all chunks for user
            results = self.collection.get(
                where={self.config.user_id_metadata_key: user_id}
            )

            if not results['ids']:
                return []

            # Group by document
            doc_info = {}

            for metadata in results['metadatas']:
                doc_id = metadata.get("doc_id", "")
                if doc_id not in doc_info:
                    doc_info[doc_id] = {
                        "doc_id": doc_id,
                        "filename": metadata.get("filename", ""),
                        "chunk_count": 0,
                        "ingested_at": metadata.get("created_at", "")
                    }
                doc_info[doc_id]["chunk_count"] += 1

            documents = list(doc_info.values())

            logger.info(f"Listed {len(documents)} documents for user: {user_id}")
            return documents

        except Exception as e:
            logger.error(f"Error listing documents from ChromaDB: {e}")
            raise
