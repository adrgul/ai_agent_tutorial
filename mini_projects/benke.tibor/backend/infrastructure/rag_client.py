"""
Infrastructure - Mock RAG client for development (Qdrant integration ready).
"""
import logging
from typing import List, Dict, Any, Optional

from domain.models import Citation, DomainType
from domain.interfaces import IRAGClient
from infrastructure.postgres_client import postgres_client

logger = logging.getLogger(__name__)


def calculate_feedback_boost(like_percentage: Optional[float]) -> float:
    """
    Calculate multiplicative boost factor based on user feedback.
    Same formula as QdrantRAGClient for consistency.
    
    Args:
        like_percentage: Percentage of likes (0-100) or None if no feedback
        
    Returns:
        Boost factor: -0.2 to +0.3
    """
    if like_percentage is None:
        return 0.0  # Neutral for new content
    
    if like_percentage > 70:
        return 0.3  # High quality boost
    elif like_percentage >= 40:
        return 0.1  # Moderate boost
    else:
        return -0.2  # Quality penalty


class MockQdrantClient(IRAGClient):
    """
    Mock Qdrant RAG client for development.
    In production, this would connect to real Qdrant vector DB.
    """

    def __init__(self):
        # Mock knowledge base - domain-specific documents
        self.knowledge_base = {
            DomainType.HR: [
                {
                    "doc_id": "HR-POL-001",
                    "title": "Vacation Policy",
                    "content": "Szabadságkérés minimum 2 héttel előre kell jelezni...",
                    "score": 0.94
                },
                {
                    "doc_id": "HR-POL-002",
                    "title": "Benefits Package",
                    "content": "Egészségügyi biztosítás, 25 nap szabadság...",
                    "score": 0.88
                },
            ],
            DomainType.IT: [
                {
                    "doc_id": "IT-KB-234",
                    "title": "VPN Troubleshooting Guide",
                    "content": "VPN problémák: 1. Ellenőrizd a kliens fut-e...",
                    "score": 0.91
                },
                {
                    "doc_id": "IT-KB-189",
                    "title": "VPN Client Installation",
                    "content": "VPN kliens telepítés lépésről lépésre...",
                    "score": 0.87
                },
            ],
            DomainType.FINANCE: [
                {
                    "doc_id": "FIN-POL-010",
                    "title": "Expense Report Guidelines",
                    "content": "Költségvetési nyilvántartási szabályok...",
                    "score": 0.92
                },
            ],
            DomainType.MARKETING: [
                {
                    "doc_id": "BRAND-v3.2",
                    "title": "Brand Guidelines v3.2",
                    "content": """Brand Guidelines v3.2 - Teljes útmutató
                    
1. Színpaletta
- Elsődleges szín: #10a37f (zöld)
- Másodlagos szín: #1a1a1a (sötétszürke)
- Kiegészítő szín: #ececf1 (világosszürke)

2. Tipográfia
- Főbetűtípus: Arial, Regular, 12pt.
- Címek: Arial Bold, 16pt.
- Egyéb betűtípusok: Használj maximalisan 2-3 különböző betűtípust a tiszta és egységes megjelenés érdekében.

3. Logóhasználat
- A logó mindig tiszta háttéren jelenjen meg
- Minimum méret: 48x48 pixel
- Védőterület: 10px minden oldalon

4. Képhasználat
- Stílus: A képek legyenek professzionálisak, tükrözzék a cég értékeit.
- Minőség: Mindig használj HD minőségű képeket, kerüld az alacsony felbontású képeket.

5. Hangvétel és kommunikáció
- Írásbeli kommunikáció: Barátságos, de professzionális hangvétel.
- Szóhasználat: Kerüld a túlzott szakmai zsargont, a cél közönség számára érthető nyelvezetet használj.

6. Alkalmazás platformok
- Weboldal: A weboldalon a brand guideline összes elemét követni kell, beleértve a színpalettát és a betűtípusokat.
- Közösségi média: A közösségi médiában a brand elemek egységes alkalmazása szükséges a márka arculatának megőrzése érdekében.

Ezek az irányelvek segítik a márkánk egységes megjelenését és kommunikációját minden platformon. Kérjük, hogy minden munkatárs tartsa be ezeket a szabályokat a brand integritásának megőrzése érdekében. Ha további részletekre van szükséged, kérlek, jelezd!""",
                    "score": 0.97
                },
            ],
        }

    async def retrieve_for_domain(
        self, domain: str, query: str, top_k: int = 5
    ) -> List[Citation]:
        """
        Retrieve relevant documents for a domain.
        Mock implementation returns docs from knowledge base.
        """
        try:
            domain_enum = DomainType(domain.lower())
        except ValueError:
            domain_enum = DomainType.GENERAL

        docs = self.knowledge_base.get(domain_enum, [])
        
        # Simple mock scoring based on keyword matching
        scored_docs = []
        for doc in docs:
            # Check if query keywords appear in document
            if any(keyword in doc["content"].lower() for keyword in query.lower().split()):
                scored_docs.append(doc)
        
        # If no keyword match, return top docs anyway
        if not scored_docs:
            scored_docs = docs[:top_k]
        
        # Convert to Citations
        citations = [
            Citation(
                doc_id=doc["doc_id"],
                title=doc["title"],
                score=doc.get("score", 0.5),
                url=None
            )
            for doc in scored_docs[:top_k]
        ]
        
        # Apply feedback-weighted re-ranking (same as QdrantRAGClient)
        logger.info(f"🔍 DEBUG: postgres_client.pool = {postgres_client.pool}")
        logger.info(f"🔍 DEBUG: postgres_client.is_available() = {postgres_client.is_available()}")
        
        if postgres_client.is_available():
            logger.info("🎯 Applying feedback-weighted re-ranking (MockQdrantClient)...")
            
            # Use asgiref.sync to call async function from sync context
            from asgiref.sync import async_to_sync
            
            for citation in citations:
                # Fetch feedback percentage (sync wrapper for async method)
                like_pct = async_to_sync(postgres_client.get_citation_feedback_percentage)(
                    citation.doc_id,
                    domain
                )
                
                # Calculate boost factor
                boost = calculate_feedback_boost(like_pct)
                
                # Apply boost to score
                original_score = citation.score
                citation.score = original_score * (1 + boost)
                
                if like_pct is not None:
                    logger.info(
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
        
        logger.info(f"Retrieved {len(citations)} docs for domain={domain}")
        return citations
