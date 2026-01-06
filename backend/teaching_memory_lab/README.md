# Teaching Memory Lab - LangGraph Memory Management Patterns

**Educational module demonstrating 4 different memory management strategies for LangGraph applications.**

## ⚡ NEW: Parallel Execution & Reducer Demonstration

This module now includes **parallel node execution** to teach how LangGraph handles concurrent operations and deterministic state merging. See [Parallel Execution Guide](../../../docs/PARALLEL_EXECUTION_GUIDE.md) for details.

**Key concepts demonstrated:**
- ✅ Fan-out: Multiple nodes run concurrently
- ✅ Fan-in: Reducers merge outputs deterministically
- ✅ No race conditions: Reducer-based conflict resolution
- ✅ Order independence: Commutativity & associativity

## Overview

This module is designed for teaching and comparing different approaches to conversation memory in LangGraph:

1. **Rolling Window** - Keep full message history with token/turn-based trimming
2. **Summary Buffer** - Maintain a running summary, trim old messages
3. **Facts Extraction** - Extract and store structured facts, trim messages
4. **Hybrid** - Combine summary + facts + on-demand RAG retrieval

Each strategy is implemented side-by-side in the same graph, allowing direct comparison of:
- Memory consumption
- Context retention
- Response quality
- Trade-offs and use cases

## Architecture

```
teaching_memory_lab/
├── state.py              # AppState with 6 explicit channels
├── reducers.py           # Deterministic channel merge logic
├── router.py             # Routing heuristics for memory modes
├── graph.py              # LangGraph builder
├── api.py                # FastAPI endpoints
├── nodes/                # 6 specialized nodes
│   ├── answer_node.py           # Final response generation
│   ├── summarizer_node.py       # Delta summary updates
│   ├── facts_extractor_node.py  # Structured facts extraction
│   ├── rag_recall_node.py       # On-demand RAG retrieval
│   ├── pii_filter_node.py       # PII masking
│   └── metrics_logger_node.py   # Observability
├── persistence/          # Checkpoint storage
│   ├── interfaces.py     # ICheckpointStore abstract interface
│   ├── file_store.py     # JSON file-based storage
│   └── sqlite_store.py   # SQLite-based storage
├── utils/                # Utilities
│   ├── token_estimator.py  # Token counting
│   ├── pii_masker.py       # PII detection/masking
│   └── retry.py            # Exponential backoff
└── tests/                # Test suite
    ├── test_reducers.py
    ├── test_trimming.py
    └── test_pii_masker.py
```

## State Design

The `AppState` uses 6 explicit channels with custom reducers:

```python
class AppState(BaseModel):
    messages: List[Message]              # Conversation history (deduplicated)
    summary: Optional[Summary]           # Running summary (versioned)
    facts: List[Fact]                   # Extracted facts (upsert by key)
    profile: Optional[UserProfile]       # User profile (replaced)
    trace: List[TraceEntry]             # Execution trace (append with limit)
    retrieved_context: Optional[RetrievedContext]  # RAG context (ephemeral)
```

**Key Design Principles:**
- **Deterministic reducers** - No race conditions, predictable merging
- **Idempotent operations** - Same input always produces same output
- **Conflict resolution** - Timestamp-based last-write-wins for facts
- **Deduplication** - SHA256 hash-based message IDs

## Memory Strategies

### 1. Rolling Window

**When to use:** Short conversations, debugging, full context needed

**How it works:**
- Keeps all messages in history
- Trims by token budget or conversation turns
- No summarization overhead
- Direct access to full conversation

**Configuration:**
```python
memory_mode = "rolling"
```

**Graph flow:**
```
metrics_logger → pii_filter → answer
```

**Trimming:**
- Token budget: Keep messages within budget, preserve system message
- Turn limit: Keep last N user/assistant pairs

### 2. Summary Buffer

**When to use:** Long conversations, general context retention

**How it works:**
- Maintains a running summary (delta updates)
- Aggressively trims old messages
- Summary provides context to LLM
- Lower memory footprint

**Configuration:**
```python
memory_mode = "summary"
```

**Graph flow:**
```
metrics_logger → summarizer → pii_filter → answer
```

**Trimming:**
- Keeps only last 2 conversation turns
- Summary preserved across all turns

### 3. Facts Extraction

**When to use:** User preferences, settings, profile-based interactions

**How it works:**
- Extracts structured facts (key-value pairs)
- Categories: preference, personal, context, decision
- Upsert logic: new facts added, existing updated
- Facts injected into answer prompt

**Configuration:**
```python
memory_mode = "facts"
```

**Graph flow:**
```
metrics_logger → facts_extractor → pii_filter → answer
```

**Fact structure:**
```python
{
  "key": "favorite_color",
  "value": "blue",
  "category": "preference",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 4. Hybrid (Advanced)

**When to use:** Complex applications, maximum context retention

**How it works:**
- Combines summary + facts + RAG retrieval
- Summary for general context
- Facts for structured data
- RAG for on-demand document retrieval
- Intelligent routing based on user query

**Configuration:**
```python
memory_mode = "hybrid"
```

**Graph flow:**
```
metrics_logger → summarizer → facts_extractor → [rag_recall] → pii_filter → answer
```

**RAG triggering:**
- Automatic when user references past information
- Keywords: "remember", "recall", "earlier", "before", "you said"

## API Endpoints

### POST /api/teaching/chat

Chat with specific memory mode.

**Request:**
```json
{
  "session_id": "session_123",
  "user_id": "user_456",
  "tenant_id": "teaching",
  "message": "What's my favorite color?",
  "memory_mode": "facts",
  "pii_mode": "placeholder"
}
```

**Response:**
```json
{
  "response": "Based on our conversation, your favorite color is blue.",
  "memory_snapshot": {
    "messages_count": 8,
    "facts_count": 3,
    "has_summary": true,
    "summary_version": 2,
    "has_retrieved_context": false,
    "trace_length": 4
  },
  "trace": [
    {"step": "metrics_logger", "action": "logged_metrics", "details": "..."},
    {"step": "facts_extractor", "action": "extracted_facts", "details": "..."},
    {"step": "pii_filter", "action": "masked_pii", "details": "..."},
    {"step": "answer", "action": "generated_response", "details": "..."}
  ]
}
```

### GET /api/teaching/session/{session_id}/checkpoints

List checkpoints for session (time-travel debugging).

**Query params:** `user_id`, `tenant_id`, `limit`

**Response:**
```json
[
  {
    "checkpoint_id": "cp_1234567890",
    "created_at": "2024-01-15T10:30:00",
    "metadata": {"memory_mode": "summary"}
  }
]
```

### POST /api/teaching/session/{session_id}/restore/{checkpoint_id}

Restore session to specific checkpoint.

**Query params:** `user_id`, `tenant_id`

**Response:**
```json
{
  "checkpoint_id": "cp_1234567890",
  "created_at": "2024-01-15T10:30:00",
  "metadata": {"memory_mode": "summary"},
  "snapshot": {
    "messages_count": 6,
    "facts_count": 2,
    "has_summary": true,
    "summary_version": 1,
    "has_retrieved_context": false,
    "trace_length": 3
  }
}
```

## Observability

### Metrics Logging

All interactions are logged to `data/teaching_metrics/session_{session_id}.jsonl`:

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "session_id": "session_123",
  "memory_mode": "summary",
  "total_tokens": 450,
  "message_count": 8,
  "facts_count": 3,
  "has_summary": true,
  "trace_length": 4
}
```

### Trace Entries

Every node execution adds a trace entry showing:
- Step name
- Action taken
- Details (counts, decisions, errors)

Use traces to understand graph execution flow.

## PII Handling

Two modes for sensitive data:

### Placeholder Mode (default)
```
"Email me at john@example.com" → "Email me at [EMAIL]"
```

### Pseudonymize Mode
```
"Email me at john@example.com" → "Email me at email_a3f5b9c2..."
```

**Supported patterns:**
- Email addresses
- Phone numbers (+1-555-1234, 555.123.4567)
- IBAN (GB82WEST12345698765432)
- Credit cards (4532-1234-5678-9010)

## Testing

Run tests with pytest:

```bash
cd backend/teaching_memory_lab
pytest tests/
```

**Test coverage:**
- `test_reducers.py` - Deterministic merging, deduplication
- `test_trimming.py` - Token/turn-based trimming logic
- `test_pii_masker.py` - PII detection and masking

## What to Observe

When comparing memory strategies, watch for:

### Memory Consumption
- **Rolling:** Grows linearly with conversation length
- **Summary:** Stays relatively constant (summary + 2 turns)
- **Facts:** Grows slowly (only new facts added)
- **Hybrid:** Medium (summary + facts + 3 turns)

### Context Retention
- **Rolling:** Perfect (all messages preserved)
- **Summary:** Good for general context, may lose specifics
- **Facts:** Excellent for structured data, poor for narratives
- **Hybrid:** Best overall, but most complex

### Response Quality
- **Rolling:** Best when all context fits in context window
- **Summary:** Good for long conversations
- **Facts:** Excellent for preference-based responses
- **Hybrid:** Most consistent across conversation types

### Latency
- **Rolling:** Fast (no processing overhead)
- **Summary:** Slower (LLM call for summarization)
- **Facts:** Slower (LLM call for extraction)
- **Hybrid:** Slowest (multiple LLM calls + RAG)

## Example Workflows

### Test Rolling Window
```bash
curl -X POST http://localhost:8000/api/teaching/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_rolling",
    "user_id": "user1",
    "message": "Hello! My name is Alice.",
    "memory_mode": "rolling"
  }'
```

### Test Summary Mode
```bash
# First message
curl -X POST http://localhost:8000/api/teaching/chat \
  -d '{"session_id": "test_summary", "user_id": "user1", "message": "Tell me about Paris.", "memory_mode": "summary"}'

# Second message (should reference summary)
curl -X POST http://localhost:8000/api/teaching/chat \
  -d '{"session_id": "test_summary", "user_id": "user1", "message": "What did I just ask about?", "memory_mode": "summary"}'
```

### Test Facts Extraction
```bash
curl -X POST http://localhost:8000/api/teaching/chat \
  -d '{"session_id": "test_facts", "user_id": "user1", "message": "I prefer dark mode and my favorite language is Python.", "memory_mode": "facts"}'
```

### Test Hybrid Mode
```bash
curl -X POST http://localhost:8000/api/teaching/chat \
  -d '{"session_id": "test_hybrid", "user_id": "user1", "message": "Remember when we discussed LangGraph architecture?", "memory_mode": "hybrid"}'
```

## Integration with Main App

To integrate with main app, add to `backend/main.py`:

```python
from teaching_memory_lab.api import router as teaching_router

app = FastAPI()
app.include_router(teaching_router)
```

## Key Learnings

This module demonstrates:

1. **Channel-based state** - Explicit channels with custom reducers prevent conflicts
2. **Deterministic merging** - Predictable behavior in distributed systems
3. **Memory trade-offs** - No one-size-fits-all solution
4. **Observability** - Traces and metrics critical for debugging
5. **PII handling** - Privacy considerations in memory systems
6. **Checkpointing** - Time-travel debugging enables better understanding

## Further Exploration

Try these experiments:

1. **Compare token usage** across modes for same 20-turn conversation
2. **Measure response latency** for each strategy
3. **Test context retention** - ask about turn 1 after 50 turns
4. **Stress test** - 1000-turn conversation with each mode
5. **Custom reducers** - Implement priority-based message retention
6. **Enhanced RAG** - Add semantic similarity threshold tuning

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/how-tos/persistence/)
- [Memory Management Patterns](https://python.langchain.com/docs/modules/memory/)
