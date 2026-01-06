"""
Checkpoint persistence interfaces for teaching.

Demonstrates abstraction of state persistence - students can see how
different backends (file vs SQL) implement the same interface.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class ICheckpointStore(ABC):
    """
    Abstract interface for checkpoint persistence.
    
    Why abstract? Allows swapping storage backends without changing
    graph code. Teaching principle: depend on abstractions, not concrete classes.
    """
    
    @abstractmethod
    async def save_checkpoint(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        checkpoint_id: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save checkpoint with composite key.
        
        Args:
            tenant_id: Tenant identifier for multi-tenancy
            user_id: User identifier
            session_id: Session identifier
            checkpoint_id: Unique checkpoint ID (e.g., turn number or UUID)
            state_data: Serialized state (JSON-compatible dict)
            metadata: Optional metadata (e.g., model version, timestamp)
        
        Returns:
            True if saved successfully
        """
        pass
    
    @abstractmethod
    async def load_checkpoint(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint. If checkpoint_id is None, loads latest.
        
        Returns:
            State data dict or None if not found
        """
        pass
    
    @abstractmethod
    async def list_checkpoints(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List checkpoints for a session.
        
        Returns:
            List of checkpoint metadata dicts with:
            - checkpoint_id
            - created_at
            - metadata
        """
        pass
    
    @abstractmethod
    async def delete_checkpoint(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        checkpoint_id: str
    ) -> bool:
        """
        Delete specific checkpoint.
        
        Returns:
            True if deleted, False if not found
        """
        pass
