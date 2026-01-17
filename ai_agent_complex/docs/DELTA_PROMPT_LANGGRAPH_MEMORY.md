You are working in an existing repository called AI Agent Complex (FastAPI backend + React frontend). Follow the existing Clean Architecture style (domain / services / infrastructure / rag). The current app already supports: chat endpoint, tools, RAG via Chroma, file-based persistence for users + sessions, and a LangGraph agent. 

pasted

Goal

Create a teaching-focused extension that demonstrates multiple LangGraph memory management techniques side-by-side, with clear code structure and short comments explaining “what this is for”. Students should be able to run it and see how memory behaviors differ.

Hard constraints

Do not modify existing production code paths unless strictly necessary (prefer integration via new endpoints / optional mode flags).

Put all new files under a new top-level folder:
backend/teaching_memory_lab/

Keep code readable and educational. Add concise comments to each new class and important method.

Follow SOLID: each module should have a single clear purpose.

Provide a small README in the new folder with instructions and “what to observe”.

Add lightweight tests (unit-style) for the reducers/mergers and trimming logic.

What to implement
1) Memory taxonomy: implement 4 memory strategies

Implement four strategies that can be selected per request (e.g., memory_mode in request body or query param). Each strategy should produce a memory_snapshot so the UI/debug panel can show differences.

Rolling Window (Turn-based + Token-based trimming)

Keep last K turns (user+assistant pairs) and/or enforce a token budget.

Always keep system messages.

Demonstrate: trim_by_budget(messages, budget_tokens, keep_system=True).

Summary Buffer (Rolling summary + message trimming)

Maintain a persistent summary string for the session.

When message count or token budget exceeds threshold, call summarizer node:

Update summary (delta summary approach).

Trim old messages.

Provide a versioned summary schema (e.g., summary_version).

Facts Memory (Structured facts extraction + upsert)

Extract stable “facts” from conversation (e.g., preferences, stable constraints).

Store facts in a separate channel (not mixed with raw messages).

Support idempotent upsert: do not duplicate same fact.

Include a simple canonical fact model like:

{"key": "preferred_language", "value": "hu", "confidence": 0.9, "source": "user", "updated_at": ...}

Make it easy to add new fact types later.

Hybrid: Summary + On-demand RAG Recall

Always use summary for long-term context.

Only perform “memory recall” from vector store when router decides the question needs older detail.

Use small top-k (3–5), optional re-rank hook, and a relevance threshold.

Store retrieved snippets as a retrieved_context channel for that turn (not permanently unless configured).

2) Channels-based state design (explicit channels)

Create an educational AppState (Pydantic or TypedDict) with explicit channels:

messages

summary

facts

profile (stable user attributes; load/save separately)

trace (tools used, decisions, costs/latency metadata)

retrieved_context (RAG recall snippets for the current turn)

Explain in comments why channels reduce coupling and why reducers matter.

3) Reducers / mergers (deterministic, conflict-safe)

Implement deterministic reducers for channel merges, including:

messages: append + optional dedup by message id/hash

facts: merge by key (last-write-wins but deterministic using timestamp + tie-breaker)

trace: append, keep bounded size

summary: replace (versioned)
Add unit tests proving determinism and no “last writer chaos” in parallel merges.

4) Checkpointing & persistence backends (teaching version)

The production app uses file JSON persistence; for the teaching lab:

Implement an abstraction: ICheckpointStore and two implementations:

FileCheckpointStore (JSON files under data/teaching_checkpoints/)

SQLiteCheckpointStore (single sqlite file under data/teaching_checkpoints/checkpoints.sqlite)

Store checkpoints by:

tenant_id, user_id, session_id, checkpoint_id, created_at

Add composite indexes in SQLite (documented in code).

Provide a simple API:

save_checkpoint(state, checkpoint_id)

load_checkpoint(checkpoint_id) or “latest for session”

list_checkpoints(session_id)

This should demonstrate “state + persistence” and “restore / branch” behavior.

5) Router node types (memory-aware routing)

Create a teaching LangGraph that includes these node types:

router_node: decides next step:

summarize if summary needed

recall_rag if needs older details

else answer

summarizer_node: updates summary + trims messages

facts_extractor_node: updates facts store

pii_filter_node: masks PII before saving messages/summaries

metrics_logger_node: records token/latency estimates and tool usage

answer_node: produces final response with appropriate context

Routing heuristics:

need_summary: if messages tokens exceed threshold or N messages passed

requires_knowledge: if query references old topic OR asks for detail not in recent window OR user explicitly asks “what did I say earlier…”

on-demand recall: only run RAG recall if relevance > threshold

6) Error handling, idempotency, retry/backoff (teaching examples)

Implement:

Idempotency keys for persistence writes (hash of session_id + message_id)

Retry + exponential backoff wrapper for external tool calls (configurable)

Demonstrate optimistic locking concept in SQLite store (e.g., version column) OR safe compare-and-swap simulation

Ensure deterministic reduction when branches merge (no nondeterministic ordering)

7) PII handling & retention (teaching)

Add a simple PII masker:

emails, phone numbers, addresses-ish patterns, IBAN-like patterns

Use regex + placeholder tokens (e.g., [EMAIL], [PHONE])

Optionally salted hash mode for “consistent pseudonymization”
Document retention policy in README (even if not enforced everywhere):

messages: 30/90 days idea

summaries: 365 days idea

8) Observability hooks (teaching)

Add metrics capture:

latency p50/p95 placeholders (store raw timings)

tokens in/out estimate per turn

summary hit rate

RAG recall hit@k indicator

cache hit/miss counters (even if cache is a stub)
Export to:

JSON log lines (file) under data/teaching_metrics/

and in API response memory_snapshot.trace

API surface (new endpoints only)

Add new FastAPI routes under something like:

POST /api/teaching/chat

GET /api/teaching/session/{session_id}/checkpoints

POST /api/teaching/session/{session_id}/restore/{checkpoint_id}

Request for teaching chat:

{
  "tenant_id": "demo",
  "user_id": "user_123",
  "session_id": "session_456",
  "message": "…",
  "memory_mode": "rolling|summary|facts|hybrid",
  "debug": true
}


Response should include:

final_answer

tools_used

memory_snapshot including:

mode

messages_kept_count

summary_version and summary_length

facts_count (+ a few example facts)

rag_recall_used boolean and retrieved_context_count

checkpoint_id written for this turn

trace (token estimate, latency, cache hits)

Frontend (minimal changes, optional)

If feasible with minimal risk:

Add a “Teaching mode” toggle in DebugPanel that calls /api/teaching/chat.

Otherwise, backend-only is acceptable, but ensure endpoints are fully testable via curl.

File layout to create (example)

Create these new files under backend/teaching_memory_lab/:

README.md (how to run + what to observe)

api.py (FastAPI router for teaching endpoints)

state.py (AppState + channels)

reducers.py (deterministic reducers + tests)

router.py (routing heuristics)

graph.py (LangGraph teaching graph builder)

nodes/

answer_node.py

summarizer_node.py

facts_extractor_node.py

rag_recall_node.py

pii_filter_node.py

metrics_logger_node.py

persistence/

interfaces.py (ICheckpointStore)

file_store.py

sqlite_store.py

models.py (session/checkpoint/message schemas if needed)

utils/

token_estimator.py (simple token estimate helper)

pii_masker.py

retry.py

tests/

test_reducers.py

test_trimming.py

test_pii_masker.py

All new code must be documented with short, precise comments.

Acceptance criteria

I can run the app and call /api/teaching/chat with different memory_mode values and see different memory_snapshot outputs.

Rolling window trims messages; summary buffer creates and updates summaries; facts mode extracts/upserts facts; hybrid triggers RAG recall only when needed.

Checkpoints are created per turn and can be listed and restored.

Reducers are deterministic and tested.

PII is masked before persistence.

Metrics/trace show token+latency estimates and whether RAG recall ran.

Implementation notes

Reuse existing RAG services/tooling where possible, but wrap them so the teaching module is isolated.

Keep dependencies minimal; prefer stdlib + existing project deps.

Keep the code “teachable”: clarity > cleverness.

Now implement this entire teaching module.