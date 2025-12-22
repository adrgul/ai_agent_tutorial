"""
Domain interfaces - abstract base classes for repositories and clients.

Follows SOLID principles for better testability and flexibility.
Inspired by vector_embeddings/app clean architecture patterns.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .models import Message, Citation, UserProfile


# ============================================================================
# Repository Interfaces
# ============================================================================

class IUserRepository(ABC):
    """User profile storage interface."""

    @abstractmethod
    async def get_profile(self, user_id: str) -> UserProfile:
        pass

    @abstractmethod
    async def save_profile(self, profile: UserProfile) -> UserProfile:
        pass

    @abstractmethod
    async def update_profile(self, user_id: str, updates: Dict[str, Any]) -> UserProfile:
        pass


class IConversationRepository(ABC):
    """Conversation history storage interface."""

    @abstractmethod
    async def get_history(self, session_id: str) -> List[Message]:
        pass

    @abstractmethod
    async def save_message(self, session_id: str, message: Message) -> None:
        pass

    @abstractmethod
    async def clear_history(self, session_id: str) -> None:
        pass

    @abstractmethod
    async def search_messages(self, query: str) -> List[Message]:
        pass


# ============================================================================
# Embedding Service Interface
# ============================================================================

class IEmbeddingService(ABC):
    """
    Abstract interface for text embedding generation.
    
    Allows swapping embedding providers (OpenAI, Cohere, HuggingFace, etc.)
    without changing dependent code.
    
    Follows Open/Closed Principle and Dependency Inversion Principle.
    """
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        pass
    
    @abstractmethod
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch operation).
        
        More efficient than multiple get_embedding() calls.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if embedding service is available and healthy.
        
        Returns:
            True if service is ready, False otherwise
        """
        pass


# ============================================================================
# Vector Store Interface
# ============================================================================

class IVectorStore(ABC):
    """
    Abstract interface for vector database operations.
    
    Allows swapping vector stores (Qdrant, Pinecone, Weaviate, Chroma, etc.)
    without changing RAG client logic.
    """

    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 5) -> List[Citation]:
        """
        Simple retrieval without domain filtering.
        
        Args:
            query: Search query text
            top_k: Maximum number of results
            
        Returns:
            List of Citations
        """
        pass

    @abstractmethod
    async def upsert(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """
        Insert or update a document in the vector store.
        
        Args:
            doc_id: Unique document identifier
            content: Document text content
            metadata: Additional metadata (domain, title, etc.)
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        collection: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search with embedding vector.
        
        Args:
            query_embedding: Query vector
            collection: Collection/index name
            limit: Maximum number of results
            filters: Optional metadata filters (e.g., {"domain": "marketing"})
            
        Returns:
            List of search results with scores and metadata
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if vector store is available and healthy.
        
        Returns:
            True if store is ready, False otherwise
        """
        pass


# ============================================================================
# Feedback Store Interface
# ============================================================================

class IFeedbackStore(ABC):
    """
    Abstract interface for feedback persistence and retrieval.
    
    Allows swapping feedback stores (PostgreSQL, MongoDB, Redis, etc.)
    without changing feedback ranking logic.
    """
    
    @abstractmethod
    async def get_citation_feedback_batch(
        self,
        citation_ids: List[str],
        domain: str
    ) -> Dict[str, float]:
        """
        Get feedback percentages for multiple citations (batch operation).
        
        Optimized to avoid N+1 query problem.
        
        Args:
            citation_ids: List of citation identifiers
            domain: Domain filter
            
        Returns:
            Dict mapping citation_id → like_percentage (0-100)
        """
        pass
    
    @abstractmethod
    async def get_citation_feedback_percentage(
        self,
        citation_id: str,
        domain: str
    ) -> Optional[float]:
        """
        Get feedback percentage for a single citation.
        
        Args:
            citation_id: Citation identifier
            domain: Domain filter
            
        Returns:
            Like percentage (0-100) or None if no feedback exists
        """
        pass
    
    @abstractmethod
    async def record_feedback(
        self,
        citation_id: str,
        domain: str,
        feedback_type: str,
        user_id: Optional[str] = None
    ) -> None:
        """
        Record user feedback for a citation.
        
        Args:
            citation_id: Citation identifier
            domain: Domain name
            feedback_type: 'like' or 'dislike'
            user_id: Optional user identifier
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if feedback store is available and healthy.
        
        Returns:
            True if store is ready, False otherwise
        """
        pass


# ============================================================================
# RAG Client Interface
# ============================================================================

class IRAGClient(ABC):
    """
    Abstract interface for RAG (Retrieval-Augmented Generation) operations.
    
    Orchestrates embedding generation, vector search, and optional feedback ranking.
    """

    @abstractmethod
    async def retrieve_for_domain(self, domain: str, query: str, top_k: int = 5) -> List[Citation]:
        """
        Retrieve relevant citations for a domain-specific query.
        
        Args:
            domain: Domain filter (marketing, IT, HR, finance, etc.)
            query: User query text
            top_k: Number of results to return
            
        Returns:
            List of Citations ranked by relevance
        """
        pass
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        domain: str,
        top_k: int = 5,
        apply_feedback_boost: bool = True
    ) -> List[Citation]:
        """
        Advanced retrieval with optional feedback-weighted ranking.
        
        Args:
            query: User query text
            domain: Domain filter
            top_k: Number of results to return
            apply_feedback_boost: Whether to apply feedback-based ranking
            
        Returns:
            List of Citations ranked by semantic similarity + feedback
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if RAG client is available and healthy.
        
        Returns:
            True if client is ready (vector store + embedding service OK)
        """
        pass


# ============================================================================
# Type Aliases for Clarity
# ============================================================================

EmbeddingVector = List[float]
CitationID = str
FeedbackPercentage = float
DomainName = str
