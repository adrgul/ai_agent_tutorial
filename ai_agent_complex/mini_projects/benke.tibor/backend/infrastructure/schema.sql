-- KnowledgeRouter Feedback Database Schema
-- PostgreSQL 15+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Citation feedback table
CREATE TABLE IF NOT EXISTS citation_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    citation_id VARCHAR(255) NOT NULL,  -- Qdrant point ID
    domain VARCHAR(50) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    query_text TEXT NOT NULL,
    query_embedding FLOAT8[],  -- 1536-dimensional array for OpenAI embeddings
    feedback_type VARCHAR(10) NOT NULL CHECK (feedback_type IN ('like', 'dislike')),
    citation_rank INTEGER,  -- Position in results (1-5)
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Indexes for common queries
    CONSTRAINT citation_feedback_user_citation UNIQUE (user_id, citation_id, session_id)
);

-- Response-level feedback table
CREATE TABLE IF NOT EXISTS response_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    query_text TEXT NOT NULL,
    domain VARCHAR(50) NOT NULL,
    feedback_type VARCHAR(10) NOT NULL CHECK (feedback_type IN ('like', 'dislike')),
    comment TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- One feedback per session response
    CONSTRAINT response_feedback_session UNIQUE (session_id)
);

-- Indexes for citation_feedback
CREATE INDEX IF NOT EXISTS idx_citation_feedback_citation_id ON citation_feedback(citation_id);
CREATE INDEX IF NOT EXISTS idx_citation_feedback_domain ON citation_feedback(domain);
CREATE INDEX IF NOT EXISTS idx_citation_feedback_user_id ON citation_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_citation_feedback_timestamp ON citation_feedback(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_citation_feedback_type ON citation_feedback(feedback_type);

-- Indexes for response_feedback
CREATE INDEX IF NOT EXISTS idx_response_feedback_domain ON response_feedback(domain);
CREATE INDEX IF NOT EXISTS idx_response_feedback_user_id ON response_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_response_feedback_timestamp ON response_feedback(timestamp DESC);

-- Materialized view for citation statistics (for fast analytics)
CREATE MATERIALIZED VIEW IF NOT EXISTS citation_stats AS
SELECT 
    citation_id,
    domain,
    COUNT(*) as total_feedback,
    SUM(CASE WHEN feedback_type = 'like' THEN 1 ELSE 0 END) as like_count,
    SUM(CASE WHEN feedback_type = 'dislike' THEN 1 ELSE 0 END) as dislike_count,
    ROUND(
        (CAST(SUM(CASE WHEN feedback_type = 'like' THEN 1 ELSE 0 END) AS NUMERIC) / 
        NULLIF(COUNT(*), 0) * 100)::NUMERIC, 
        2
    ) as like_percentage,
    MAX(timestamp) as last_feedback_at
FROM citation_feedback
GROUP BY citation_id, domain;

-- Index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_citation_stats_pk ON citation_stats(citation_id, domain);
CREATE INDEX IF NOT EXISTS idx_citation_stats_like_pct ON citation_stats(like_percentage DESC);

-- Function to refresh citation stats
CREATE OR REPLACE FUNCTION refresh_citation_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY citation_stats;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE citation_feedback IS 'User feedback on individual citations (like/dislike)';
COMMENT ON TABLE response_feedback IS 'User feedback on complete responses';
COMMENT ON COLUMN citation_feedback.query_embedding IS 'OpenAI embedding for context-aware feedback aggregation';
COMMENT ON COLUMN citation_feedback.citation_rank IS 'Position of citation in search results (1=top)';
COMMENT ON MATERIALIZED VIEW citation_stats IS 'Aggregated citation feedback statistics (refresh periodically)';
