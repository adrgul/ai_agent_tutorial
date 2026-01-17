"""
RAG domain models for documents, chunks, and retrieval results.

These models represent the core entities in the RAG pipeline:
- Document: Uploaded file metadata
- Chunk: Text segment with embeddings metadata
- RetrievalResult: Search result with similarity scores
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import uuid


class Document(BaseModel):
    """Represents an uploaded document."""

    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    filename: str
    content: str
    chunk_count: int = 0
    size_chars: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Chunk(BaseModel):
    """Represents a text chunk with metadata for vector storage."""

    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    user_id: str
    text: str
    chunk_index: int
    start_offset: int = 0
    end_offset: int = 0
    token_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)  # filename, section_heading, etc.

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @property
    def source_label(self) -> str:
        """Generate a human-readable source label for citations."""
        filename = self.metadata.get("filename", "unknown")
        section = self.metadata.get("section_heading", "")
        if section:
            return f"{filename} - {section}"
        return f"{filename} (chunk {self.chunk_index + 1})"


class RetrievalResult(BaseModel):
    """Represents a retrieved chunk with similarity scores."""

    chunk: Chunk
    score: float  # Combined similarity score (0-1, higher is better)
    dense_score: Optional[float] = None  # Vector similarity score
    sparse_score: Optional[float] = None  # BM25 score (for future hybrid search)
    rank: int = 0  # Position in result list (1-indexed)

    @property
    def chunk_id(self) -> str:
        return self.chunk.chunk_id

    @property
    def text(self) -> str:
        return self.chunk.text

    @property
    def source_label(self) -> str:
        return self.chunk.source_label

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.chunk.metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_label": self.source_label,
            "score": self.score,
            "dense_score": self.dense_score,
            "sparse_score": self.sparse_score,
            "rank": self.rank,
            "metadata": self.metadata
        }


class RAGContext(BaseModel):
    """RAG context to be included in agent state."""

    rewritten_query: Optional[str] = None
    retrieved_chunks: List[RetrievalResult] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    context_text: str = ""
    retrieval_scores: List[float] = Field(default_factory=list)
    max_similarity_score: float = 0.0
    used_in_response: bool = False
    has_knowledge: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "rewritten_query": self.rewritten_query,
            "citations": self.citations,
            "chunk_count": len(self.retrieved_chunks),
            "max_similarity_score": self.max_similarity_score,
            "used_in_response": self.used_in_response,
            "has_knowledge": self.has_knowledge
        }


class RAGMetrics(BaseModel):
    """RAG performance metrics."""

    retrieval_latency_ms: float = 0.0
    chunk_count: int = 0
    max_similarity_score: float = 0.0
    rerank_used: bool = False
    query_rewrite_latency_ms: float = 0.0
    total_pipeline_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "retrieval_latency_ms": self.retrieval_latency_ms,
            "chunk_count": self.chunk_count,
            "max_similarity_score": self.max_similarity_score,
            "rerank_used": self.rerank_used,
            "query_rewrite_latency_ms": self.query_rewrite_latency_ms,
            "total_pipeline_latency_ms": self.total_pipeline_latency_ms
        }
