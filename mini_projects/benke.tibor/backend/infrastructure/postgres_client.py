"""
Postgres client for feedback storage and retrieval.
"""
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg
from contextlib import asynccontextmanager

from domain.models import CitationFeedback, ResponseFeedback, FeedbackStats, FeedbackType

logger = logging.getLogger(__name__)


class PostgresClient:
    """Async PostgreSQL client for feedback management."""
    
    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "knowledgerouter")
        self.user = os.getenv("POSTGRES_USER", "kruser")
        self.password = os.getenv("POSTGRES_PASSWORD", "krpass123")
        self.pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self):
        """Create connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info(f"✅ Postgres connection pool created ({self.host}:{self.port}/{self.database})")
        except Exception as e:
            logger.error(f"❌ Failed to create Postgres pool: {e}")
            raise
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Postgres connection pool closed")
    
    def is_available(self) -> bool:
        """Check if Postgres is available."""
        return self.pool is not None
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool."""
        if not self.pool:
            raise RuntimeError("PostgresClient not initialized. Call initialize() first.")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    async def get_standalone_connection(self):
        """
        Create standalone connection (NOT from pool).
        Use this for background threads where pool may not be thread-safe.
        Caller must close the connection.
        """
        return await asyncpg.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )
    
    # ==================== Citation Feedback ====================
    
    async def save_citation_feedback(self, feedback: CitationFeedback) -> str:
        """
        Save citation feedback to database.
        
        Args:
            feedback: CitationFeedback model
            
        Returns:
            UUID string of created feedback record
        """
        try:
            async with self.get_connection() as conn:
                # Convert embedding list to PostgreSQL array format
                embedding_array = feedback.query_embedding if feedback.query_embedding else None
                
                row = await conn.fetchrow(
                    """
                    INSERT INTO citation_feedback (
                        citation_id, domain, user_id, session_id, query_text,
                        query_embedding, feedback_type, citation_rank, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (user_id, citation_id, session_id)
                    DO UPDATE SET
                        feedback_type = EXCLUDED.feedback_type,
                        timestamp = EXCLUDED.timestamp
                    RETURNING id
                    """,
                    feedback.citation_id,
                    feedback.domain,
                    feedback.user_id,
                    feedback.session_id,
                    feedback.query_text,
                    embedding_array,
                    feedback.feedback_type.value,
                    feedback.citation_rank,
                    datetime.now()
                )
                
                return str(row["id"])
        
        except Exception as e:
            logger.error(f"❌ Failed to save citation feedback: {e}")
            raise
    
    async def save_citation_feedback_standalone(self, feedback: CitationFeedback) -> str:
        """
        Save citation feedback using standalone connection (thread-safe).
        Use this for background threads.
        """
        conn = None
        try:
            conn = await self.get_standalone_connection()
            
            embedding_array = feedback.query_embedding if feedback.query_embedding else None
            
            row = await conn.fetchrow(
                """
                INSERT INTO citation_feedback (
                    citation_id, domain, user_id, session_id, query_text,
                    query_embedding, feedback_type, citation_rank, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (user_id, citation_id, session_id)
                DO UPDATE SET
                    feedback_type = EXCLUDED.feedback_type,
                    timestamp = EXCLUDED.timestamp
                RETURNING id
                """,
                feedback.citation_id,
                feedback.domain,
                feedback.user_id,
                feedback.session_id,
                feedback.query_text,
                embedding_array,
                feedback.feedback_type.value,
                feedback.citation_rank,
                datetime.now()
            )
            
            return str(row["id"])
        
        except Exception as e:
            logger.error(f"❌ Failed to save citation feedback (standalone): {e}")
            raise
        
        finally:
            if conn:
                await conn.close()
    
    async def get_citation_feedbacks(
        self,
        citation_id: Optional[str] = None,
        domain: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[CitationFeedback]:
        """
        Retrieve citation feedbacks with optional filters.
        
        Args:
            citation_id: Filter by citation ID
            domain: Filter by domain
            user_id: Filter by user ID
            limit: Maximum results
            
        Returns:
            List of CitationFeedback models
        """
        try:
            query = "SELECT * FROM citation_feedback WHERE 1=1"
            params = []
            param_count = 1
            
            if citation_id:
                query += f" AND citation_id = ${param_count}"
                params.append(citation_id)
                param_count += 1
            
            if domain:
                query += f" AND domain = ${param_count}"
                params.append(domain)
                param_count += 1
            
            if user_id:
                query += f" AND user_id = ${param_count}"
                params.append(user_id)
                param_count += 1
            
            query += f" ORDER BY timestamp DESC LIMIT ${param_count}"
            params.append(limit)
            
            async with self.get_connection() as conn:
                rows = await conn.fetch(query, *params)
                
                feedbacks = [
                    CitationFeedback(
                        id=str(row["id"]),
                        citation_id=row["citation_id"],
                        domain=row["domain"],
                        user_id=row["user_id"],
                        session_id=row["session_id"],
                        query_text=row["query_text"],
                        query_embedding=list(row["query_embedding"]) if row["query_embedding"] else None,
                        feedback_type=FeedbackType(row["feedback_type"]),
                        citation_rank=row["citation_rank"],
                        timestamp=row["timestamp"]
                    )
                    for row in rows
                ]
                
                return feedbacks
                
        except Exception as e:
            logger.error(f"❌ Failed to retrieve citation feedbacks: {e}")
            return []
    
    async def get_citation_score(
        self,
        citation_id: str,
        domain: str,
        current_query_embedding: Optional[List[float]] = None,
        similarity_threshold: float = 0.7
    ) -> float:
        """
        Calculate aggregated feedback score for a citation.
        
        Args:
            citation_id: Citation to score
            domain: Domain context
            current_query_embedding: Optional query embedding for context-aware scoring
            similarity_threshold: Min similarity for relevant feedback (0-1)
            
        Returns:
            Score between -1 and 1 (-1 = all dislikes, 1 = all likes, 0 = neutral)
        """
        try:
            feedbacks = await self.get_citation_feedbacks(citation_id=citation_id, domain=domain)
            
            if not feedbacks:
                return 0.0
            
            # If query embedding provided, filter by similarity
            if current_query_embedding and feedbacks[0].query_embedding:
                # TODO: Implement cosine similarity filtering
                # For now, use all feedbacks
                pass
            
            # Calculate score: like = +1, dislike = -1
            total_score = sum(
                1 if fb.feedback_type == FeedbackType.LIKE else -1
                for fb in feedbacks
            )
            
            # Normalize to -1 to 1 range
            normalized_score = total_score / len(feedbacks)
            
            return normalized_score
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate citation score: {e}")
            return 0.0
    
    # ==================== Response Feedback ====================
    
    async def save_response_feedback(self, feedback: ResponseFeedback) -> str:
        """Save response-level feedback."""
        try:
            async with self.get_connection() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO response_feedback (
                        user_id, session_id, query_text, domain, feedback_type, comment, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (session_id)
                    DO UPDATE SET
                        feedback_type = EXCLUDED.feedback_type,
                        comment = EXCLUDED.comment,
                        timestamp = EXCLUDED.timestamp
                    RETURNING id
                    """,
                    feedback.user_id,
                    feedback.session_id,
                    feedback.query_text,
                    feedback.domain,
                    feedback.feedback_type.value,
                    feedback.comment,
                    feedback.timestamp
                )
                
                feedback_id = str(row["id"])
                logger.info(f"💾 Response feedback saved: {feedback_id} ({feedback.feedback_type.value})")
                return feedback_id
                
        except Exception as e:
            logger.error(f"❌ Failed to save response feedback: {e}")
            raise
    
    # ==================== Analytics ====================
    
    async def get_feedback_stats(self, domain: Optional[str] = None) -> FeedbackStats:
        """
        Get aggregated feedback statistics.
        
        Args:
            domain: Optional domain filter
            
        Returns:
            FeedbackStats model with aggregated data
        """
        try:
            async with self.get_connection() as conn:
                # Overall stats
                query = """
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN feedback_type = 'like' THEN 1 ELSE 0 END) as likes,
                        SUM(CASE WHEN feedback_type = 'dislike' THEN 1 ELSE 0 END) as dislikes
                    FROM citation_feedback
                """
                params = []
                
                if domain:
                    query += " WHERE domain = $1"
                    params.append(domain)
                
                row = await conn.fetchrow(query, *params)
                
                total = row["total"] or 0
                likes = row["likes"] or 0
                dislikes = row["dislikes"] or 0
                like_ratio = likes / total if total > 0 else 0.0
                
                # Top liked/disliked citations
                top_liked = await conn.fetch(
                    """
                    SELECT citation_id, domain, like_count, total_feedback
                    FROM citation_stats
                    WHERE like_percentage > 50
                    ORDER BY like_count DESC
                    LIMIT 10
                    """
                )
                
                top_disliked = await conn.fetch(
                    """
                    SELECT citation_id, domain, dislike_count, total_feedback
                    FROM citation_stats
                    WHERE like_percentage < 50
                    ORDER BY dislike_count DESC
                    LIMIT 10
                    """
                )
                
                return FeedbackStats(
                    total_feedbacks=total,
                    like_count=likes,
                    dislike_count=dislikes,
                    like_ratio=like_ratio,
                    top_liked_citations=[dict(row) for row in top_liked],
                    top_disliked_citations=[dict(row) for row in top_disliked]
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to get feedback stats: {e}")
            return FeedbackStats(
                total_feedbacks=0,
                like_count=0,
                dislike_count=0,
                like_ratio=0.0
            )
    
    async def refresh_stats(self):
        """Refresh materialized view for citation statistics."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("SELECT refresh_citation_stats()")
                logger.info("📊 Citation stats refreshed")
        except Exception as e:
            logger.error(f"❌ Failed to refresh stats: {e}")


# Global instance
postgres_client = PostgresClient()
