"""
Sparse (lexical) index using SQLite FTS5 for BM25-like scoring.

This provides a lightweight, persistent sparse retrieval mechanism
without requiring external services.
"""

import sqlite3
from typing import List, Dict, Tuple
from pathlib import Path
import json

from rag.models import Chunk, RetrievalResult
from rag.config import StorageConfig


class SparseIndex:
    """
    Sparse text index using SQLite FTS5 (Full-Text Search).
    
    FTS5 provides BM25 ranking out of the box and persists to disk.
    Each tenant gets a separate database file for isolation.
    """
    
    def __init__(self, tenant_id: str, config: StorageConfig = None):
        """
        Initialize sparse index for a tenant.
        
        Args:
            tenant_id: Tenant ID for isolation.
            config: Storage configuration.
        """
        self.tenant_id = tenant_id
        self.config = config or StorageConfig()
        
        # Get tenant-specific database path
        db_dir = self.config.get_sparse_index_path(tenant_id)
        self.db_path = db_dir / "sparse_index.db"
        
        # Initialize database
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the SQLite FTS5 database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create FTS5 virtual table for full-text search
        # BM25 ranking is built into FTS5
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
            USING fts5(
                chunk_id UNINDEXED,
                doc_id UNINDEXED,
                chunk_text,
                metadata UNINDEXED,
                tokenize='porter unicode61'
            )
        """)
        
        # Create a regular table for metadata (for easier querying)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunk_metadata (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                chunk_index INTEGER,
                start_offset INTEGER,
                end_offset INTEGER,
                metadata_json TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_doc_id
            ON chunk_metadata(doc_id)
        """)
        
        conn.commit()
        conn.close()
    
    def add_chunk(self, chunk: Chunk) -> None:
        """
        Add a chunk to the sparse index.
        
        Args:
            chunk: Chunk object.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Add to FTS5 table
        cursor.execute("""
            INSERT INTO chunks_fts (chunk_id, doc_id, chunk_text, metadata)
            VALUES (?, ?, ?, ?)
        """, (
            chunk.chunk_id,
            chunk.doc_id,
            chunk.text,
            json.dumps(chunk.metadata)
        ))
        
        # Add to metadata table
        cursor.execute("""
            INSERT OR REPLACE INTO chunk_metadata
            (chunk_id, doc_id, tenant_id, chunk_index, start_offset, end_offset, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk.chunk_id,
            chunk.doc_id,
            chunk.tenant_id,
            chunk.chunk_index,
            chunk.start_offset,
            chunk.end_offset,
            json.dumps(chunk.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def add_chunks_batch(self, chunks: List[Chunk]) -> None:
        """
        Add multiple chunks in a batch.
        
        Args:
            chunks: List of chunks.
        """
        if not chunks:
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Prepare data for batch insert
        fts_data = [
            (chunk.chunk_id, chunk.doc_id, chunk.text, json.dumps(chunk.metadata))
            for chunk in chunks
        ]
        
        metadata_data = [
            (
                chunk.chunk_id,
                chunk.doc_id,
                chunk.tenant_id,
                chunk.chunk_index,
                chunk.start_offset,
                chunk.end_offset,
                json.dumps(chunk.metadata)
            )
            for chunk in chunks
        ]
        
        # Batch insert
        cursor.executemany("""
            INSERT INTO chunks_fts (chunk_id, doc_id, chunk_text, metadata)
            VALUES (?, ?, ?, ?)
        """, fts_data)
        
        cursor.executemany("""
            INSERT OR REPLACE INTO chunk_metadata
            (chunk_id, doc_id, tenant_id, chunk_index, start_offset, end_offset, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, metadata_data)
        
        conn.commit()
        conn.close()
    
    def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """
        Search using BM25 scoring.
        
        Args:
            query: Search query text.
            top_k: Number of results to return.
        
        Returns:
            List of RetrievalResult objects with sparse scores.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # FTS5 MATCH query with BM25 ranking
        # The rank column contains negative BM25 scores (lower is better)
        cursor.execute("""
            SELECT
                f.chunk_id,
                f.chunk_text,
                f.doc_id,
                -rank AS bm25_score,
                m.chunk_index,
                m.start_offset,
                m.end_offset,
                m.metadata_json
            FROM chunks_fts f
            JOIN chunk_metadata m ON f.chunk_id = m.chunk_id
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, top_k))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return []
        
        results = []
        
        # Normalize scores to 0-1 range
        scores = [row[3] for row in rows]
        max_score = max(scores) if scores else 1.0
        min_score = min(scores) if scores else 0.0
        score_range = max_score - min_score if max_score > min_score else 1.0
        
        for row in rows:
            chunk_id, text, doc_id, bm25_score, chunk_index, start_offset, end_offset, metadata_json = row
            
            # Normalize score to 0-1
            normalized_score = (bm25_score - min_score) / score_range if score_range > 0 else 1.0
            
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                tenant_id=self.tenant_id,
                text=text,
                start_offset=start_offset,
                end_offset=end_offset,
                chunk_index=chunk_index,
                metadata=metadata
            )
            
            results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=normalized_score,
                    sparse_score=normalized_score
                )
            )
        
        return results
    
    def delete_by_doc_id(self, doc_id: str) -> None:
        """
        Delete all chunks for a document.
        
        Args:
            doc_id: Document ID.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Get chunk IDs for this document
        cursor.execute("""
            SELECT chunk_id FROM chunk_metadata WHERE doc_id = ?
        """, (doc_id,))
        
        chunk_ids = [row[0] for row in cursor.fetchall()]
        
        if chunk_ids:
            # Delete from FTS5 table
            placeholders = ",".join(["?"] * len(chunk_ids))
            cursor.execute(f"""
                DELETE FROM chunks_fts WHERE chunk_id IN ({placeholders})
            """, chunk_ids)
            
            # Delete from metadata table
            cursor.execute("""
                DELETE FROM chunk_metadata WHERE doc_id = ?
            """, (doc_id,))
        
        conn.commit()
        conn.close()
    
    def count(self) -> int:
        """
        Get total number of chunks.
        
        Returns:
            Number of chunks.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chunk_metadata")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_chunk_by_id(self, chunk_id: str) -> Chunk:
        """
        Get a chunk by ID.
        
        Args:
            chunk_id: Chunk ID.
        
        Returns:
            Chunk object or None.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                f.chunk_text,
                m.doc_id,
                m.chunk_index,
                m.start_offset,
                m.end_offset,
                m.metadata_json
            FROM chunks_fts f
            JOIN chunk_metadata m ON f.chunk_id = m.chunk_id
            WHERE f.chunk_id = ?
        """, (chunk_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        text, doc_id, chunk_index, start_offset, end_offset, metadata_json = row
        metadata = json.loads(metadata_json) if metadata_json else {}
        
        return Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            tenant_id=self.tenant_id,
            text=text,
            start_offset=start_offset,
            end_offset=end_offset,
            chunk_index=chunk_index,
            metadata=metadata
        )
