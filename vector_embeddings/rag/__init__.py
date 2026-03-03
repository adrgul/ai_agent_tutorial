"""
RAG (Retrieval-Augmented Generation) Module

This module provides a complete RAG pipeline implementation including:
- Document ingestion and chunking with overlap
- Multi-tenant isolation
- Dense (vector) and sparse (BM25) indexing
- Hybrid retrieval with configurable scoring
- Reranking strategies (LLM-based and embedding-based)
- RAG answer generation with citations
"""

__version__ = "1.0.0"
