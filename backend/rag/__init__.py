"""
RAG (Retrieval-Augmented Generation) module for document-based knowledge retrieval.

This module implements a production-grade RAG pipeline using:
- ChromaDB for vector storage
- OpenAI embeddings (text-embedding-3-small)
- LangGraph for RAG orchestration
- Paragraph-aware text chunking

The RAG pipeline follows the retrieval-before-tools principle:
RAG retrieval ALWAYS executes BEFORE any external tool decisions.
"""

__version__ = "1.0.0"
