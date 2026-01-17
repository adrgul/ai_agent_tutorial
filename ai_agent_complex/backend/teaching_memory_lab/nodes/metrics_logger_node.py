"""
Metrics Logger Node - Track token usage and latency.

Records:
- Token counts (input, output, total)
- Latency per node
- Routing decisions
- Memory strategy used

Writes to data/teaching_metrics/ as JSONL for easy analysis.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from ..state import AppState, TraceEntry
from ..utils.token_estimator import estimate_messages_tokens


async def metrics_logger_node(state: AppState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Log metrics for observability.
    
    Args:
        state: Current AppState
        config: Contains session_id, memory_mode, etc.
    
    Returns:
        Update to trace channel with metrics entry
    """
    session_id = config.get("configurable", {}).get("session_id", "unknown")
    memory_mode = config.get("configurable", {}).get("memory_mode", "unknown")
    
    # Estimate token usage from messages
    total_tokens = estimate_messages_tokens(state.messages)
    
    # Create metrics entry
    metrics_entry = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "memory_mode": memory_mode,
        "total_tokens": total_tokens,
        "message_count": len(state.messages),
        "facts_count": len(state.facts),
        "has_summary": state.summary is not None,
        "trace_length": len(state.trace)
    }
    
    # Write to JSONL file
    metrics_dir = Path("data/teaching_metrics")
    metrics_dir.mkdir(parents=True, exist_ok=True)
    
    metrics_file = metrics_dir / f"session_{session_id}.jsonl"
    
    try:
        with open(metrics_file, 'a') as f:
            f.write(json.dumps(metrics_entry, default=str) + "\n")
    except Exception as e:
        print(f"Error writing metrics: {e}")
    
    # Add trace entry
    trace_entry = TraceEntry(
        step="metrics_logger",
        action="logged_metrics",
        details=f"Tokens: {total_tokens}, Messages: {len(state.messages)}"
    )
    
    return {"trace": [trace_entry]}
