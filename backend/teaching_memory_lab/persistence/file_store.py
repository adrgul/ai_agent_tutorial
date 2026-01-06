"""
File-based checkpoint store for teaching.

Stores checkpoints as JSON files organized by tenant/user/session.
Simple, transparent, easy to inspect - perfect for teaching.
"""
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .interfaces import ICheckpointStore


class FileCheckpointStore(ICheckpointStore):
    """
    File-based checkpoint persistence.
    
    Directory structure:
    data/teaching_checkpoints/{tenant_id}/{user_id}/{session_id}/{checkpoint_id}.json
    """
    
    def __init__(self, base_dir: str = "data/teaching_checkpoints"):
        """
        Args:
            base_dir: Base directory for checkpoint storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_checkpoint_path(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        checkpoint_id: str
    ) -> Path:
        """Build path to checkpoint file"""
        return self.base_dir / tenant_id / user_id / session_id / f"{checkpoint_id}.json"
    
    def _get_session_dir(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str
    ) -> Path:
        """Build path to session directory"""
        return self.base_dir / tenant_id / user_id / session_id
    
    async def save_checkpoint(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        checkpoint_id: str,
        state_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save checkpoint as JSON file"""
        path = self._get_checkpoint_path(tenant_id, user_id, session_id, checkpoint_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "session_id": session_id,
            "state": state_data,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        
        try:
            with open(path, 'w') as f:
                json.dump(checkpoint_data, f, indent=2, default=str)
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
        """Load checkpoint from file. If checkpoint_id is None, load latest."""
        session_dir = self._get_session_dir(tenant_id, user_id, session_id)
        
        if not session_dir.exists():
            return None
        
        if checkpoint_id:
            # Load specific checkpoint
            path = self._get_checkpoint_path(tenant_id, user_id, session_id, checkpoint_id)
            if not path.exists():
                return None
            
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading checkpoint: {e}")
                return None
        else:
            # Load latest checkpoint
            checkpoint_files = list(session_dir.glob("*.json"))
            if not checkpoint_files:
                return None
            
            # Sort by modification time, newest first
            latest_file = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
            
            try:
                with open(latest_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading latest checkpoint: {e}")
                return None
    
    async def list_checkpoints(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List checkpoints for session"""
        session_dir = self._get_session_dir(tenant_id, user_id, session_id)
        
        if not session_dir.exists():
            return []
        
        checkpoint_files = list(session_dir.glob("*.json"))
        
        # Sort by modification time, newest first
        checkpoint_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Limit results
        checkpoint_files = checkpoint_files[:limit]
        
        checkpoints = []
        for path in checkpoint_files:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    checkpoints.append({
                        "checkpoint_id": data.get("checkpoint_id"),
                        "created_at": data.get("created_at"),
                        "metadata": data.get("metadata", {})
                    })
            except Exception as e:
                print(f"Error reading checkpoint {path}: {e}")
                continue
        
        return checkpoints
    
    async def delete_checkpoint(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        checkpoint_id: str
    ) -> bool:
        """Delete specific checkpoint file"""
        path = self._get_checkpoint_path(tenant_id, user_id, session_id, checkpoint_id)
        
        if not path.exists():
            return False
        
        try:
            path.unlink()
            return True
        except Exception as e:
            print(f"Error deleting checkpoint: {e}")
            return False
