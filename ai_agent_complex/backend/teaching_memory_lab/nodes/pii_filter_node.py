"""
PII Filter Node - Mask sensitive information before persistence.

Applies before checkpointing to ensure PII doesn't leak to storage.
Uses PIIMasker utility with configurable mode (placeholder/pseudonymize).
"""
from typing import Dict, Any

from ..state import AppState, Message, TraceEntry
from ..utils.pii_masker import PIIMasker


async def pii_filter_node(state: AppState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask PII in messages before persistence.
    
    Args:
        state: Current AppState
        config: Contains pii_mode ("placeholder" or "pseudonymize")
    
    Returns:
        Update to messages channel with PII masked
    """
    pii_mode = config.get("configurable", {}).get("pii_mode", "placeholder")
    masker = PIIMasker(mode=pii_mode)
    
    masked_messages = []
    pii_found_count = 0
    
    for msg in state.messages:
        # Mask content
        masked_content = masker.mask_pii(msg.content)
        
        # Check if PII was found
        if masked_content != msg.content:
            pii_found_count += 1
        
        # Create new message with masked content
        masked_msg = Message(
            role=msg.role,
            content=masked_content,
            timestamp=msg.timestamp,
            message_id=msg.message_id,
            metadata=msg.metadata
        )
        masked_messages.append(masked_msg)
    
    # Add trace entry
    trace_entry = TraceEntry(
        step="pii_filter",
        action="masked_pii",
        details=f"Mode: {pii_mode}, PII found in {pii_found_count} messages"
    )
    
    return {
        "messages": masked_messages,
        "trace": [trace_entry]
    }
