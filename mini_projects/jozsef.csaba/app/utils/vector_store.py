"""FAISS Vector Store implementation.

Following SOLID principles:
- Single Responsibility: Handles only vector storage and retrieval
- Dependency Inversion: Depends on abstractions (embeddings service interface)
- Open/Closed: Can be extended with new retrieval strategies
"""

import json
import os
import pickle
from pathlib import Path
from typing import List, Optional, Tuple

import faiss
import numpy as np

from app.models.schemas import Citation, KBChunk


class FAISSVectorStore:
    """FAISS-based vector store for knowledge base retrieval."""

    def __init__(
        self,
        embedding_dimension: int = 1536,  # OpenAI text-embedding-3-large dimension
        index_path: Optional[str] = None,
    ):
        """Initialize FAISS vector store.

        Args:
            embedding_dimension: Dimension of embedding vectors
            index_path: Path to save/load the index
        """
        self.embedding_dimension = embedding_dimension
        self.index_path = index_path
        self.index: Optional[faiss.Index] = None
        self.chunks: List[KBChunk] = []
        self._initialize_index()

    def _initialize_index(self) -> None:
        """Initialize or load FAISS index."""
        if self.index_path and os.path.exists(f"{self.index_path}/faiss.index"):
            self._load_index()
        else:
            # Create a new flat L2 index (exact search, good for POC)
            # For production, consider using IndexIVFFlat or IndexHNSWFlat
            self.index = faiss.IndexFlatL2(self.embedding_dimension)

    def add_documents(
        self, chunks: List[KBChunk], embeddings: np.ndarray
    ) -> None:
        """Add documents with their embeddings to the index.

        Args:
            chunks: List of knowledge base chunks
            embeddings: Numpy array of embeddings (n_docs x embedding_dim)
        """
        if embeddings.shape[0] != len(chunks):
            raise ValueError("Number of embeddings must match number of chunks")

        if embeddings.shape[1] != self.embedding_dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} doesn't match "
                f"expected dimension {self.embedding_dimension}"
            )

        # Add to FAISS index
        self.index.add(embeddings.astype(np.float32))

        # Store chunks
        self.chunks.extend(chunks)

    def search(
        self, query_embedding: np.ndarray, top_k: int = 10
    ) -> List[Citation]:
        """Search for similar documents.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return

        Returns:
            List of citations with relevance scores
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        # Ensure query is 2D array
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Search FAISS index
        distances, indices = self.index.search(
            query_embedding.astype(np.float32), min(top_k, self.index.ntotal)
        )

        # Convert to citations with scores
        citations = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx >= len(self.chunks):
                continue

            chunk = self.chunks[idx]

            # Convert L2 distance to similarity score (0-1 range)
            # Lower distance = higher similarity
            # Use exponential decay: score = exp(-distance)
            score = float(np.exp(-distance))

            citation = Citation(
                doc_id=chunk.doc_id,
                chunk_id=chunk.chunk_id,
                title=chunk.title,
                score=score,
                url=chunk.url,
                content=chunk.content,
            )
            citations.append(citation)

        return citations

    def save_index(self) -> None:
        """Save FAISS index and chunks to disk."""
        if self.index_path is None:
            raise ValueError("index_path must be set to save index")

        # Create directory if it doesn't exist
        Path(self.index_path).mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, f"{self.index_path}/faiss.index")

        # Save chunks metadata
        chunks_data = [chunk.model_dump() for chunk in self.chunks]
        with open(f"{self.index_path}/chunks.pkl", "wb") as f:
            pickle.dump(chunks_data, f)

    def _load_index(self) -> None:
        """Load FAISS index and chunks from disk."""
        if self.index_path is None:
            raise ValueError("index_path must be set to load index")

        # Load FAISS index
        self.index = faiss.read_index(f"{self.index_path}/faiss.index")

        # Load chunks metadata
        with open(f"{self.index_path}/chunks.pkl", "rb") as f:
            chunks_data = pickle.load(f)
            self.chunks = [KBChunk(**chunk) for chunk in chunks_data]

    @property
    def num_documents(self) -> int:
        """Get number of documents in the index."""
        return self.index.ntotal if self.index else 0

    def clear(self) -> None:
        """Clear the index and chunks."""
        self._initialize_index()
        self.chunks = []
