"""
LangGraph state snapshot tracking for agent decision tracing.

Captures LangGraph state at critical points:
- Before execution
- After each node
- After completion

Stores snapshots in memory or structured logs (NO full prompt content).
"""
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import copy

from observability.correlation import get_request_id

logger = logging.getLogger(__name__)


@dataclass
class StateSnapshot:
    """
    Snapshot of LangGraph state at a specific point in execution.
    
    Attributes:
        snapshot_id: Unique snapshot identifier
        agent_execution_id: Agent execution identifier
        request_id: Request identifier
        timestamp: ISO timestamp
        snapshot_type: Type of snapshot (before_execution, after_node, after_completion)
        node_name: Name of node (if applicable)
        state_summary: Summarized state (no full prompts)
        metadata: Additional metadata
    """
    snapshot_id: str
    agent_execution_id: str
    request_id: str
    timestamp: str
    snapshot_type: str  # before_execution, after_node, after_completion
    node_name: Optional[str] = None
    state_summary: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class StateTracker:
    """
    Tracks LangGraph state snapshots for agent decision tracing.
    
    Stores snapshots in memory. For production, consider persisting to disk or DB.
    """
    
    def __init__(self):
        """Initialize the tracker."""
        self._snapshots: List[StateSnapshot] = []
        self._snapshot_counter = 0
    
    def snapshot_before_execution(
        self,
        agent_execution_id: str,
        initial_state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> StateSnapshot:
        """
        Capture state snapshot before agent execution begins.
        
        Args:
            agent_execution_id: Unique execution identifier
            initial_state: Initial state dictionary
            metadata: Additional metadata
        
        Returns:
            StateSnapshot record
        """
        snapshot = self._create_snapshot(
            agent_execution_id=agent_execution_id,
            snapshot_type="before_execution",
            node_name=None,
            state=initial_state,
            metadata=metadata
        )
        
        logger.info(
            f"State snapshot (before_execution): "
            f"exec_id={agent_execution_id} snapshot_id={snapshot.snapshot_id}"
        )
        
        return snapshot
    
    def snapshot_after_node(
        self,
        agent_execution_id: str,
        node_name: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> StateSnapshot:
        """
        Capture state snapshot after a node executes.
        
        Args:
            agent_execution_id: Unique execution identifier
            node_name: Name of the node that just executed
            state: Current state dictionary
            metadata: Additional metadata
        
        Returns:
            StateSnapshot record
        """
        snapshot = self._create_snapshot(
            agent_execution_id=agent_execution_id,
            snapshot_type="after_node",
            node_name=node_name,
            state=state,
            metadata=metadata
        )
        
        logger.info(
            f"State snapshot (after_node): "
            f"exec_id={agent_execution_id} node={node_name} "
            f"snapshot_id={snapshot.snapshot_id}"
        )
        
        return snapshot
    
    def snapshot_after_completion(
        self,
        agent_execution_id: str,
        final_state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> StateSnapshot:
        """
        Capture state snapshot after agent execution completes.
        
        Args:
            agent_execution_id: Unique execution identifier
            final_state: Final state dictionary
            metadata: Additional metadata
        
        Returns:
            StateSnapshot record
        """
        snapshot = self._create_snapshot(
            agent_execution_id=agent_execution_id,
            snapshot_type="after_completion",
            node_name=None,
            state=final_state,
            metadata=metadata
        )
        
        logger.info(
            f"State snapshot (after_completion): "
            f"exec_id={agent_execution_id} snapshot_id={snapshot.snapshot_id}"
        )
        
        return snapshot
    
    def _create_snapshot(
        self,
        agent_execution_id: str,
        snapshot_type: str,
        state: Dict[str, Any],
        node_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StateSnapshot:
        """
        Create a state snapshot.
        
        Args:
            agent_execution_id: Execution identifier
            snapshot_type: Type of snapshot
            state: State dictionary
            node_name: Optional node name
            metadata: Optional metadata
        
        Returns:
            StateSnapshot record
        """
        self._snapshot_counter += 1
        snapshot_id = f"{agent_execution_id}_{self._snapshot_counter}"
        
        # Summarize state (avoid storing full prompts/messages)
        state_summary = self._summarize_state(state)
        
        snapshot = StateSnapshot(
            snapshot_id=snapshot_id,
            agent_execution_id=agent_execution_id,
            request_id=get_request_id(),
            timestamp=datetime.utcnow().isoformat(),
            snapshot_type=snapshot_type,
            node_name=node_name,
            state_summary=state_summary,
            metadata=metadata or {}
        )
        
        self._snapshots.append(snapshot)
        return snapshot
    
    def _summarize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of the state without full prompt content.
        
        As per spec: NO full prompt content in logs.
        
        Args:
            state: Full state dictionary
        
        Returns:
            Summarized state
        """
        summary = {}
        
        for key, value in state.items():
            if key in ("messages", "chat_history", "conversation"):
                # For message lists, just count them
                if isinstance(value, list):
                    summary[key] = {
                        "count": len(value),
                        "types": [msg.type if hasattr(msg, 'type') else type(msg).__name__ for msg in value[:5]]
                    }
                else:
                    summary[key] = {"type": type(value).__name__}
            elif key in ("tools_called", "debug_logs"):
                # Include these as-is (they're metadata, not prompts)
                summary[key] = copy.deepcopy(value)
            elif isinstance(value, (str, int, float, bool, type(None))):
                # Include primitive values
                if isinstance(value, str) and len(value) > 200:
                    summary[key] = value[:200] + "..."
                else:
                    summary[key] = value
            elif isinstance(value, dict):
                # Recursively summarize nested dicts
                summary[key] = self._summarize_state(value)
            elif isinstance(value, list):
                # Summarize lists
                summary[key] = {"count": len(value), "type": "list"}
            else:
                # For other types, just record the type
                summary[key] = {"type": type(value).__name__}
        
        return summary
    
    def get_snapshots_by_execution(self, agent_execution_id: str) -> List[StateSnapshot]:
        """
        Retrieve all snapshots for a given execution.
        
        Args:
            agent_execution_id: Execution identifier
        
        Returns:
            List of StateSnapshot records
        """
        return [
            snap for snap in self._snapshots 
            if snap.agent_execution_id == agent_execution_id
        ]
    
    def get_recent_snapshots(self, limit: int = 100) -> List[StateSnapshot]:
        """
        Get the most recent snapshots.
        
        Args:
            limit: Maximum number of snapshots to return
        
        Returns:
            List of recent snapshots
        """
        return self._snapshots[-limit:]
    
    def clear(self):
        """Clear all snapshots (useful for testing)."""
        self._snapshots.clear()
        self._snapshot_counter = 0
        logger.info("State snapshots cleared")


# Global singleton tracker
_global_state_tracker = StateTracker()


def get_state_tracker() -> StateTracker:
    """Get the global state tracker."""
    return _global_state_tracker
