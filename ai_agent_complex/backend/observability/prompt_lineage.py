"""
Prompt lineage tracking for deep observability.

Tracks prompt versions/hashes per LLM invocation and associates each with:
- request_id
- agent_execution_id
- model_name
- timestamp

This enables tracking of prompt evolution and debugging of LLM behavior.
"""
import hashlib
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json

from langchain_core.messages import BaseMessage
from observability.correlation import get_request_id

logger = logging.getLogger(__name__)


@dataclass
class PromptLineage:
    """
    Prompt lineage record for tracking LLM invocations.
    
    Attributes:
        prompt_hash: SHA256 hash of the full prompt text
        request_id: Unique request identifier
        agent_execution_id: Unique agent execution identifier
        model_name: LLM model used
        timestamp: ISO timestamp of invocation
        prompt_version: Optional semantic version of prompt template
        message_count: Number of messages in the prompt
        total_chars: Total character count
    """
    prompt_hash: str
    request_id: str
    agent_execution_id: str
    model_name: str
    timestamp: str
    prompt_version: Optional[str] = None
    message_count: int = 0
    total_chars: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class PromptLineageTracker:
    """
    Tracks prompt lineage across LLM invocations.
    
    Stores prompt hashes and metadata in memory (can be extended to persist to disk/DB).
    """
    
    def __init__(self):
        """Initialize the tracker with empty lineage storage."""
        self._lineage_records: List[PromptLineage] = []
    
    def track_prompt(
        self,
        messages: List[BaseMessage],
        model_name: str,
        agent_execution_id: str,
        prompt_version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PromptLineage:
        """
        Track a prompt invocation.
        
        Args:
            messages: List of LangChain messages
            model_name: Model name (e.g., "gpt-4o-mini")
            agent_execution_id: Unique agent execution ID
            prompt_version: Optional semantic version
            metadata: Additional metadata to store
        
        Returns:
            PromptLineage record
        """
        # Compute prompt hash
        prompt_text = self._messages_to_text(messages)
        prompt_hash = self._hash_prompt(prompt_text)
        
        # Create lineage record
        lineage = PromptLineage(
            prompt_hash=prompt_hash,
            request_id=get_request_id(),
            agent_execution_id=agent_execution_id,
            model_name=model_name,
            timestamp=datetime.utcnow().isoformat(),
            prompt_version=prompt_version,
            message_count=len(messages),
            total_chars=len(prompt_text),
            metadata=metadata or {}
        )
        
        # Store record
        self._lineage_records.append(lineage)
        
        # Log (without full prompt content - as per spec)
        logger.info(
            f"Prompt lineage tracked: hash={prompt_hash[:16]}... "
            f"model={model_name} exec_id={agent_execution_id} "
            f"messages={len(messages)}"
        )
        
        return lineage
    
    def _messages_to_text(self, messages: List[BaseMessage]) -> str:
        """Convert messages to canonical text representation for hashing."""
        parts = []
        for msg in messages:
            role = msg.type or "unknown"
            content = msg.content or ""
            parts.append(f"{role}: {content}")
        return "\n".join(parts)
    
    def _hash_prompt(self, prompt_text: str) -> str:
        """
        Compute SHA256 hash of prompt text.
        
        Args:
            prompt_text: Full prompt text
        
        Returns:
            Hex digest of SHA256 hash
        """
        return hashlib.sha256(prompt_text.encode('utf-8')).hexdigest()
    
    def get_lineage_by_hash(self, prompt_hash: str) -> List[PromptLineage]:
        """
        Retrieve all lineage records for a given prompt hash.
        
        Args:
            prompt_hash: Prompt hash to search for
        
        Returns:
            List of matching PromptLineage records
        """
        return [rec for rec in self._lineage_records if rec.prompt_hash == prompt_hash]
    
    def get_lineage_by_execution(self, agent_execution_id: str) -> List[PromptLineage]:
        """
        Retrieve all lineage records for a given agent execution.
        
        Args:
            agent_execution_id: Agent execution ID
        
        Returns:
            List of PromptLineage records for this execution
        """
        return [
            rec for rec in self._lineage_records 
            if rec.agent_execution_id == agent_execution_id
        ]
    
    def get_recent_lineage(self, limit: int = 100) -> List[PromptLineage]:
        """
        Get the most recent lineage records.
        
        Args:
            limit: Maximum number of records to return
        
        Returns:
            List of recent PromptLineage records
        """
        return self._lineage_records[-limit:]
    
    def clear(self):
        """Clear all lineage records (useful for testing)."""
        self._lineage_records.clear()
        logger.info("Prompt lineage records cleared")


# Global singleton tracker
_global_tracker = PromptLineageTracker()


def get_prompt_tracker() -> PromptLineageTracker:
    """Get the global prompt lineage tracker."""
    return _global_tracker
