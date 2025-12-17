"""
Infrastructure - Mock RAG client for development (Qdrant integration ready).
"""
import logging
from typing import List, Dict, Any, Optional

from domain.models import Citation, DomainType
from domain.interfaces import IRAGClient

logger = logging.getLogger(__name__)


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
        
        logger.info(f"Retrieved {len(citations)} docs for domain={domain}")
        return citations
