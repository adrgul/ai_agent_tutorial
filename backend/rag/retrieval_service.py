"""
Retrieval service for RAG vector search.

Provides high-level retrieval interface with:
- Vector similarity search
- Similarity score filtering
- Hybrid-ready design (future BM25 integration)
"""

import logging
from typing import List, Optional
import time

from .models import RetrievalResult
from .embeddings import IEmbeddingService
from .vector_store import IVectorStore
from .config import RetrievalConfig

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Service for retrieving relevant chunks from vector store.

    Currently implements pure vector search.
    Designed to support future hybrid search (BM25 + vector).
    """

    def __init__(
        self,
        vector_store: IVectorStore,
        embedding_service: IEmbeddingService,
        config: RetrievalConfig
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.config = config

        logger.info("Initialized retrieval service")

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: Optional[int] = None
    ) -> tuple[List[RetrievalResult], float]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: User query text
            user_id: User identifier for filtering
            top_k: Number of results to return (overrides config)

        Returns:
            Tuple of (retrieval_results, latency_ms)
        """
        start_time = time.time()

        if top_k is None:
            top_k = self.config.top_k

        try:
            # Embed query
            query_embedding = await self.embedding_service.embed_query(query)

            # Search vector store
            results = await self.vector_store.search(
                query_embedding=query_embedding,
                user_id=user_id,
                top_k=top_k
            )

            # Apply similarity threshold filtering
            filtered_results = [
                r for r in results
                if r.score >= self.config.similarity_threshold
            ]

            latency_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Retrieved {len(filtered_results)}/{len(results)} chunks "
                f"(filtered by threshold {self.config.similarity_threshold}) "
                f"in {latency_ms:.2f}ms"
            )

            return filtered_results, latency_ms

        except Exception as e:
            logger.error(f"Error in retrieval: {e}")
            raise

    async def retrieve_hybrid(
        self,
        query: str,
        user_id: str,
        top_k: Optional[int] = None
    ) -> tuple[List[RetrievalResult], float]:
        """
        Hybrid retrieval combining vector and BM25 search.

        FUTURE IMPLEMENTATION: Currently falls back to vector-only search.

        Args:
            query: User query text
            user_id: User identifier
            top_k: Number of results

        Returns:
            Tuple of (retrieval_results, latency_ms)
        """
        # TODO: Implement BM25 sparse retrieval
        # TODO: Combine scores using dense_weight and sparse_weight
        # TODO: Rerank combined results

        logger.warning("Hybrid retrieval not yet implemented, falling back to vector search")
        return await self.retrieve(query, user_id, top_k)
