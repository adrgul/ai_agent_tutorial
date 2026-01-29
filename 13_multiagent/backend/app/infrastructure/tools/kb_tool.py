"""Knowledge base retrieval tool (RAG) with semantic search."""
from typing import List, Dict, Any
import hashlib
import numpy as np
from app.infrastructure.cache.memory_cache import kb_cache
from app.domain.events import TraceEvent
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


# Mock knowledge base articles
KNOWLEDGE_BASE = [
    {
        "id": "KB-001",
        "title": "Billing Policy",
        "content": "Our billing policy covers payment methods, billing cycles, and charge disputes. "
                  "Charges appear within 1-3 business days. For billing inquiries, contact billing@support.com.",
        "category": "Billing",
        "tags": ["billing", "payments", "charges"],
    },
    {
        "id": "KB-002",
        "title": "Account Security Best Practices",
        "content": "Protect your account with strong passwords, enable 2FA, and never share credentials. "
                  "If you suspect unauthorized access, immediately reset your password and contact security@support.com.",
        "category": "Account",
        "tags": ["security", "account", "password", "2fa"],
    },
    {
        "id": "KB-003",
        "title": "Troubleshooting Guide",
        "content": "Common troubleshooting steps: 1) Clear browser cache and cookies, "
                  "2) Update to the latest version, 3) Check internet connection, "
                  "4) Disable browser extensions, 5) Try a different browser.",
        "category": "Technical",
        "tags": ["troubleshooting", "technical", "errors"],
    },
    {
        "id": "KB-004",
        "title": "Shipping Policy",
        "content": "Standard shipping: 5-7 business days. Expedited: 2-3 business days. "
                  "International: 10-15 business days. Tracking numbers sent via email. "
                  "Free shipping on orders over $50.",
        "category": "Shipping",
        "tags": ["shipping", "delivery", "tracking"],
    },
    {
        "id": "KB-005",
        "title": "Refund Guidelines",
        "content": "Refunds processed within 5-10 business days. Eligible items must be unused "
                  "and returned within 30 days. Digital products are non-refundable. "
                  "Refund disputes over $100 require manager approval.",
        "category": "Refund",
        "tags": ["refund", "returns", "money-back"],
    },
    {
        "id": "KB-006",
        "title": "Password Reset",
        "content": "To reset your password: 1) Click 'Forgot Password' on login page, "
                  "2) Enter your email, 3) Check email for reset link (valid 24 hours), "
                  "4) Create new password (min 8 characters, include numbers and symbols).",
        "category": "Account",
        "tags": ["password", "reset", "account"],
    },
    {
        "id": "KB-007",
        "title": "Common Error Codes",
        "content": "Error 400: Invalid request - check your input. "
                  "Error 401: Authentication required - please log in. "
                  "Error 404: Resource not found - check the URL. "
                  "Error 500: Server error - we're working on it.",
        "category": "Technical",
        "tags": ["errors", "error codes", "technical"],
    },
    {
        "id": "KB-008",
        "title": "Tracking Your Order",
        "content": "Track your order using the tracking number in your confirmation email. "
                  "Updates available 24 hours after shipment. Contact shipping@support.com for issues.",
        "category": "Shipping",
        "tags": ["tracking", "shipping", "orders"],
    },
]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    return float(np.dot(vec1_np, vec2_np) / (np.linalg.norm(vec1_np) * np.linalg.norm(vec2_np)))


def retrieve_kb_articles(query: str, top_k: int = 3) -> tuple[List[Dict[str, Any]], TraceEvent]:
    """
    Retrieve relevant knowledge base articles using semantic search with OpenAI embeddings.
    
    Args:
        query: User query
        top_k: Number of articles to retrieve
        
    Returns:
        Tuple of (articles list, trace event)
    """
    # Generate cache key
    cache_key = hashlib.md5(f"{query}:{top_k}".encode()).hexdigest()
    
    # Check cache
    cached = kb_cache.get(cache_key)
    if cached:
        return cached, TraceEvent.cache_hit({"cache_type": "kb_retrieval", "query": query[:50]})
    
    try:
        # Get query embedding using OpenAI
        llm = OpenAIProvider()
        query_embedding = llm.get_embeddings(query)
        
        # Calculate similarities with all articles
        scored_articles = []
        
        for article in KNOWLEDGE_BASE:
            # Create article text for embedding
            article_text = f"{article['title']} {article['content']} {' '.join(article['tags'])}"
            
            # Get article embedding
            article_embedding = llm.get_embeddings(article_text)
            
            # Calculate similarity
            similarity = cosine_similarity(query_embedding, article_embedding)
            scored_articles.append((similarity, article))
        
        # Sort by similarity and get top-k
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        results = [article for _, article in scored_articles[:top_k]]
        
        logger.info(f"Retrieved {len(results)} KB articles using semantic search")
        
    except Exception as e:
        logger.warning(f"Semantic search failed: {e}. Falling back to keyword search")
        # Fallback to keyword-based search if embeddings fail
        query_lower = query.lower()
        scored_articles = []
        
        for article in KNOWLEDGE_BASE:
            score = 0
            if any(word in article["title"].lower() for word in query_lower.split()):
                score += 3
            if any(word in article["content"].lower() for word in query_lower.split()):
                score += 1
            if any(tag in query_lower for tag in article["tags"]):
                score += 2
            
            if score > 0:
                scored_articles.append((score, article))
        
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        results = [article for _, article in scored_articles[:top_k]]
        
        if not results:
            results = [KNOWLEDGE_BASE[0]]
    
    # Cache the result
    kb_cache.set(cache_key, results)
    
    trace_event = TraceEvent.cache_miss({
        "cache_type": "kb_retrieval",
        "query": query[:50],
        "results_count": len(results)
    })
    
    return results, trace_event


def format_kb_sources(articles: List[Dict[str, Any]]) -> List[str]:
    """Format KB articles as citation sources."""
    return [f"{article['id']}: {article['title']}" for article in articles]


def get_all_kb_articles() -> List[Dict[str, Any]]:
    """Get all KB articles for demo/UI purposes."""
    return KNOWLEDGE_BASE
