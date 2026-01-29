"""Trace events for tracking graph execution."""
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel
from datetime import datetime


EventType = Literal[
    "node_start",
    "node_end",
    "tool_call",
    "tool_result",
    "send_fanout",
    "handoff",
    "cache_hit",
    "cache_miss",
]


class TraceEvent(BaseModel):
    """Represents a single trace event during graph execution."""
    
    type: EventType
    timestamp: str
    node_name: Optional[str] = None
    tool_name: Optional[str] = None
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    reason: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def node_start(cls, node_name: str, data: Optional[Dict[str, Any]] = None) -> "TraceEvent":
        """Create a node start event."""
        return cls(
            type="node_start",
            timestamp=datetime.now().isoformat(),
            node_name=node_name,
            data=data or {},
        )
    
    @classmethod
    def node_end(cls, node_name: str, data: Optional[Dict[str, Any]] = None) -> "TraceEvent":
        """Create a node end event."""
        return cls(
            type="node_end",
            timestamp=datetime.now().isoformat(),
            node_name=node_name,
            data=data or {},
        )
    
    @classmethod
    def tool_call(cls, tool_name: str, data: Optional[Dict[str, Any]] = None) -> "TraceEvent":
        """Create a tool call event."""
        return cls(
            type="tool_call",
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            data=data or {},
        )
    
    @classmethod
    def tool_result(cls, tool_name: str, data: Optional[Dict[str, Any]] = None) -> "TraceEvent":
        """Create a tool result event."""
        return cls(
            type="tool_result",
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            data=data or {},
        )
    
    @classmethod
    def send_fanout(cls, data: Optional[Dict[str, Any]] = None) -> "TraceEvent":
        """Create a send fanout event."""
        return cls(
            type="send_fanout",
            timestamp=datetime.now().isoformat(),
            data=data or {},
        )
    
    @classmethod
    def handoff(cls, from_agent: str, to_agent: str, reason: str) -> "TraceEvent":
        """Create a handoff event."""
        return cls(
            type="handoff",
            timestamp=datetime.now().isoformat(),
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason,
        )
    
    @classmethod
    def cache_hit(cls, data: Optional[Dict[str, Any]] = None) -> "TraceEvent":
        """Create a cache hit event."""
        return cls(
            type="cache_hit",
            timestamp=datetime.now().isoformat(),
            data=data or {},
        )
    
    @classmethod
    def cache_miss(cls, data: Optional[Dict[str, Any]] = None) -> "TraceEvent":
        """Create a cache miss event."""
        return cls(
            type="cache_miss",
            timestamp=datetime.now().isoformat(),
            data=data or {},
        )
