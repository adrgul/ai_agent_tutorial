"""Dependency injection for FastAPI.

Following SOLID principles:
- Dependency Inversion: Provides abstractions through FastAPI dependencies
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Generator

from app.core.config import Settings, get_settings
from app.services.embeddings import EmbeddingService
from app.utils.vector_store import FAISSVectorStore
from app.workflows.langgraph_workflow import TriageWorkflow
from app.models.schemas import KBArticle, KBChunk


@lru_cache()
def get_vector_store(settings: Settings = None) -> FAISSVectorStore:
    """Get or create vector store instance.

    Args:
        settings: Application settings

    Returns:
        Initialized vector store
    """
    if settings is None:
        settings = get_settings()

    vector_store = FAISSVectorStore(
        embedding_dimension=1536,  # OpenAI text-embedding-3-large
        index_path=settings.faiss_index_path,
    )

    return vector_store


@lru_cache()
def get_embedding_service(settings: Settings = None) -> EmbeddingService:
    """Get embedding service instance.

    Args:
        settings: Application settings

    Returns:
        Embedding service
    """
    if settings is None:
        settings = get_settings()

    return EmbeddingService(settings)


@lru_cache()
def get_workflow(
    settings: Settings = None,
    vector_store: FAISSVectorStore = None,
    embedding_service: EmbeddingService = None,
) -> TriageWorkflow:
    """Get workflow instance.

    Args:
        settings: Application settings
        vector_store: Vector store instance
        embedding_service: Embedding service instance

    Returns:
        Initialized workflow
    """
    if settings is None:
        settings = get_settings()

    if vector_store is None:
        vector_store = get_vector_store(settings)

    if embedding_service is None:
        embedding_service = get_embedding_service(settings)

    return TriageWorkflow(settings, vector_store, embedding_service)


def initialize_knowledge_base() -> None:
    """Initialize knowledge base with dummy data."""
    settings = get_settings()
    vector_store = get_vector_store(settings)
    embedding_service = get_embedding_service(settings)

    # Check if already initialized
    if vector_store.num_documents > 0:
        print(f"Knowledge base already initialized with {vector_store.num_documents} documents")
        return

    # Load KB articles
    kb_file = Path("data/kb_articles.json")
    if not kb_file.exists():
        print(f"Warning: KB articles file not found at {kb_file}")
        return

    with open(kb_file, "r") as f:
        kb_data = json.load(f)

    articles = [KBArticle(**item) for item in kb_data]

    # Chunk articles (simple chunking by paragraph or max length)
    chunks = []
    for article in articles:
        # Split by paragraphs
        paragraphs = article.content.split("\n\n")

        for idx, paragraph in enumerate(paragraphs):
            if len(paragraph.strip()) < 50:  # Skip very short paragraphs
                continue

            chunk = KBChunk(
                chunk_id=f"{article.doc_id}-c{idx}",
                doc_id=article.doc_id,
                title=article.title,
                content=paragraph.strip(),
                chunk_index=idx,
                url=article.url,
                category=article.category,
            )
            chunks.append(chunk)

    if not chunks:
        print("No chunks created from KB articles")
        return

    print(f"Creating embeddings for {len(chunks)} chunks...")

    # Generate embeddings
    texts = [chunk.content for chunk in chunks]
    embeddings = embedding_service.embed_texts(texts)

    print(f"Adding {len(chunks)} chunks to vector store...")

    # Add to vector store
    vector_store.add_documents(chunks, embeddings)

    # Save index
    vector_store.save_index()

    print(f"Knowledge base initialized with {vector_store.num_documents} documents")
