"""
RAG configuration dataclasses for all RAG components.

Provides centralized configuration with sensible defaults for:
- Chunking (size, overlap, paragraph awareness)
- Embeddings (model selection, dimensions)
- Vector store (persist directory, collection name)
- Retrieval (top_k, similarity threshold)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os


@dataclass
class ChunkingConfig:
    """Configuration for text chunking."""

    chunk_size: int = 600  # Target tokens per chunk
    chunk_overlap: int = 90  # ~15% overlap
    min_chunk_size: int = 100  # Minimum chunk size
    max_chunk_size: int = 800  # Maximum chunk size
    paragraph_aware: bool = True  # Respect paragraph boundaries
    respect_sentence_boundary: bool = True  # Try to break at sentence ends
    markdown_heading_aware: bool = True  # Preserve MD headings as boundaries

    def __post_init__(self):
        """Validate configuration."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        if self.min_chunk_size <= 0:
            raise ValueError("min_chunk_size must be positive")


@dataclass
class EmbeddingConfig:
    """Configuration for embedding service."""

    model_name: str = "text-embedding-3-small"  # OpenAI model
    embedding_dim: int = 1536  # Dimensions for text-embedding-3-small
    batch_size: int = 100  # Max texts per API call
    max_retries: int = 3  # Retry attempts for API failures
    timeout_seconds: float = 30.0  # API timeout

    # Environment variable for API key
    api_key_env_var: str = "OPENAI_API_KEY"

    @property
    def api_key(self) -> str:
        """Get OpenAI API key from environment."""
        key = os.getenv(self.api_key_env_var)
        if not key:
            raise ValueError(
                f"OpenAI API key not found in environment variable: {self.api_key_env_var}"
            )
        return key


@dataclass
class VectorStoreConfig:
    """Configuration for ChromaDB vector store."""

    persist_directory: Path = field(default_factory=lambda: Path("data/rag/chroma"))
    collection_name: str = "rag_documents"  # Single collection with user_id filtering
    distance_function: str = "cosine"  # Similarity metric
    embedding_dim: int = 1536  # Must match embedding config

    # Multi-tenancy strategy
    use_per_user_collections: bool = False  # False = single collection with metadata filtering
    user_id_metadata_key: str = "user_id"

    def __post_init__(self):
        """Ensure persist directory exists."""
        self.persist_directory = Path(self.persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

    @property
    def chroma_client_settings(self) -> dict:
        """Get ChromaDB client settings."""
        return {
            "is_persistent": True,
            "path": str(self.persist_directory),
            "anonymized_telemetry": False
        }


@dataclass
class RetrievalConfig:
    """Configuration for retrieval service."""

    top_k: int = 5  # Number of chunks to retrieve
    similarity_threshold: float = 0.3  # Minimum similarity score (0-1) - lowered for better recall with multilingual queries
    max_context_tokens: int = 2500  # Maximum tokens in context window
    enable_reranking: bool = False  # Future: LLM-based reranking
    enable_hybrid_search: bool = False  # Future: BM25 + vector search

    # Score weighting for hybrid search (future)
    dense_weight: float = 0.7  # Vector similarity weight
    sparse_weight: float = 0.3  # BM25 weight

    def __post_init__(self):
        """Validate configuration."""
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        if not 0 <= self.similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        if self.dense_weight + self.sparse_weight != 1.0:
            raise ValueError("dense_weight + sparse_weight must equal 1.0")


@dataclass
class IngestionConfig:
    """Configuration for document ingestion."""

    uploads_directory: Path = field(default_factory=lambda: Path("data/rag/uploads"))
    supported_extensions: tuple = (".txt", ".md")
    max_file_size_mb: int = 10  # Maximum upload size
    store_raw_documents: bool = True  # Keep original files
    store_document_metadata: bool = True  # Save metadata JSON

    def __post_init__(self):
        """Ensure uploads directory exists."""
        self.uploads_directory = Path(self.uploads_directory)
        self.uploads_directory.mkdir(parents=True, exist_ok=True)

    def get_user_upload_dir(self, user_id: str) -> Path:
        """Get upload directory for specific user."""
        user_dir = self.uploads_directory / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


@dataclass
class RAGConfig:
    """Aggregated RAG configuration."""

    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)

    # Environment-based overrides
    def __post_init__(self):
        """Apply environment variable overrides."""
        # Override chunk size from env
        if chunk_size_str := os.getenv("RAG_CHUNK_SIZE"):
            try:
                self.chunking.chunk_size = int(chunk_size_str)
            except ValueError:
                pass

        # Override chunk overlap from env
        if overlap_str := os.getenv("RAG_CHUNK_OVERLAP"):
            try:
                self.chunking.chunk_overlap = int(overlap_str)
            except ValueError:
                pass

        # Override max context tokens from env
        if max_tokens_str := os.getenv("RAG_MAX_CONTEXT_TOKENS"):
            try:
                self.retrieval.max_context_tokens = int(max_tokens_str)
            except ValueError:
                pass

        # Override ChromaDB persist directory from env
        if persist_dir := os.getenv("CHROMA_PERSIST_DIR"):
            self.vector_store.persist_directory = Path(persist_dir)
            self.vector_store.persist_directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "RAGConfig":
        """Create configuration with environment variable overrides."""
        return cls()
