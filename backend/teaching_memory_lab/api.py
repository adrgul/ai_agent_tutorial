"""
FastAPI Router for Teaching Memory Lab.

Endpoints:
- POST /api/teaching/chat - Chat with specific memory mode
- GET /api/teaching/session/{session_id}/checkpoints - List checkpoints
- POST /api/teaching/session/{session_id}/restore/{checkpoint_id} - Restore from checkpoint
"""
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .state import AppState, Message, MemorySnapshot
from .graph import create_teaching_graph
from .persistence import FileCheckpointStore, SQLiteCheckpointStore


# Initialize router
router = APIRouter(prefix="/api/teaching", tags=["teaching"])

# Initialize persistence (use file store by default for teaching)
checkpoint_store = FileCheckpointStore()

# Initialize graph
graph = create_teaching_graph()


# Request/Response models
class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    tenant_id: str = "teaching"
    message: str
    memory_mode: str = "rolling"  # rolling, summary, facts, hybrid
    pii_mode: str = "placeholder"  # placeholder, pseudonymize


class ChatResponse(BaseModel):
    response: str
    memory_snapshot: Optional[Dict[str, Any]] = None
    trace: List[Dict[str, Any]] = []


class CheckpointInfo(BaseModel):
    checkpoint_id: str
    created_at: str
    metadata: Dict[str, Any]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with teaching memory mode.
    
    This endpoint demonstrates different memory strategies.
    """
    # Create user message
    user_message = Message(
        role="user",
        content=request.message,
        timestamp=datetime.now()
    )
    
    # Load existing state or create new
    checkpoint_data = await checkpoint_store.load_checkpoint(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        session_id=request.session_id
    )
    
    if checkpoint_data:
        # Restore from checkpoint
        state_dict = checkpoint_data.get("state", {})
        state = AppState(**state_dict)
    else:
        # New session
        state = AppState(messages=[])
    
    # Add user message
    state.messages.append(user_message)
    
    # Run graph
    config = {
        "configurable": {
            "session_id": request.session_id,
            "user_id": request.user_id,
            "tenant_id": request.tenant_id,
            "memory_mode": request.memory_mode,
            "pii_mode": request.pii_mode
        }
    }
    
    try:
        result = await graph.ainvoke(state.model_dump(), config)
        
        # Convert result back to AppState
        final_state = AppState(**result)
        
        # Save checkpoint
        checkpoint_id = f"cp_{int(datetime.now().timestamp() * 1000)}"
        await checkpoint_store.save_checkpoint(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            session_id=request.session_id,
            checkpoint_id=checkpoint_id,
            state_data=final_state.model_dump(),
            metadata={"memory_mode": request.memory_mode}
        )
        
        # Get assistant response (last message)
        assistant_messages = [msg for msg in final_state.messages if msg.role == "assistant"]
        response_text = assistant_messages[-1].content if assistant_messages else "No response generated"
        
        # Analyze trace to determine which nodes executed and if they were parallel
        parallel_nodes = []
        reducers_used = []
        
        # Check trace for parallel execution markers
        trace_steps = [entry.step for entry in final_state.trace]
        
        # If we see both summarizer and facts_extractor in trace, they ran in parallel
        if "summarizer" in trace_steps and "facts_extractor" in trace_steps:
            parallel_nodes = ["summarizer", "facts_extractor"]
            reducers_used = ["summary_reducer", "facts_reducer", "messages_reducer", "trace_reducer"]
        
        # Create memory snapshot for debugging
        from ..utils.token_estimator import estimate_messages_tokens
        
        snapshot = MemorySnapshot(
            mode=request.memory_mode,
            messages_kept_count=len(final_state.messages),
            message_tokens_estimate=estimate_messages_tokens(final_state.messages),
            summary_version=final_state.summary.version if final_state.summary else None,
            summary_length=len(final_state.summary.content) if final_state.summary else None,
            facts_count=len(final_state.facts),
            sample_facts=[
                {"key": k, "value": v.value, "category": v.category}
                for k, v in list(final_state.facts.items())[:3]
            ],
            rag_recall_used=final_state.retrieved_context is not None and len(final_state.retrieved_context) > 0,
            retrieved_context_count=len(final_state.retrieved_context) if final_state.retrieved_context else 0,
            checkpoint_id=checkpoint_id,
            trace_entries=len(final_state.trace),
            total_tokens_estimate=estimate_messages_tokens(final_state.messages),
            parallel_nodes_executed=parallel_nodes,  # PARALLEL EXECUTION INFO
            reducers_applied=reducers_used  # PARALLEL EXECUTION INFO
        )
        
        return ChatResponse(
            response=response_text,
            memory_snapshot=snapshot.model_dump(),
            trace=[trace.model_dump() for trace in final_state.trace]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@router.get("/session/{session_id}/checkpoints", response_model=List[CheckpointInfo])
async def list_checkpoints(
    session_id: str,
    user_id: str,
    tenant_id: str = "teaching",
    limit: int = 10
):
    """
    List checkpoints for a session.
    
    Useful for understanding how memory evolved over time.
    """
    try:
        checkpoints = await checkpoint_store.list_checkpoints(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
        
        return [
            CheckpointInfo(
                checkpoint_id=cp["checkpoint_id"],
                created_at=cp["created_at"],
                metadata=cp["metadata"]
            )
            for cp in checkpoints
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing checkpoints: {str(e)}")


@router.post("/session/{session_id}/restore/{checkpoint_id}")
async def restore_checkpoint(
    session_id: str,
    checkpoint_id: str,
    user_id: str,
    tenant_id: str = "teaching"
):
    """
    Restore session to specific checkpoint.
    
    This is useful for teaching - show how memory state looked at different points.
    """
    try:
        checkpoint_data = await checkpoint_store.load_checkpoint(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            checkpoint_id=checkpoint_id
        )
        
        if not checkpoint_data:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
        
        # Create memory snapshot from checkpoint
        state_dict = checkpoint_data.get("state", {})
        state = AppState(**state_dict)
        
        snapshot = MemorySnapshot(
            messages_count=len(state.messages),
            facts_count=len(state.facts),
            has_summary=state.summary is not None,
            summary_version=state.summary.version if state.summary else 0,
            has_retrieved_context=state.retrieved_context is not None,
            trace_length=len(state.trace)
        )
        
        return {
            "checkpoint_id": checkpoint_id,
            "created_at": checkpoint_data.get("created_at"),
            "metadata": checkpoint_data.get("metadata", {}),
            "snapshot": snapshot.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error restoring checkpoint: {str(e)}")
