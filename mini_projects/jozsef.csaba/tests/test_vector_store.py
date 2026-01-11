"""Tests for FAISS vector store."""

import numpy as np
import pytest
import tempfile
import shutil

from app.models.schemas import KBChunk
from app.utils.vector_store import FAISSVectorStore


class TestFAISSVectorStore:
    """Tests for FAISS vector store."""

    @pytest.fixture
    def temp_index_path(self):
        """Create temporary directory for index."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_chunks(self):
        """Provide sample KB chunks."""
        return [
            KBChunk(
                chunk_id="c-1",
                doc_id="KB-1",
                title="Article 1",
                content="This is about billing issues",
                chunk_index=0,
                url="https://kb.example.com/1",
                category="Billing",
            ),
            KBChunk(
                chunk_id="c-2",
                doc_id="KB-2",
                title="Article 2",
                content="This is about technical problems",
                chunk_index=0,
                url="https://kb.example.com/2",
                category="Technical",
            ),
        ]

    def test_initialization(self, temp_index_path):
        """Test vector store initialization."""
        store = FAISSVectorStore(
            embedding_dimension=1536,
            index_path=temp_index_path,
        )

        assert store.embedding_dimension == 1536
        assert store.num_documents == 0

    def test_add_documents(self, temp_index_path, sample_chunks):
        """Test adding documents to vector store."""
        store = FAISSVectorStore(
            embedding_dimension=128,  # Smaller for testing
            index_path=temp_index_path,
        )

        # Create random embeddings for testing
        embeddings = np.random.rand(len(sample_chunks), 128)

        store.add_documents(sample_chunks, embeddings)

        assert store.num_documents == len(sample_chunks)

    def test_search(self, temp_index_path, sample_chunks):
        """Test document search."""
        store = FAISSVectorStore(
            embedding_dimension=128,
            index_path=temp_index_path,
        )

        # Add documents
        embeddings = np.random.rand(len(sample_chunks), 128)
        store.add_documents(sample_chunks, embeddings)

        # Search with query
        query_embedding = np.random.rand(128)
        results = store.search(query_embedding, top_k=2)

        assert len(results) == 2
        assert all(hasattr(r, "doc_id") for r in results)
        assert all(hasattr(r, "score") for r in results)

    def test_save_and_load(self, temp_index_path, sample_chunks):
        """Test saving and loading index."""
        # Create and populate store
        store1 = FAISSVectorStore(
            embedding_dimension=128,
            index_path=temp_index_path,
        )

        embeddings = np.random.rand(len(sample_chunks), 128)
        store1.add_documents(sample_chunks, embeddings)
        store1.save_index()

        # Load in new store
        store2 = FAISSVectorStore(
            embedding_dimension=128,
            index_path=temp_index_path,
        )

        assert store2.num_documents == len(sample_chunks)
        assert len(store2.chunks) == len(sample_chunks)

    def test_empty_search(self, temp_index_path):
        """Test search on empty index."""
        store = FAISSVectorStore(
            embedding_dimension=128,
            index_path=temp_index_path,
        )

        query_embedding = np.random.rand(128)
        results = store.search(query_embedding, top_k=5)

        assert len(results) == 0

    def test_dimension_mismatch(self, temp_index_path, sample_chunks):
        """Test dimension mismatch error."""
        store = FAISSVectorStore(
            embedding_dimension=128,
            index_path=temp_index_path,
        )

        # Wrong dimension embeddings
        embeddings = np.random.rand(len(sample_chunks), 64)

        with pytest.raises(ValueError, match="dimension"):
            store.add_documents(sample_chunks, embeddings)

    def test_clear(self, temp_index_path, sample_chunks):
        """Test clearing the index."""
        store = FAISSVectorStore(
            embedding_dimension=128,
            index_path=temp_index_path,
        )

        # Add documents
        embeddings = np.random.rand(len(sample_chunks), 128)
        store.add_documents(sample_chunks, embeddings)

        assert store.num_documents == len(sample_chunks)

        # Clear
        store.clear()

        assert store.num_documents == 0
        assert len(store.chunks) == 0
