"""
RAG Configuration Module

Centralized configuration for the RAG pipeline.
"""

import os
from dataclasses import dataclass
from typing import List
from pathlib import Path


@dataclass
class ChunkingConfig:
    """Configuration for text chunking."""
    chunk_size: int = 1000  # characters
    chunk_overlap: int = 200  # characters


@dataclass
class EmbeddingConfig:
    """Configuration for embeddings."""
    model: str = "text-embedding-3-small"
    api_key: str = os.getenv("OPENAI_API_KEY", "")


@dataclass
class HybridConfig:
    """Configuration for hybrid retrieval."""
    alpha: float = 0.7  # weight for dense score (1-alpha for sparse)
    dense_top_k: int = 30
    sparse_top_k: int = 30


@dataclass
class RerankConfig:
    """Configuration for reranking."""
    enabled: bool = False
    strategy: str = "llm"  # "llm" or "embed"
    top_k_candidates: int = 30
    top_k_final: int = 5
    beta: float = 0.3  # weight for initial score (1-beta for rerank)
    llm_model: str = "gpt-4o-mini"


@dataclass
class StorageConfig:
    """Configuration for storage paths."""
    base_path: Path = Path("./data/rag")
    allowed_ingest_roots: List[str] = None
    
    def __post_init__(self):
        if self.allowed_ingest_roots is None:
            # Default allowed roots
            self.allowed_ingest_roots = [
                str(Path("/app/docs").resolve()),
                str(Path("./docs").resolve()),
                str(Path("./data/uploads").resolve()),
                str(Path("./test").resolve())
            ]
        self.base_path = Path(self.base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def get_tenant_path(self, tenant_id: str) -> Path:
        """Get base path for a tenant."""
        path = self.base_path / tenant_id
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_docs_path(self, tenant_id: str) -> Path:
        """Get docs path for a tenant."""
        path = self.get_tenant_path(tenant_id) / "docs"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_chunks_path(self, tenant_id: str) -> Path:
        """Get chunks path for a tenant."""
        path = self.get_tenant_path(tenant_id) / "chunks"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_vector_store_path(self, tenant_id: str) -> Path:
        """Get vector store path for a tenant."""
        path = self.get_tenant_path(tenant_id) / "vector_store"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_sparse_index_path(self, tenant_id: str) -> Path:
        """Get sparse index path for a tenant."""
        path = self.get_tenant_path(tenant_id) / "sparse_index"
        path.mkdir(parents=True, exist_ok=True)
        return path


@dataclass
class RAGConfig:
    """Main RAG configuration."""
    chunking: ChunkingConfig = None
    embedding: EmbeddingConfig = None
    hybrid: HybridConfig = None
    rerank: RerankConfig = None
    storage: StorageConfig = None
    
    def __post_init__(self):
        if self.chunking is None:
            self.chunking = ChunkingConfig()
        if self.embedding is None:
            self.embedding = EmbeddingConfig()
        if self.hybrid is None:
            self.hybrid = HybridConfig()
        if self.rerank is None:
            self.rerank = RerankConfig()
        if self.storage is None:
            self.storage = StorageConfig()
