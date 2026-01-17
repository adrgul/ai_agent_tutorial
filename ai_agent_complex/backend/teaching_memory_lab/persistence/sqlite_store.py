"""
SQLite-based checkpoint store for teaching.

More scalable than file store, with indexes and efficient queries.
Good for demonstrating production-grade persistence patterns.
"""
import json
import sqlite3
import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .interfaces import ICheckpointStore


class SQLiteCheckpointStore(ICheckpointStore):
    """
    SQLite-based checkpoint persistence with indexes.
    
    Schema:
    - checkpoints table with composite key (tenant_id, user_id, session_id, checkpoint_id)
    - Indexes on (session_id, created_at) for fast listing
    """
    
    def __init__(self, db_path: str = "data/teaching_checkpoints.db"):
        """
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize schema synchronously
        self._init_schema()
    
    def _init_schema(self):
        """Create tables and indexes if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    tenant_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    state_data TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, user_id, session_id, checkpoint_id)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_created
                ON checkpoints(session_id, created_at DESC)
            """)
            
            conn.commit()
    
    async def save_checkpoint(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        checkpoint_id: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save checkpoint to SQLite"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO checkpoints
                    (tenant_id, user_id, session_id, checkpoint_id, state_data, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    tenant_id,
                    user_id,
                    session_id,
                    checkpoint_id,
                    json.dumps(state_data, default=str),
                    json.dumps(metadata or {}, default=str),
                    datetime.now().isoformat()
                ))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error saving checkpoint: {e}")
            return False
    
    async def load_checkpoint(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint from SQLite. If checkpoint_id is None, load latest."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if checkpoint_id:
                    # Load specific checkpoint
                    async with db.execute("""
                        SELECT checkpoint_id, state_data, metadata, created_at
                        FROM checkpoints
                        WHERE tenant_id = ? AND user_id = ? AND session_id = ? AND checkpoint_id = ?
                    """, (tenant_id, user_id, session_id, checkpoint_id)) as cursor:
                        row = await cursor.fetchone()
                else:
                    # Load latest checkpoint
                    async with db.execute("""
                        SELECT checkpoint_id, state_data, metadata, created_at
                        FROM checkpoints
                        WHERE tenant_id = ? AND user_id = ? AND session_id = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (tenant_id, user_id, session_id)) as cursor:
                        row = await cursor.fetchone()
                
                if not row:
                    return None
                
                return {
                    "checkpoint_id": row["checkpoint_id"],
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "session_id": session_id,
                    "state": json.loads(row["state_data"]),
                    "metadata": json.loads(row["metadata"]),
                    "created_at": row["created_at"]
                }
        except Exception as e:
            print(f"Error loading checkpoint: {e}")
            return None
    
    async def list_checkpoints(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List checkpoints for session"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                async with db.execute("""
                    SELECT checkpoint_id, metadata, created_at
                    FROM checkpoints
                    WHERE tenant_id = ? AND user_id = ? AND session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (tenant_id, user_id, session_id, limit)) as cursor:
                    rows = await cursor.fetchall()
                    
                    return [
                        {
                            "checkpoint_id": row["checkpoint_id"],
                            "created_at": row["created_at"],
                            "metadata": json.loads(row["metadata"])
                        }
                        for row in rows
                    ]
        except Exception as e:
            print(f"Error listing checkpoints: {e}")
            return []
    
    async def delete_checkpoint(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        checkpoint_id: str
    ) -> bool:
        """Delete specific checkpoint"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM checkpoints
                    WHERE tenant_id = ? AND user_id = ? AND session_id = ? AND checkpoint_id = ?
                """, (tenant_id, user_id, session_id, checkpoint_id))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error deleting checkpoint: {e}")
            return False
