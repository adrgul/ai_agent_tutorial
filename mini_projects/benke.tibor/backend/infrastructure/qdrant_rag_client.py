"""
Infrastructure - Qdrant-based RAG client for production use.
"""
import logging
import os
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from domain.models import Citation, DomainType
from domain.interfaces import IRAGClient
from infrastructure.openai_clients import OpenAIClientFactory
from infrastructure.redis_client import redis_cache
from infrastructure.postgres_client import postgres_client

logger = logging.getLogger(__name__)


def calculate_feedback_boost(like_percentage: Optional[float]) -> float:
    """
    Calculate multiplicative boost factor based on user feedback.
    
    Formula: final_score = semantic_score * (1 + feedback_boost)
    
    Tiered boost system:
    - >70% like: +0.3 (30% boost) - High quality, popular content
    - 40-70% like: +0.1 (10% boost) - Moderate approval
    - <40% like: -0.2 (20% penalty) - Poor quality, demote
    - No feedback: 0.0 (neutral) - Don't penalize new content
    
    Args:
        like_percentage: Percentage of likes (0-100) or None if no feedback
        
    Returns:
        Boost factor to apply: -0.2 to +0.3
        
    Examples:
        >>> calculate_feedback_boost(85.0)  # 85% like
        0.3  # 30% boost
        >>> calculate_feedback_boost(55.0)  # 55% like
        0.1  # 10% boost
        >>> calculate_feedback_boost(25.0)  # 25% like
        -0.2  # 20% penalty
        >>> calculate_feedback_boost(None)  # No feedback
        0.0  # Neutral
    """
    if like_percentage is None:
        return 0.0  # Neutral for new/unfeedback content
    
    if like_percentage > 70:
        return 0.3  # High quality boost
    elif like_percentage >= 40:
        return 0.1  # Moderate boost
    else:
        return -0.2  # Quality penalty


class QdrantRAGClient(IRAGClient):
    """
    Production Qdrant RAG client.
    Retrieves relevant documents from Qdrant vector database.
    """

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6334",
        collection_name: str = "multi_domain_kb"  # Multi-domain collection with domain filtering
    ):
        """
        Initialize Qdrant RAG client with hybrid search support.
        Uses centralized OpenAI embeddings factory.
        
        Args:
            qdrant_url: Qdrant server URL
            collection_name: Qdrant collection name (default: multi_domain_kb for all domains)
        """
        self.qdrant_client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name
        # Use centralized embeddings instance
        self.embeddings = OpenAIClientFactory.get_embeddings()
        logger.info(f"QdrantRAGClient initialized: {qdrant_url}, collection={collection_name} (hybrid search ready)")

    async def retrieve_for_domain(
        self, domain: str, query: str, top_k: int = 5
    ) -> List[Citation]:
        """
        Retrieve relevant documents for a domain from Qdrant.
        
        Args:
            domain: Domain type (hr, it, finance, legal, marketing, general)
            query: User query
            top_k: Number of documents to retrieve
            
        Returns:
            List of citations with relevance scores
        """
        try:
            domain_enum = DomainType(domain.lower())
        except ValueError:
            domain_enum = DomainType.GENERAL
            logger.warning(f"Invalid domain '{domain}', using GENERAL")

        # All domains can use Qdrant (with domain filtering)
        # Marketing is currently indexed, others will be added
        if domain_enum == DomainType.MARKETING:
            return await self._retrieve_from_qdrant(query, top_k, domain=domain_enum.value)
        
        # For non-marketing domains, try Qdrant first, fallback to mock
        # This allows gradual migration as we index more domains
        try:
            results = await self._retrieve_from_qdrant(query, top_k, domain=domain_enum.value)
            if results:
                return results
        except Exception as e:
            logger.warning(f"Qdrant retrieval failed for {domain_enum.value}, using mock: {e}")
        
        # Fallback to mock data if domain not yet indexed
        return await self._retrieve_mock_data(domain_enum, query, top_k)

    async def _retrieve_from_qdrant(self, query: str, top_k: int, domain: str = "marketing") -> List[Citation]:
        """
        Retrieve documents from Qdrant using hybrid search with Redis caching.
        
        Caching layers:
        1. Check query result cache (doc IDs) - FASTEST
        2. If miss: Check embedding cache, generate if needed
        3. Search Qdrant with semantic similarity
        4. Cache results for next time
        
        Args:
            query: User query
            top_k: Number of results
            domain: Domain to filter (hr, it, finance, marketing, etc.)
            
        Returns:
            List of citations from Qdrant
        """
        try:
            # Layer 1: Check query result cache (full cache hit)
            cached_result = redis_cache.get_query_result(query, domain)
            if cached_result and cached_result.get("doc_ids"):
                # Fetch documents by IDs from Qdrant
                logger.info(f"🚀 FULL CACHE HIT - Fetching {len(cached_result['doc_ids'])} docs by ID")
                return await self._fetch_by_qdrant_ids(cached_result["doc_ids"], domain)
            
            # Layer 2: Generate/retrieve embedding (partial cache hit)
            cached_embedding = redis_cache.get_embedding(query)
            if cached_embedding:
                query_embedding = cached_embedding
                logger.info("⚡ Embedding from cache")
            else:
                query_embedding = self.embeddings.embed_query(query)
                redis_cache.set_embedding(query, query_embedding)
                logger.info("🔄 New embedding generated and cached")
            
            # Domain filter - only search within specific domain
            domain_filter = Filter(
                must=[
                    FieldCondition(
                        key="domain",
                        match=MatchValue(value=domain.lower())
                    )
                ]
            )
            
            # Layer 3: Qdrant search with cached embedding
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=domain_filter,
                limit=top_k,
                with_payload=True
            )
            
            # Convert to Citations
            citations = []
            doc_ids = []  # For caching
            
            for point in search_results:
                payload = point.payload
                file_id = payload.get("source_file_id") or payload.get("file_id", "UNKNOWN")
                file_name = payload.get("source_file_name") or payload.get("file_name", "Unknown Document")
                chunk_index = payload.get("chunk_index", 0)
                
                citations.append(
                    Citation(
                        doc_id=f"{file_id}#chunk{chunk_index}",
                        title=file_name,
                        score=float(point.score),
                        url=None,
                        content=payload.get("text", "")
                    )
                )
                doc_ids.append(str(point.id))  # Store Qdrant point ID (UUID string)
            
            # Apply feedback-weighted re-ranking (BATCH to avoid connection pool exhaustion)
            if postgres_client.is_available() and citations:
                logger.info("🎯 Applying feedback-weighted re-ranking...")
                logger.debug(f"🔍 Retrieved {len(citations)} citations from Qdrant, checking feedback...")
                
                # Batch fetch all feedback percentages in ONE query
                citation_ids = [c.doc_id for c in citations]
                logger.debug(f"🔍 Calling get_citation_feedback_batch for {len(citation_ids)} IDs")
                feedback_map = await postgres_client.get_citation_feedback_batch(
                    citation_ids,
                    domain
                )
                logger.debug(f"✅ Received feedback for {len(feedback_map)} citations")
                
                # Apply boosts to each citation
                for citation in citations:
                    like_pct = feedback_map.get(citation.doc_id)  # None if no feedback
                    boost = calculate_feedback_boost(like_pct)
                    
                    original_score = citation.score
                    citation.score = original_score * (1 + boost)
                    
                    if like_pct is not None:
                        logger.debug(
                            f"📊 {citation.doc_id}: "
                            f"semantic={original_score:.3f}, "
                            f"feedback={like_pct:.1f}%, "
                            f"boost={boost:+.1f}, "
                            f"final={citation.score:.3f}"
                        )
                
                # Re-sort by boosted score
                citations.sort(key=lambda c: c.score, reverse=True)
                logger.info(f"✅ Re-ranked {len(citations)} citations by feedback-weighted scores")
            else:
                logger.warning("⚠️ PostgreSQL unavailable, skipping feedback ranking")
            
            # Layer 4: Cache query results
            if citations:
                metadata = {
                    "top_score": citations[0].score,
                    "result_count": len(citations),
                    "top_k": top_k
                }
                redis_cache.set_query_result(query, domain, doc_ids, metadata)
                logger.info(f"💾 Cached {len(doc_ids)} doc IDs for future queries")
            
            logger.info(f"Retrieved {len(citations)} docs from Qdrant (domain={domain}) for query: {query[:50]}...")
            return citations
            
        except Exception as e:
            logger.error(f"Qdrant retrieval error: {e}", exc_info=True)
            return []
    
    async def _fetch_by_qdrant_ids(self, point_ids: List[str], domain: str) -> List[Citation]:
        """
        Fetch documents directly by Qdrant point IDs (for cache hits).
        
        Args:
            point_ids: List of Qdrant point IDs (UUID strings)
            domain: Domain filter (for logging)
            
        Returns:
            List of citations
        """
        try:
            # Retrieve points by IDs
            points = self.qdrant_client.retrieve(
                collection_name=self.collection_name,
                ids=point_ids,
                with_payload=True,
                with_vectors=False  # Don't need vectors
            )
            
            # Convert to Citations (maintain order from cache)
            id_to_point = {p.id: p for p in points}
            citations = []
            
            for point_id in point_ids:
                point = id_to_point.get(point_id)
                if not point:
                    logger.warning(f"Point ID {point_id} not found in Qdrant")
                    continue
                
                payload = point.payload
                file_id = payload.get("source_file_id") or payload.get("file_id", "UNKNOWN")
                file_name = payload.get("source_file_name") or payload.get("file_name", "Unknown Document")
                chunk_index = payload.get("chunk_index", 0)
                
                citations.append(
                    Citation(
                        doc_id=f"{file_id}#chunk{chunk_index}",
                        title=file_name,
                        score=1.0,  # No score from retrieve, use 1.0
                        url=None,
                        content=payload.get("text", "")
                    )
                )
            
            logger.info(f"✅ Fetched {len(citations)}/{len(point_ids)} cached docs from Qdrant (domain={domain})")
            return citations
            
        except Exception as e:
            logger.error(f"Qdrant fetch by IDs error: {e}", exc_info=True)
            return []

    async def _retrieve_mock_data(self, domain: DomainType, query: str, top_k: int) -> List[Citation]:
        """
        Fallback mock data for non-marketing domains.
        TODO: Implement Qdrant collections for other domains.
        """
        mock_kb = {
            DomainType.HR: [
                Citation(
                    doc_id="HR-POL-001",
                    title="Vacation Policy",
                    score=0.94,
                    url=None,
                    content="Szabadságkérés minimum 2 héttel előre kell jelezni. Éves szabadság: 25 munkanap."
                ),
                Citation(
                    doc_id="HR-POL-002",
                    title="Benefits Package",
                    score=0.88,
                    url=None,
                    content="Egészségügyi biztosítás, cafeteria rendszer, home office lehetőség."
                ),
            ],
            DomainType.IT: [
                Citation(
                    doc_id="IT-KB-234",
                    title="VPN Troubleshooting Guide",
                    score=0.91,
                    url=None,
                    content="VPN problémák: 1. Ellenőrizd a kliens fut-e 2. Újraindítás 3. IT helpdesk"
                ),
                Citation(
                    doc_id="IT-KB-189",
                    title="VPN Client Installation",
                    score=0.87,
                    url=None,
                    content="VPN kliens telepítés: Cisco AnyConnect letöltése, telepítés, konfiguráció."
                ),
            ],
            DomainType.FINANCE: [
                Citation(
                    doc_id="FIN-POL-010",
                    title="Expense Report Guidelines",
                    score=0.92,
                    url=None,
                    content="Költségelszámolás: számla szükséges, jóváhagyás 5 munkanapon belül."
                ),
            ],
        }
        
        docs = mock_kb.get(domain, [])
        logger.info(f"Retrieved {len(docs[:top_k])} mock docs for domain={domain.value}")
        return docs[:top_k]
