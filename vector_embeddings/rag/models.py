"""
Data models for RAG pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import hashlib


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    chunk_id: str
    doc_id: str
    tenant_id: str
    text: str
    start_offset: int
    end_offset: int
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_source_label(self) -> str:
        """Get a short source label for citations."""
        filename = self.metadata.get("filename", "unknown")
        return f"{filename}#chunk_{self.chunk_index}"
    
    @property
    def checksum(self) -> str:
        """Calculate checksum of chunk text."""
        return hashlib.md5(self.text.encode()).hexdigest()


@dataclass
class Document:
    """Represents an ingested document."""
    doc_id: str
    tenant_id: str
    filename: str
    source_path: str
    text: str
    ingested_at: str
    size_chars: int
    chunk_size: int
    chunk_overlap: int
    hash: str
    chunk_count: int = 0
    
    @staticmethod
    def generate_id(tenant_id: str, filename: str) -> str:
        """Generate a unique document ID."""
        timestamp = datetime.utcnow().isoformat()
        content = f"{tenant_id}:{filename}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @staticmethod
    def hash_text(text: str) -> str:
        """Calculate hash of document text."""
        return hashlib.sha256(text.encode()).hexdigest()


@dataclass
class RetrievalResult:
    """Result from retrieval with score."""
    chunk: Chunk
    score: float
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None
    rerank_score: Optional[float] = None
    rerank_rationale: Optional[str] = None


@dataclass
class RerankMetadata:
    """Metadata about reranking operation."""
    strategy: str
    model: Optional[str]
    beta: float
    top_k_candidates: int
    top_k_final: int


@dataclass
class RAGAnswer:
    """RAG answer with citations."""
    answer: str
    citations: List[str]
    retrieved_chunks: List[RetrievalResult]
    candidates_before_rerank: Optional[List[RetrievalResult]] = None
    rerank_metadata: Optional[RerankMetadata] = None
    mode: str = "hybrid"
    query: str = ""
