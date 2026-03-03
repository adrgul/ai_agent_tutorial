"""
Reranking strategies for retrieved chunks.

Implements two-stage retrieval:
Stage 1: Retrieve candidates (dense/sparse/hybrid)
Stage 2: Rerank candidates using LLM or embedding similarity
"""

import requests
import json
import hashlib
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

from rag.models import RetrievalResult, RerankMetadata
from rag.config import RerankConfig, EmbeddingConfig
from rag.embeddings import EmbeddingService


class Reranker(ABC):
    """Abstract base class for reranking strategies."""
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """
        Rerank candidates and return top_k results.
        
        Args:
            query: Original query.
            candidates: Candidate results from initial retrieval.
            top_k: Number of final results to return.
        
        Returns:
            Reranked results.
        """
        pass


class LLMReranker(Reranker):
    """
    LLM-based reranker using OpenAI chat model.
    
    Uses structured output to get relevance scores for each candidate.
    """
    
    def __init__(self, config: RerankConfig = None):
        """
        Initialize LLM reranker.
        
        Args:
            config: Reranking configuration.
        """
        self.config = config or RerankConfig()
        self.api_key = EmbeddingConfig().api_key
        self.model = self.config.llm_model
        self.cache: Dict[str, float] = {}  # Simple in-memory cache
    
    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """
        Rerank using LLM relevance scoring.
        
        Args:
            query: Original query.
            candidates: Candidate results.
            top_k: Number of results to return.
        
        Returns:
            Reranked results with rerank_score and rerank_rationale.
        """
        if not candidates:
            return []
        
        # Score each candidate
        for result in candidates:
            cache_key = self._get_cache_key(query, result.chunk.chunk_id)
            
            if cache_key in self.cache:
                rerank_score = self.cache[cache_key]
                result.rerank_score = rerank_score
                result.rerank_rationale = "cached"
            else:
                score, rationale = self._score_candidate(query, result.chunk.text)
                result.rerank_score = score
                result.rerank_rationale = rationale
                self.cache[cache_key] = score
        
        # Normalize rerank scores to 0-1 range
        rerank_scores = [r.rerank_score for r in candidates if r.rerank_score is not None]
        if rerank_scores:
            max_score = max(rerank_scores)
            min_score = min(rerank_scores)
            score_range = max_score - min_score if max_score > min_score else 1.0
            
            for result in candidates:
                if result.rerank_score is not None:
                    result.rerank_score = (
                        (result.rerank_score - min_score) / score_range
                        if score_range > 0 else 1.0
                    )
        
        # Combine initial score with rerank score
        beta = self.config.beta
        for result in candidates:
            if result.rerank_score is not None:
                initial_score = result.score
                rerank_score = result.rerank_score
                result.score = beta * initial_score + (1 - beta) * rerank_score
        
        # Sort by combined score and return top_k
        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates[:top_k]
    
    def _score_candidate(self, query: str, chunk_text: str) -> tuple[float, str]:
        """
        Score a single candidate using LLM.
        
        Args:
            query: Query text.
            chunk_text: Chunk text to score.
        
        Returns:
            Tuple of (score, rationale).
        """
        # Truncate chunk if too long
        max_chunk_length = 1000
        if len(chunk_text) > max_chunk_length:
            chunk_text = chunk_text[:max_chunk_length] + "..."
        
        # Build prompt
        system_prompt = """You are a relevance scoring assistant. Rate how relevant a text chunk is to a query on a scale of 0-100.
Output JSON: {"score": <0-100>, "rationale": "<1 sentence max>"}"""
        
        user_prompt = f"""Query: {query}

Chunk: {chunk_text}

Rate relevance (0-100):"""
        
        # Call OpenAI API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": 100
        }
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            
            score = float(result.get("score", 50))
            rationale = result.get("rationale", "")
            
            return score, rationale
        
        except Exception as e:
            # Fallback to default score
            return 50.0, f"Error: {str(e)}"
    
    def _get_cache_key(self, query: str, chunk_id: str) -> str:
        """Generate cache key for query and chunk."""
        content = f"{query}:{chunk_id}:{self.model}"
        return hashlib.md5(content.encode()).hexdigest()


class EmbeddingReranker(Reranker):
    """
    Embedding-based reranker.
    
    Computes cosine similarity between query and candidate embeddings.
    This is a cheap alternative to LLM reranking.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService = None,
        config: RerankConfig = None
    ):
        """
        Initialize embedding reranker.
        
        Args:
            embedding_service: Embedding service instance.
            config: Reranking configuration.
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.config = config or RerankConfig()
    
    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """
        Rerank using embedding cross-similarity.
        
        Args:
            query: Original query.
            candidates: Candidate results.
            top_k: Number of results to return.
        
        Returns:
            Reranked results.
        """
        if not candidates:
            return []
        
        # Get query embedding
        query_embedding = self.embedding_service.get_embedding(query)
        
        # Get embeddings for all candidates (batch)
        candidate_texts = [r.chunk.text for r in candidates]
        candidate_embeddings = self.embedding_service.get_embeddings_batch(
            candidate_texts
        )
        
        # Compute cosine similarity
        for result, candidate_embedding in zip(candidates, candidate_embeddings):
            similarity = self._cosine_similarity(query_embedding, candidate_embedding)
            result.rerank_score = similarity
            result.rerank_rationale = "embedding similarity"
        
        # Combine initial score with rerank score
        beta = self.config.beta
        for result in candidates:
            if result.rerank_score is not None:
                initial_score = result.score
                rerank_score = result.rerank_score
                result.score = beta * initial_score + (1 - beta) * rerank_score
        
        # Sort and return top_k
        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates[:top_k]
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.
        
        Args:
            vec1: First vector.
            vec2: Second vector.
        
        Returns:
            Cosine similarity (0-1).
        """
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)


def create_reranker(
    strategy: str,
    embedding_service: EmbeddingService = None,
    config: RerankConfig = None
) -> Reranker:
    """
    Factory function to create reranker instance.
    
    Args:
        strategy: "llm" or "embed".
        embedding_service: Embedding service (for embed strategy).
        config: Reranking configuration.
    
    Returns:
        Reranker instance.
    """
    if strategy == "llm":
        return LLMReranker(config)
    elif strategy == "embed":
        return EmbeddingReranker(embedding_service, config)
    else:
        raise ValueError(f"Unknown reranking strategy: {strategy}")
