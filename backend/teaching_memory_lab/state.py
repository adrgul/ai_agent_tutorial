"""
AppState definition with explicit channels for teaching memory management.

Channels separate concerns and make state management predictable:
- messages: conversation history (can be trimmed)
- summary: persistent summary of conversation (versioned)
- facts: structured facts extracted from conversation
- profile: stable user attributes (loaded/saved separately)
- trace: metadata about tools, costs, latency
- retrieved_context: RAG recall snippets for current turn only
"""
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Single message in conversation"""
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    message_id: Optional[str] = None  # For deduplication
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Fact(BaseModel):
    """Structured fact extracted from conversation"""
    key: str  # e.g., "preferred_language"
    value: Any  # e.g., "hu"
    confidence: float = 1.0  # 0.0 to 1.0
    source: str = "user"  # user|assistant|inferred
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        # For deterministic comparison
        frozen = False


class Summary(BaseModel):
    """Versioned summary of conversation"""
    text: str
    version: int = 1
    token_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class UserProfile(BaseModel):
    """Stable user attributes - loaded/saved separately from state"""
    user_id: str
    tenant_id: str = "demo"
    language: str = "en"
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class TraceEntry(BaseModel):
    """Single trace entry for observability"""
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str  # e.g., "tool_call", "summary_update", "rag_recall"
    details: Dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = 0
    latency_ms: float = 0.0


class RetrievedContext(BaseModel):
    """RAG recall snippets for current turn"""
    source: str  # document name or ID
    content: str
    score: float  # similarity score
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AppState(BaseModel):
    """
    Teaching-focused state with explicit channels.
    
    Why channels? They decouple state updates - each channel has its own
    reducer, preventing conflicts and making state management predictable.
    """
    # Core conversation channel
    messages: List[Message] = Field(default_factory=list)
    
    # Summary channel - versioned, replaced not appended
    summary: Optional[Summary] = None
    
    # Facts channel - merged by key, last-write-wins with timestamp
    facts: Dict[str, Fact] = Field(default_factory=dict)
    
    # Profile channel - stable attributes, loaded separately
    profile: Optional[UserProfile] = None
    
    # Trace channel - append-only with size limit
    trace: List[TraceEntry] = Field(default_factory=list)
    
    # Retrieved context channel - ephemeral, cleared each turn
    retrieved_context: List[RetrievedContext] = Field(default_factory=list)
    
    # Metadata
    session_id: str
    tenant_id: str = "demo"
    user_id: str
    memory_mode: Literal["rolling", "summary", "facts", "hybrid"] = "rolling"
    
    class Config:
        arbitrary_types_allowed = True


class MemorySnapshot(BaseModel):
    """
    Memory snapshot for debugging and teaching - shows what's in memory
    after a turn, helping students understand different memory strategies.
    
    PARALLEL EXECUTION INFO:
    - parallel_nodes_executed: Which nodes ran concurrently
    - reducers_applied: Which reducers merged their outputs
    """
    mode: str
    messages_kept_count: int
    message_tokens_estimate: int
    
    # Summary mode
    summary_version: Optional[int] = None
    summary_length: Optional[int] = None
    
    # Facts mode
    facts_count: int = 0
    sample_facts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Hybrid/RAG mode
    rag_recall_used: bool = False
    retrieved_context_count: int = 0
    
    # Trace
    checkpoint_id: Optional[str] = None
    trace_entries: int = 0
    total_tokens_estimate: int = 0
    total_latency_ms: float = 0.0
    
    # PARALLEL EXECUTION INFO (for teaching)
    parallel_nodes_executed: List[str] = Field(default_factory=list)
    reducers_applied: List[str] = Field(default_factory=list)
