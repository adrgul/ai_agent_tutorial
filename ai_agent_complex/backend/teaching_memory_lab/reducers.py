"""
Deterministic reducers for channel merges.

Reducers ensure that when multiple branches of a graph merge, the state
combination is predictable and doesn't depend on execution order.

Key principles:
1. Determinism: same inputs always produce same output
2. Idempotency: applying same update multiple times is safe
3. Conflict resolution: clear rules (timestamp + tie-breaker)
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

from .state import Message, Fact, TraceEntry, Summary, RetrievedContext


def messages_reducer(existing: List[Message], new: List[Message]) -> List[Message]:
    """
    Append new messages, deduplicate by message_id if present.
    
    Why: Prevents duplicate messages when parallel branches merge.
    Always preserves order by timestamp.
    """
    # Create lookup for existing messages
    seen_ids = {msg.message_id for msg in existing if msg.message_id}
    
    result = list(existing)
    for msg in new:
        # Skip if we've seen this message_id
        if msg.message_id and msg.message_id in seen_ids:
            continue
        result.append(msg)
        if msg.message_id:
            seen_ids.add(msg.message_id)
    
    # Sort by timestamp for determinism
    result.sort(key=lambda m: m.timestamp)
    return result


def facts_reducer(existing: Dict[str, Fact], new: Dict[str, Fact]) -> Dict[str, Fact]:
    """
    Merge facts by key with last-write-wins using timestamp.
    
    Why: Facts represent stable information. We want the most recent
    value, but need deterministic tie-breaking if timestamps match.
    """
    result = dict(existing)
    
    for key, new_fact in new.items():
        if key not in result:
            # New fact, just add it
            result[key] = new_fact
        else:
            existing_fact = result[key]
            # Compare timestamps
            if new_fact.updated_at > existing_fact.updated_at:
                result[key] = new_fact
            elif new_fact.updated_at == existing_fact.updated_at:
                # Tie-breaker: lexicographic comparison of source
                # This ensures determinism even with same timestamp
                if new_fact.source >= existing_fact.source:
                    result[key] = new_fact
    
    return result


def trace_reducer(existing: List[TraceEntry], new: List[TraceEntry], max_size: int = 100) -> List[TraceEntry]:
    """
    Append trace entries, keep only last max_size entries.
    
    Why: Trace grows unbounded otherwise. We keep recent entries
    for debugging but trim old ones to prevent memory bloat.
    """
    result = existing + new
    result.sort(key=lambda t: t.timestamp)
    
    # Keep only last max_size entries
    if len(result) > max_size:
        result = result[-max_size:]
    
    return result


def summary_reducer(existing: Optional[Summary], new: Optional[Summary]) -> Optional[Summary]:
    """
    Replace summary with new one (versioned).
    
    Why: Summary is a full replacement, not an append. We keep version
    to track updates and can compare versions if needed.
    """
    if new is None:
        return existing
    return new


def retrieved_context_reducer(existing: List[RetrievedContext], new: List[RetrievedContext]) -> List[RetrievedContext]:
    """
    Replace retrieved context (ephemeral per turn).
    
    Why: Retrieved context is only relevant for current turn,
    so we replace rather than accumulate.
    """
    # For teaching: just replace
    return new


def trim_messages_by_budget(messages: List[Message], budget_tokens: int, keep_system: bool = True) -> List[Message]:
    """
    Token-based trimming: keep messages that fit within budget.
    
    Strategy:
    1. Always keep system messages (if keep_system=True)
    2. Keep most recent messages that fit in budget
    3. Estimate tokens as ~4 chars per token
    """
    from .utils.token_estimator import estimate_tokens
    
    system_msgs = [m for m in messages if m.role == "system"] if keep_system else []
    other_msgs = [m for m in messages if m.role != "system"] if keep_system else messages
    
    # Calculate system message tokens
    system_tokens = sum(estimate_tokens(m.content) for m in system_msgs)
    remaining_budget = budget_tokens - system_tokens
    
    if remaining_budget <= 0:
        return system_msgs  # Only system messages fit
    
    # Add messages from most recent backward
    kept_msgs = []
    current_tokens = 0
    
    for msg in reversed(other_msgs):
        msg_tokens = estimate_tokens(msg.content)
        if current_tokens + msg_tokens <= remaining_budget:
            kept_msgs.insert(0, msg)
            current_tokens += msg_tokens
        else:
            break
    
    # Combine and sort
    result = system_msgs + kept_msgs
    result.sort(key=lambda m: m.timestamp)
    return result


def trim_messages_by_turns(messages: List[Message], keep_turns: int, keep_system: bool = True) -> List[Message]:
    """
    Turn-based trimming: keep last K user+assistant pairs.
    
    A turn is a user message + assistant response pair.
    """
    system_msgs = [m for m in messages if m.role == "system"] if keep_system else []
    conversation_msgs = [m for m in messages if m.role in ("user", "assistant")]
    
    # Count turns from the end
    turns_kept = 0
    kept_msgs = []
    
    # Go backwards, counting user-assistant pairs
    i = len(conversation_msgs) - 1
    while i >= 0 and turns_kept < keep_turns:
        if conversation_msgs[i].role == "assistant":
            # Look for matching user message before it
            kept_msgs.insert(0, conversation_msgs[i])
            i -= 1
            while i >= 0 and conversation_msgs[i].role != "user":
                kept_msgs.insert(0, conversation_msgs[i])
                i -= 1
            if i >= 0:
                kept_msgs.insert(0, conversation_msgs[i])
                i -= 1
                turns_kept += 1
        else:
            i -= 1
    
    result = system_msgs + kept_msgs
    result.sort(key=lambda m: m.timestamp)
    return result


def generate_message_id(message: Message) -> str:
    """
    Generate deterministic message ID for deduplication.
    
    Uses hash of role + content + timestamp to create unique but
    reproducible ID.
    """
    content = f"{message.role}:{message.content}:{message.timestamp.isoformat()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]
