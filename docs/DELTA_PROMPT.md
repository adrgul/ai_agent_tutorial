EXTEND THE EXISTING APPLICATION WITH A FULL RAG (Retrieval-Augmented Generation) ARCHITECTURE.

DO NOT rewrite or replace the existing agent, tools, memory, or frontend logic.
ONLY ADD the necessary components to demonstrate a production-style RAG pipeline that integrates cleanly into the current LangGraph-based agent.

================================================================================
RAG GOALS

Add a document-based knowledge layer to the agent using:
	•	ChromaDB as the vector database
	•	LangGraph for the RAG pipeline orchestration
	•	File-based document ingestion (TXT / MD)
	•	Chunking + embeddings
	•	Retrieval-before-tools rule (MANDATORY)

The RAG pipeline MUST be executed BEFORE any external tool calls.
The agent must always attempt retrieval from the vector database first,
because RAG knowledge may influence:
	•	the final answer
	•	OR the choice of tools

ALWAYS run retrieval on every user message (except “reset context”).
If retrieval returns relevant chunks, prefer them over tool calls when possible.

================================================================================
LANGGRAPH NODE ARCHITECTURE (MUST MATCH COURSE SLIDES)

Implement the RAG+Agent flow using the conceptual nodes below.
These are NOT built-in LangGraph classes; you MUST implement them as LangGraph nodes
(function nodes / runnable nodes) with these exact responsibilities.

Use these exact node role names in code and docs:
	1.	QueryRewriteNode (RAGQueryRewriteNode acceptable as alias)
	•	Purpose: optimize the user question for retrieval (better recall)
	•	Input: question, preferences (language, default_city), optional workflow_state
	•	Output: rewritten_query (string)
	•	Requirements:
	•	Normalize language (HU/EN), expand abbreviations, make query explicit
	•	Keep semantics; do not change intent
	•	Store rewritten_query into graph state
	2.	RetrieveNode (RAGRetrieveNode acceptable as alias)
	•	Purpose: retrieve relevant chunks from ChromaDB
	•	Input: rewritten_query, user_id, top_k
	•	Output: retrieved_chunks (list), retrieval_scores, max_similarity_score
	•	Requirements:
	•	Must run BEFORE tool decision
	•	Must support:
	•	vector search now
	•	“hybrid-ready” design (add BM25 later) via interface abstraction
	•	Must store results in graph state
	3.	ContextBuilderNode (RAGContextBuilderNode acceptable as alias)
	•	Purpose: turn retrieved chunks into prompt-ready context
	•	Input: retrieved_chunks + metadata + scores
	•	Output: rag_context (string), citations (list)
	•	Requirements:
	•	Deduplicate overlapping chunks (by source+chunk_index or similarity threshold)
	•	Sort by relevance
	•	Enforce a max token budget for context (configurable, e.g. 2k–3k tokens)
	•	Produce citation format: [RAG-1], [RAG-2], …
	•	Store rag_context + citations into graph state
	4.	LLMNode (Agent LLM nodes already exist; integrate via state)
	•	Purpose: generate answers and/or decisions using:
	•	conversation memory
	•	user profile
	•	workflow_state
	•	rag_context + citations
	•	Requirements:
	•	The agent’s decision prompt MUST include rag_context first (if any)
	•	The agent MUST cite RAG sources when using them
	•	If rag_context is insufficient, say so explicitly and then consider tools
	5.	GuardrailNode (RAG output validation)
	•	Purpose: safety + correctness checks before returning to user
	•	Requirements:
	•	Ensure citations are present when RAG claims are made
	•	Prevent hallucinated document references
	•	Optional: basic PII masking or policy checks (keep lightweight)
	6.	FeedbackNode (metrics + learning loop)
	•	Purpose: capture and persist metrics per request
	•	Must store metrics in session memory/state and expose to frontend debug panel
	•	Required metrics fields:
	•	retrieval_latency_ms
	•	retrieved_chunk_count
	•	max_similarity_score
	•	citations_used_count
	•	rag_used_in_response (boolean)
	•	total_latency_p50_p95 hooks (if available)

================================================================================
PROJECT STRUCTURE (MANDATORY)

All new RAG-related code MUST be placed under:

backend/
└── rag/
├── init.py
├── models.py              # RAG domain models (Document, Chunk, RetrievalResult)
├── chunking.py            # Chunking strategies (overlap + paragraph-aware)
├── embeddings.py          # Embedding service abstraction
├── vector_store.py        # ChromaDB adapter (repository pattern)
├── ingestion_service.py   # File ingestion + indexing pipeline
├── retrieval_service.py   # Retrieval logic (hybrid-ready, vector-first)
├── rag_nodes.py           # LangGraph RAG nodes (QueryRewriteNode, RetrieveNode, ContextBuilderNode, GuardrailNode, FeedbackNode)
└── rag_graph.py           # LangGraph subgraph for RAG

Do NOT place RAG logic inside existing agent or tool files.
Follow SOLID principles strictly:
	•	Single Responsibility
	•	Dependency inversion
	•	Interfaces / abstractions where reasonable

================================================================================
RAG PIPELINE (LANGGRAPH SUBGRAPH)

Implement a RAG pipeline as a LangGraph SUBGRAPH that can be called from the main agent graph.

RAG subgraph nodes MUST include:
	1.	QueryRewriteNode
	2.	RetrieveNode
	3.	ContextBuilderNode
	4.	GuardrailNode
	5.	FeedbackNode

OPTIONAL:
	•	Reranker step hook (not required to implement now, but design should allow it)
	•	Hybrid retrieval hook (BM25 later) via interface

RAG subgraph MUST run:
	•	BEFORE any tool decision nodes
	•	ALWAYS on every user message (except “reset context”)

================================================================================
AGENT INTEGRATION RULES

Modify the existing LangGraph agent flow as follows:

User Prompt
↓
RAG Subgraph (QueryRewrite → Retrieve → ContextBuild → Guardrail → Feedback)
↓
Agent Decide Node (LLM)
↓
[Optional Tool Nodes]
↓
Agent Finalize Node (LLM)
↓
Final GuardrailNode (existing or add lightweight validation)
↓
Return to User

The Agent Decide Node MUST receive:
	•	rag_context + citations + retrieval scores + rag_metrics
	•	conversation history
	•	user profile preferences
	•	workflow_state

CRITICAL RULE: Retrieval-before-tools
	•	The agent must ALWAYS attempt retrieval first.
	•	Only if rag_context is empty/low-confidence/insufficient should tools be considered.
	•	Even if tools are called, rag_context must remain available to the agent prompts.

================================================================================
AGENT PROMPTING RULES (STRICT)

Update ONLY the prompts (do not rewrite logic) so that the agent:
	•	Prefer RAG knowledge over tools when relevant
	•	Cite RAG sources using [RAG-x]
	•	If RAG context is insufficient:
	1.	explicitly say so (briefly)
	2.	then consider tool calls

Citation enforcement:
	•	If any claim uses retrieved doc text, it MUST include a citation.
	•	If the answer cannot be supported by retrieved documents:
“The available documents do not contain sufficient information.”

The agent MUST NEVER hallucinate document content or invent citations.

================================================================================
FILE UPLOAD (FRONTEND + BACKEND)

Frontend:
	•	Add a “Document Upload” section to the UI (minimal, demo-focused)
	•	Allow uploading .txt and .md files
	•	Show upload status and indexed chunk count
	•	Show list of uploaded filenames (optional)

Backend:
	•	Add endpoint:
POST /api/rag/upload

Behavior:
	•	Accept multipart/form-data (file + user_id)
	•	Validate file type (.txt, .md only)
	•	Store raw file under:
data/rag/uploads/{user_id}/
	•	Trigger ingestion pipeline:
	•	load file
	•	chunk
	•	embed
	•	store in ChromaDB
	•	Return JSON:
	•	number of chunks created
	•	filename
	•	success status

Also add:
	•	GET /api/rag/stats
	•	documents count, chunks count, chroma path, collection info per user

================================================================================
CHUNKING REQUIREMENTS

Chunking defaults:
	•	Chunk size: 500–700 tokens
	•	Overlap: 10–15%
	•	Chunk boundaries should respect paragraphs if possible
	•	Preserve headings for MD (treat headings as strong boundaries)

Each chunk MUST store metadata:
	•	user_id
	•	document_id
	•	filename
	•	chunk_index
	•	created_at
	•	optional: section_heading (for MD)

================================================================================
CHROMADB REQUIREMENTS
	•	Use ChromaDB as the vector store
	•	Persist DB to disk:
data/rag/chroma/
	•	One collection per user OR user_id as metadata filter (choose one; document clearly)
	•	Use cosine similarity
	•	Abstract ChromaDB behind a VectorStore interface (repository pattern)

Chunk storage format (minimum):
	•	id
	•	embedding vector
	•	text
	•	metadata (as above)

================================================================================
RAG MEMORY & STATE

Extend the agent state with:

rag_context:
	•	rewritten_query
	•	retrieved_chunks
	•	citations
	•	retrieval_scores
	•	used_in_response: boolean

rag_metrics:
	•	retrieval_latency_ms
	•	retrieved_chunk_count
	•	max_similarity_score

These MUST be exposed to:
	•	Debug panel (frontend)
	•	FeedbackNode metrics

DO NOT remove existing session memory.
Only extend it.

================================================================================
CITATION RULES

When RAG context is used:
	•	The final answer MUST include citations like:
[RAG-1], [RAG-2]

If the answer cannot be supported by retrieved documents:
	•	The agent MUST say:
“The available documents do not contain sufficient information.”

The agent MUST NEVER hallucinate document content.

================================================================================
LANGGRAPH DEMO REQUIREMENTS (IMPORTANT FOR COURSE)
	•	The RAG pipeline must be implemented as a distinct LangGraph graph (subgraph)
	•	The main agent graph must CALL the RAG graph
	•	Graph structure should be easy to visualize and explain
	•	Nodes must be named clearly and match the course slide concepts:
	•	QueryRewriteNode
	•	RetrieveNode
	•	ContextBuilderNode
	•	GuardrailNode
	•	FeedbackNode

In README and inline comments, explicitly map:
Prompt → Decision → Tool → Observation → Memory
and show where RAG sits (retrieval as a “pre-tool knowledge fetch”).

================================================================================
NON-GOALS
	•	Do NOT add authentication
	•	Do NOT add PDF parsing (TXT / MD only)
	•	Do NOT remove or refactor existing tools
	•	Do NOT break existing agent behavior

================================================================================
FINAL NOTE

This RAG extension is intended for:
	•	AI Agent programming education
	•	Demonstrating LangGraph-based RAG
	•	Showing retrieval-before-tools decision making
	•	Clean architecture and SOLID design

Ensure the code is readable, modular, and heavily commented,
especially around:
	•	RAG LangGraph nodes
	•	Retrieval flow
	•	State propagation
	•	How citations are built and enforced
	•	Where metrics are collected and exposed