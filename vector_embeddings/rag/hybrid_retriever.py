"""
Hybrid retrieval combining dense and sparse search.
"""

from typing import List, Dict
from rag.models import RetrievalResult, Chunk
from rag.vector_store import VectorStore
from rag.sparse_index import SparseIndex
from rag.embeddings import EmbeddingService
from rag.config import HybridConfig, StorageConfig, EmbeddingConfig


class HybridRetriever:
    """
    Hybrid retriever combining dense (vector) and sparse (BM25) search.
    
    Implements three modes:
    - dense: Vector similarity only
    - sparse: BM25 lexical search only
    - hybrid: Weighted combination of both
    """
    
    def __init__(
        self,
        tenant_id: str,
        embedding_service: EmbeddingService = None,
        vector_store: VectorStore = None,
        sparse_index: SparseIndex = None,
        config: HybridConfig = None,
        storage_config: StorageConfig = None
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            tenant_id: Tenant ID for multi-tenancy.
            embedding_service: Embedding service instance.
            vector_store: Vector store instance.
            sparse_index: Sparse index instance.
            config: Hybrid configuration.
            storage_config: Storage configuration.
        """
        self.tenant_id = tenant_id
        self.config = config or HybridConfig()
        
        # Initialize services if not provided
        self.embedding_service = embedding_service or EmbeddingService(
            EmbeddingConfig()
        )
        self.vector_store = vector_store or VectorStore(
            tenant_id, storage_config
        )
        self.sparse_index = sparse_index or SparseIndex(
            tenant_id, storage_config
        )
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        mode: str = "hybrid"
    ) -> List[RetrievalResult]:
        """
        Retrieve chunks using specified mode.
        
        Args:
            query: Query text.
            top_k: Number of results to return.
            mode: Retrieval mode ("dense", "sparse", or "hybrid").
        
        Returns:
            List of RetrievalResult objects sorted by score.
        """
        if mode == "dense":
            return self._retrieve_dense(query, top_k)
        elif mode == "sparse":
            return self._retrieve_sparse(query, top_k)
        elif mode == "hybrid":
            return self._retrieve_hybrid(query, top_k)
        else:
            raise ValueError(f"Unknown retrieval mode: {mode}")
    
    def _retrieve_dense(self, query: str, top_k: int) -> List[RetrievalResult]:
        """Dense retrieval using vector similarity."""
        query_embedding = self.embedding_service.get_embedding(query)
        results = self.vector_store.search(query_embedding, top_k)
        return results
    
    def _retrieve_sparse(self, query: str, top_k: int) -> List[RetrievalResult]:
        """Sparse retrieval using BM25."""
        results = self.sparse_index.search(query, top_k)
        return results
    
    def _retrieve_hybrid(self, query: str, top_k: int) -> List[RetrievalResult]:
        """
        Hybrid retrieval combining dense and sparse scores.
        
        Algorithm:
        1. Retrieve top_k candidates from both dense and sparse
        2. Combine scores with weighted average: alpha * dense + (1-alpha) * sparse
        3. Sort by combined score and return top_k
        """
        # Retrieve candidates from both methods
        # Use higher k for candidates to ensure good coverage
        candidate_k = max(top_k * 3, self.config.dense_top_k)
        
        # Dense retrieval
        query_embedding = self.embedding_service.get_embedding(query)
        dense_results = self.vector_store.search(query_embedding, candidate_k)
        
        # Sparse retrieval
        sparse_results = self.sparse_index.search(query, candidate_k)
        
        # Build score dictionaries
        dense_scores = {r.chunk.chunk_id: r.score for r in dense_results}
        sparse_scores = {r.chunk.chunk_id: r.score for r in sparse_results}
        
        # Combine all unique chunk IDs
        all_chunk_ids = set(dense_scores.keys()) | set(sparse_scores.keys())
        
        # Build chunk lookup
        chunk_lookup = {}
        for r in dense_results:
            chunk_lookup[r.chunk.chunk_id] = r.chunk
        for r in sparse_results:
            if r.chunk.chunk_id not in chunk_lookup:
                chunk_lookup[r.chunk.chunk_id] = r.chunk
        
        # Calculate combined scores
        combined_results = []
        alpha = self.config.alpha
        
        for chunk_id in all_chunk_ids:
            dense_score = dense_scores.get(chunk_id, 0.0)
            sparse_score = sparse_scores.get(chunk_id, 0.0)
            
            # Weighted combination
            combined_score = alpha * dense_score + (1 - alpha) * sparse_score
            
            chunk = chunk_lookup[chunk_id]
            
            result = RetrievalResult(
                chunk=chunk,
                score=combined_score,
                dense_score=dense_score if dense_score > 0 else None,
                sparse_score=sparse_score if sparse_score > 0 else None
            )
            
            combined_results.append(result)
        
        # Sort by combined score and return top_k
        combined_results.sort(key=lambda r: r.score, reverse=True)
        return combined_results[:top_k]
    
    def retrieve_candidates(
        self,
        query: str,
        top_k_candidates: int = 30,
        mode: str = "hybrid"
    ) -> List[RetrievalResult]:
        """
        Retrieve candidate chunks for reranking.
        
        This is the first stage in a two-stage retrieval + rerank pipeline.
        
        Args:
            query: Query text.
            top_k_candidates: Number of candidates to retrieve.
            mode: Retrieval mode.
        
        Returns:
            List of candidate RetrievalResult objects.
        """
        return self.retrieve(query, top_k_candidates, mode)
