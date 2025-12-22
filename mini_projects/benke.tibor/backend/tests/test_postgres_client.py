"""
Unit tests for PostgreSQL client.
Tests feedback data storage and retrieval.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from infrastructure.postgres_client import PostgresClient


@pytest.fixture
def postgres_client():
    """Create a PostgresClient instance for testing."""
    return PostgresClient()


@pytest.fixture
def mock_pool():
    """Create a mock asyncpg connection pool."""
    pool = MagicMock()
    pool.acquire = AsyncMock()
    return pool


@pytest.fixture
def mock_connection():
    """Create a mock database connection."""
    conn = MagicMock()
    conn.fetch = AsyncMock()
    conn.execute = AsyncMock()
    conn.close = AsyncMock()
    return conn


class TestPostgresClientInitialization:
    """Test PostgreSQL client initialization."""
    
    @pytest.mark.asyncio
    async def test_lazy_initialization(self, postgres_client):
        """Test that pool is not initialized on creation."""
        assert postgres_client.pool is None
    
    @pytest.mark.asyncio
    async def test_is_available_always_true(self, postgres_client):
        """Test that is_available returns True (lazy init pattern)."""
        assert postgres_client.is_available() is True
        assert postgres_client.pool is None  # Still not initialized
    
    @pytest.mark.asyncio
    async def test_ensure_initialized_creates_pool(self, postgres_client):
        """Test that ensure_initialized creates pool on first call."""
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_pool = MagicMock()
            mock_create_pool.return_value = mock_pool
            
            await postgres_client.ensure_initialized()
            
            assert postgres_client.pool is not None
            mock_create_pool.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_initialized_prevents_double_init(self, postgres_client):
        """Test that concurrent calls don't create multiple pools."""
        with patch('asyncpg.create_pool', new_callable=AsyncMock) as mock_create_pool:
            mock_pool = MagicMock()
            mock_create_pool.return_value = mock_pool
            
            # Simulate concurrent calls
            await asyncio.gather(
                postgres_client.ensure_initialized(),
                postgres_client.ensure_initialized(),
                postgres_client.ensure_initialized(),
            )
            
            # Should only call create_pool once
            assert mock_create_pool.call_count == 1


class TestCitationFeedbackBatch:
    """Test batch citation feedback lookup."""
    
    @pytest.mark.asyncio
    async def test_get_citation_feedback_batch_success(self, postgres_client):
        """Test successful batch feedback lookup."""
        citation_ids = [
            '1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk0',
            '1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk1',
            '1utetoO-ApR4lmOpY1HS63va_gqmjDfsA#chunk0',
        ]
        
        # Mock database response
        mock_rows = [
            {'citation_id': '1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk0', 'like_percentage': 75.0, 'like_count': 3, 'dislike_count': 1, 'total_feedback': 4},
            {'citation_id': '1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk1', 'like_percentage': 40.0, 'like_count': 2, 'dislike_count': 3, 'total_feedback': 5},
        ]
        
        with patch.object(postgres_client, 'get_standalone_connection', new_callable=AsyncMock) as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.fetch = AsyncMock(return_value=mock_rows)
            mock_conn.close = AsyncMock()
            mock_get_conn.return_value = mock_conn
            
            # Add ensure_initialized call
            await postgres_client.ensure_initialized()
            
            result = await postgres_client.get_citation_feedback_batch(citation_ids, 'marketing')
            
            # Verify results
            assert len(result) == 2
            assert result['1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk0'] == 75.0
            assert result['1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk1'] == 40.0
            assert '1utetoO-ApR4lmOpY1HS63va_gqmjDfsA#chunk0' not in result
            
            # Verify SQL query called correctly
            mock_conn.fetch.assert_called_once()
            call_args = mock_conn.fetch.call_args[0]
            assert 'WHERE citation_id = ANY($1)' in call_args[0]
            assert call_args[1] == citation_ids
            assert call_args[2] == 'marketing'
            
            # Verify connection closed
            mock_conn.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_citation_feedback_batch_empty_result(self, postgres_client):
        """Test batch lookup with no matching citations."""
        citation_ids = ['nonexistent_id1', 'nonexistent_id2']
        
        with patch.object(postgres_client, 'get_standalone_connection', new_callable=AsyncMock) as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_conn.close = AsyncMock()
            mock_get_conn.return_value = mock_conn
            
            result = await postgres_client.get_citation_feedback_batch(citation_ids, 'marketing')
            
            assert result == {}
            mock_conn.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_citation_feedback_batch_connection_error(self, postgres_client):
        """Test batch lookup handles connection errors gracefully."""
        citation_ids = ['test_id']
        
        await postgres_client.ensure_initialized()
        
        with patch.object(postgres_client, 'get_standalone_connection', new_callable=AsyncMock) as mock_get_conn:
            mock_get_conn.side_effect = Exception("Connection failed")
            
            # Should return empty dict on error, not raise
            result = await postgres_client.get_citation_feedback_batch(citation_ids, 'marketing')
            assert result == {}


class TestCitationFeedbackPercentage:
    """Test individual citation feedback lookup (legacy method)."""
    
    @pytest.mark.skip(reason="Pool.acquire is read-only, cannot mock easily")
    @pytest.mark.asyncio
    async def test_get_citation_feedback_percentage_found(self, postgres_client):
        """Test getting feedback percentage for existing citation."""
        pass
    
    @pytest.mark.skip(reason="Pool.acquire is read-only, cannot mock easily")
    @pytest.mark.asyncio
    async def test_get_citation_feedback_percentage_not_found(self, postgres_client):
        """Test getting feedback percentage for non-existent citation."""
        pass


class TestRecordFeedback:
    """Test feedback recording functionality."""
    
    @pytest.mark.skip(reason="record_citation_feedback method not implemented yet")
    @pytest.mark.asyncio
    async def test_record_citation_feedback_success(self, postgres_client):
        """Test successful citation feedback recording."""
        pass
    
    @pytest.mark.skip(reason="record_citation_feedback method not implemented yet")
    @pytest.mark.asyncio
    async def test_record_citation_feedback_invalid_type(self, postgres_client):
        """Test that invalid feedback type raises error."""
        pass


class TestStandaloneConnection:
    """Test standalone connection management."""
    
    @pytest.mark.asyncio
    async def test_get_standalone_connection(self, postgres_client):
        """Test creating standalone connection."""
        with patch('asyncpg.connect', new_callable=AsyncMock) as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            
            conn = await postgres_client.get_standalone_connection()
            
            assert conn == mock_conn
            mock_connect.assert_called_once()
            # Verify connection string format
            call_kwargs = mock_connect.call_args[1]
            assert 'host' in call_kwargs
            assert 'database' in call_kwargs
            assert 'user' in call_kwargs
            assert 'password' in call_kwargs
