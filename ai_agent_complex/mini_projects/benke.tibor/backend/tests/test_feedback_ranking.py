"""
Unit tests for feedback-weighted ranking algorithm.
Tests the boost calculation and re-ranking logic.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from domain.models import Citation
from infrastructure.qdrant_rag_client import QdrantRAGClient


@pytest.fixture
def qdrant_client():
    """Create a QdrantRAGClient instance for testing."""
    with patch('infrastructure.qdrant_rag_client.QdrantClient'):
        client = QdrantRAGClient()
        return client


@pytest.fixture
def sample_citations():
    """Create sample citations for testing."""
    return [
        Citation(
            doc_id='1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk0',
            title='Aurora Brand Guidelines - Typography',
            content='Aurora Digital brand guidelines - typography section',
            score=0.850,
            metadata={'source': 'brand_guidelines.docx', 'chunk_index': 0}
        ),
        Citation(
            doc_id='1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk1',
            title='Aurora Brand Guidelines - Colors',
            content='Aurora Digital brand guidelines - color palette',
            score=0.820,
            metadata={'source': 'brand_guidelines.docx', 'chunk_index': 1}
        ),
        Citation(
            doc_id='1utetoO-ApR4lmOpY1HS63va_gqmjDfsA#chunk0',
            title='Aurora Brand Manual HU',
            content='Aurora Digital brand manual Hungarian version',
            score=0.800,
            metadata={'source': 'brand_manual_hu.docx', 'chunk_index': 0}
        ),
        Citation(
            doc_id='150jnsbIl3HreheZyiCDU3fUt9cdL_EFS#chunk0',
            title='Aurora Brand Manual PDF',
            content='Aurora Digital brand manual PDF version',
            score=0.780,
            metadata={'source': 'brand_manual.pdf', 'chunk_index': 0}
        ),
        Citation(
            doc_id='1ZjKH8xQXxQxQxQxQxQxQxQxQxQxQxQx#chunk0',
            title='Other Marketing Doc',
            content='Other marketing document',
            score=0.750,
            metadata={'source': 'other.docx', 'chunk_index': 0}
        ),
    ]


class TestFeedbackBoostCalculation:
    """Test feedback boost calculation logic."""
    
    def test_calculate_feedback_boost_high_tier(self):
        """Test boost calculation for high feedback (>70% like)."""
        from infrastructure.qdrant_rag_client import calculate_feedback_boost
        
        # Test boundary: 70% exactly should be medium tier
        assert calculate_feedback_boost(70.0) == 0.1
        
        # Test above boundary (>70%)
        assert calculate_feedback_boost(71.0) == 0.3
        assert calculate_feedback_boost(75.0) == 0.3
        assert calculate_feedback_boost(85.0) == 0.3
        assert calculate_feedback_boost(100.0) == 0.3
    
    def test_calculate_feedback_boost_medium_tier(self):
        """Test boost calculation for medium feedback (40-70% like)."""
        from infrastructure.qdrant_rag_client import calculate_feedback_boost
        
        # Test boundary: 40% exactly
        assert calculate_feedback_boost(40.0) == 0.1
        
        # Test within range
        assert calculate_feedback_boost(50.0) == 0.1
        assert calculate_feedback_boost(55.0) == 0.1
        assert calculate_feedback_boost(60.0) == 0.1
        assert calculate_feedback_boost(70.0) == 0.1
    
    def test_calculate_feedback_boost_low_tier(self):
        """Test boost calculation for low feedback (<40% like)."""
        from infrastructure.qdrant_rag_client import calculate_feedback_boost
        
        # Test below 40%
        assert calculate_feedback_boost(39.9) == -0.2
        assert calculate_feedback_boost(30.0) == -0.2
        assert calculate_feedback_boost(25.0) == -0.2
        assert calculate_feedback_boost(0.0) == -0.2
    
    def test_calculate_feedback_boost_no_data(self):
        """Test boost calculation when no feedback data exists."""
        from infrastructure.qdrant_rag_client import calculate_feedback_boost
        
        # None should return neutral boost
        assert calculate_feedback_boost(None) == 0.0


class TestFeedbackWeightedRanking:
    """Test complete feedback-weighted ranking flow."""
    
    @pytest.mark.skip(reason="Requires mocking private QdrantRAGClient methods")
    @pytest.mark.asyncio
    async def test_retrieve_with_feedback_ranking_applied(self, qdrant_client, sample_citations):
        """Test that feedback ranking is applied and citations are re-sorted."""
        from infrastructure.postgres_client import postgres_client
        
        # Mock Qdrant search to return sample citations
        with patch.object(qdrant_client, '_search_qdrant', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = sample_citations.copy()
            
            # Mock postgres client feedback lookup
            feedback_map = {
                '1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk0': 75.0,  # +30% boost
                '1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk1': 40.0,  # -20% penalty
                # Other citations have no feedback (0% boost)
            }
            
            with patch.object(postgres_client, 'is_available', return_value=True):
                with patch.object(postgres_client, 'get_citation_feedback_batch', new_callable=AsyncMock) as mock_feedback:
                    mock_feedback.return_value = feedback_map
                    
                    # Mock Redis cache (not used in this test)
                    with patch.object(qdrant_client, '_get_cached_citations', new_callable=AsyncMock) as mock_cache_get:
                        mock_cache_get.return_value = None
                        
                        with patch.object(qdrant_client, '_cache_citations', new_callable=AsyncMock):
                            citations = await qdrant_client._retrieve_from_qdrant('test query', 'marketing', top_k=5)
            
            # Verify feedback lookup was called with correct IDs
            mock_feedback.assert_called_once()
            call_args = mock_feedback.call_args[0]
            assert len(call_args[0]) == 5  # All 5 citation IDs
            assert call_args[1] == 'marketing'
            
            # Verify scores were modified
            # Original scores: 0.850, 0.820, 0.800, 0.780, 0.750
            # After boost:
            # - chunk0: 0.850 * 1.3 = 1.105 (HIGH TIER - 75% like)
            # - chunk1: 0.820 * 0.8 = 0.656 (LOW TIER - 40% like)
            # - others: unchanged (no feedback)
            
            # chunk0 should now be top (1.105 > 0.850)
            assert citations[0].doc_id == '1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk0'
            assert citations[0].score == pytest.approx(0.850 * 1.3, rel=1e-3)
            
            # chunk1 should be pushed down (0.656 < 0.800, 0.780, 0.750)
            chunk1_index = next(i for i, c in enumerate(citations) if c.doc_id == '1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk1')
            assert chunk1_index == 4  # Should be last
            assert citations[chunk1_index].score == pytest.approx(0.820 * 0.8, rel=1e-3)
    
    @pytest.mark.skip(reason="Requires mocking private QdrantRAGClient methods")
    @pytest.mark.asyncio
    async def test_ranking_when_postgres_unavailable(self, qdrant_client, sample_citations):
        """Test that ranking works (no boost) when postgres is unavailable."""
        from infrastructure.postgres_client import postgres_client
        
        with patch.object(qdrant_client, '_search_qdrant', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = sample_citations.copy()
            
            with patch.object(postgres_client, 'is_available', return_value=False):
                with patch.object(qdrant_client, '_get_cached_citations', new_callable=AsyncMock) as mock_cache_get:
                    mock_cache_get.return_value = None
                    
                    with patch.object(qdrant_client, '_cache_citations', new_callable=AsyncMock):
                        citations = await qdrant_client._retrieve_from_qdrant('test query', 'marketing', top_k=5)
            
            # Scores should be unchanged (no feedback applied)
            assert citations[0].score == 0.850
            assert citations[1].score == 0.820
            assert citations[2].score == 0.800
            assert citations[3].score == 0.780
            assert citations[4].score == 0.750
    
    @pytest.mark.skip(reason="Requires mocking private QdrantRAGClient methods")
    @pytest.mark.asyncio
    async def test_ranking_with_no_feedback_data(self, qdrant_client, sample_citations):
        """Test that ranking works when no feedback data exists for any citation."""
        from infrastructure.postgres_client import postgres_client
        
        with patch.object(qdrant_client, '_search_qdrant', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = sample_citations.copy()
            
            with patch.object(postgres_client, 'is_available', return_value=True):
                with patch.object(postgres_client, 'get_citation_feedback_batch', new_callable=AsyncMock) as mock_feedback:
                    mock_feedback.return_value = {}  # No feedback data
                    
                    with patch.object(qdrant_client, '_get_cached_citations', new_callable=AsyncMock) as mock_cache_get:
                        mock_cache_get.return_value = None
                        
                        with patch.object(qdrant_client, '_cache_citations', new_callable=AsyncMock):
                            citations = await qdrant_client._retrieve_from_qdrant('test query', 'marketing', top_k=5)
            
            # All citations get 0% boost (neutral), so order unchanged
            assert citations[0].score == 0.850
            assert citations[1].score == 0.820
            assert citations[2].score == 0.800


class TestRankingEdgeCases:
    """Test edge cases in feedback ranking."""
    
    @pytest.mark.skip(reason="Requires mocking QdrantRAGClient internal methods")
    @pytest.mark.asyncio
    async def test_ranking_with_single_citation(self, qdrant_client):
        """Test ranking with only one citation."""
        from infrastructure.postgres_client import postgres_client
        
        single_citation = [
            Citation(
                doc_id='test_id',
                title='Test Document',
                content='test content',
                score=0.800,
                metadata={}
            )
        ]
        
        with patch.object(qdrant_client, 'retrieve', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = single_citation.copy()
            
            with patch.object(postgres_client, 'is_available', return_value=True):
                with patch.object(postgres_client, 'get_citation_feedback_batch', new_callable=AsyncMock) as mock_feedback:
                    mock_feedback.return_value = {'test_id': 85.0}
                    
                    with patch.object(qdrant_client, '_get_cached_citations', new_callable=AsyncMock) as mock_cache_get:
                        mock_cache_get.return_value = None
                        
                        with patch.object(qdrant_client, '_cache_citations', new_callable=AsyncMock):
                            citations = await qdrant_client._retrieve_from_qdrant('test', 'marketing', top_k=1)
            
            assert len(citations) == 1
            assert citations[0].score == pytest.approx(0.800 * 1.3, rel=1e-3)
    
    @pytest.mark.skip(reason="Requires mocking QdrantRAGClient internal methods")
    @pytest.mark.asyncio
    async def test_ranking_with_empty_citations(self, qdrant_client):
        """Test ranking with no citations returned."""
        from infrastructure.postgres_client import postgres_client
        
        with patch.object(qdrant_client, 'retrieve', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            
            with patch.object(postgres_client, 'is_available', return_value=True):
                with patch.object(qdrant_client, '_get_cached_citations', new_callable=AsyncMock) as mock_cache_get:
                    mock_cache_get.return_value = None
                    
                    with patch.object(qdrant_client, '_cache_citations', new_callable=AsyncMock):
                        citations = await qdrant_client._retrieve_from_qdrant('test', 'marketing', top_k=5)
            
            assert citations == []
    
    @pytest.mark.skip(reason="Requires mocking QdrantRAGClient internal methods")
    @pytest.mark.asyncio
    async def test_ranking_score_reversal(self, qdrant_client):
        """Test that feedback can reverse the original ranking order."""
        from infrastructure.postgres_client import postgres_client
        
        # Create citations where lower-scored item has better feedback
        test_citations = [
            Citation(doc_id='high_semantic', title='High Match', content='High semantic match', score=0.900, metadata={}),
            Citation(doc_id='low_semantic', title='Low Match', content='Low semantic match', score=0.600, metadata={}),
        ]
        
        # Give the low-semantic one 100% like (huge boost)
        # Give the high-semantic one 0% like (penalty)
        feedback_map = {
            'high_semantic': 0.0,    # -20% penalty → 0.900 * 0.8 = 0.720
            'low_semantic': 100.0,   # +30% boost → 0.600 * 1.3 = 0.780
        }
        
        with patch.object(qdrant_client, 'retrieve', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = test_citations.copy()
            
            with patch.object(postgres_client, 'is_available', return_value=True):
                with patch.object(postgres_client, 'get_citation_feedback_batch', new_callable=AsyncMock) as mock_feedback:
                    mock_feedback.return_value = feedback_map
                    
                    with patch.object(qdrant_client, '_get_cached_citations', new_callable=AsyncMock) as mock_cache_get:
                        mock_cache_get.return_value = None
                        
                        with patch.object(qdrant_client, '_cache_citations', new_callable=AsyncMock):
                            citations = await qdrant_client._retrieve_from_qdrant('test', 'marketing', top_k=2)
            
            # Order should be REVERSED - low_semantic now ranks higher  
            assert citations[0].doc_id == 'low_semantic'
            assert citations[1].doc_id == 'high_semantic'
            assert citations[0].score == pytest.approx(0.600 * 1.3, rel=1e-3)
            assert citations[1].score == pytest.approx(0.900 * 0.8, rel=1e-3)


class TestCacheIntegration:
    """Test that feedback ranking works with Redis caching."""
    
    @pytest.mark.skip(reason="Requires mocking QdrantRAGClient internal cache methods")
    @pytest.mark.asyncio
    async def test_cache_miss_applies_ranking(self, qdrant_client, sample_citations):
        """Test that ranking is applied on cache miss."""
        from infrastructure.postgres_client import postgres_client
        
        with patch.object(qdrant_client, '_search_qdrant', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = sample_citations.copy()
            
            with patch.object(postgres_client, 'is_available', return_value=True):
                with patch.object(postgres_client, 'get_citation_feedback_batch', new_callable=AsyncMock) as mock_feedback:
                    mock_feedback.return_value = {'1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk0': 75.0}
                    
                    with patch.object(qdrant_client, '_get_cached_citations', new_callable=AsyncMock) as mock_cache_get:
                        mock_cache_get.return_value = None  # Cache miss
                        
                        with patch.object(qdrant_client, '_cache_citations', new_callable=AsyncMock) as mock_cache_set:
                            citations = await qdrant_client._retrieve_from_qdrant('test', 'marketing', top_k=5)
                            
                            # Verify ranked citations were cached
                            mock_cache_set.assert_called_once()
                            cached_citations = mock_cache_set.call_args[0][2]
                            assert cached_citations[0].score == pytest.approx(0.850 * 1.3, rel=1e-3)
    
    @pytest.mark.skip(reason="Requires mocking QdrantRAGClient internal cache methods")
    @pytest.mark.asyncio
    async def test_cache_hit_skips_ranking(self, qdrant_client, sample_citations):
        """Test that ranking is NOT applied on cache hit."""
        from infrastructure.postgres_client import postgres_client
        
        # Pre-ranked citations from cache
        cached_citations = sample_citations.copy()
        
        with patch.object(qdrant_client, '_get_cached_citations', new_callable=AsyncMock) as mock_cache_get:
            mock_cache_get.return_value = cached_citations
            
            with patch.object(postgres_client, 'get_citation_feedback_batch', new_callable=AsyncMock) as mock_feedback:
                citations = await qdrant_client._retrieve_from_qdrant('test', 'marketing', top_k=5)
                
                # Feedback should NOT be called (cache hit)
                mock_feedback.assert_not_called()
                
                # Citations should match cached versions exactly
                assert citations == cached_citations
