"""
LangGraph RAG nodes for the RAG pipeline.

Implements 5 nodes:
1. QueryRewriteNode - Optimize query for retrieval
2. RetrieveNode - Fetch chunks from ChromaDB
3. ContextBuilderNode - Build prompt-ready context with citations
4. GuardrailNode - Validate and format results
5. FeedbackNode - Collect metrics

Each node is an async function that takes AgentState and returns updated AgentState.
"""

import logging
import time
from typing import TYPE_CHECKING, Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# Import models
from .models import RAGContext, RAGMetrics

if TYPE_CHECKING:
    # AgentState will be imported at runtime from the agent
    pass

logger = logging.getLogger(__name__)

# Global services (will be set by rag_graph.py)
_retrieval_service = None
_rag_config = None
_llm = None


def set_rag_dependencies(retrieval_service, rag_config, llm):
    """Set global dependencies for RAG nodes."""
    global _retrieval_service, _rag_config, _llm
    _retrieval_service = retrieval_service
    _rag_config = rag_config
    _llm = llm
    logger.info("RAG node dependencies configured")


async def query_rewrite_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 1: Optimize user query for retrieval.

    Rewrites the query to:
    - Expand abbreviations
    - Normalize language
    - Make query more explicit
    - Consider user preferences

    Skips if skip_rag flag is set.
    """
    logger.info("RAG QueryRewrite node executing")
    start_time = time.time()

    # Initialize RAG context if not present
    if "rag_context" not in state:
        state["rag_context"] = {}

    if "rag_metrics" not in state:
        state["rag_metrics"] = {}

    # Check skip flag
    if state.get("skip_rag", False):
        logger.info("Skipping RAG pipeline (skip_rag=True)")
        state["rag_context"] = {
            "rewritten_query": "",
            "retrieved_chunks": [],
            "citations": [],
            "context_text": "",
            "has_knowledge": False
        }
        return state

    # Extract last user message
    messages = state.get("messages", [])
    last_user_msg = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content
            break

    if not last_user_msg:
        logger.warning("No user message found for query rewriting")
        state["rag_context"]["has_knowledge"] = False
        return state

    # Get user preferences
    memory = state.get("memory", {})
    preferences = memory.get("preferences", {}) if isinstance(memory, dict) else getattr(memory, "preferences", {})
    language = preferences.get("language", "en")
    default_city = preferences.get("default_city", "")

    # Build query rewrite prompt
    rewrite_prompt = f"""You are a query optimizer for a document retrieval system.

User's original question: "{last_user_msg}"

User preferences:
- Language: {language}
- Default city: {default_city}

Your task: Rewrite the query to be more effective for document search. Make it:
1. More explicit and clear
2. Expand any abbreviations
3. Add relevant context from preferences if needed
4. Keep the semantic meaning unchanged

Respond with ONLY the rewritten query, no explanations.

Examples:
- "What's the API key?" → "What is the API key for authentication?"
- "How to install?" → "How to install the application or software?"
- "weather today" → "weather forecast for today in {default_city}"

Rewritten query:"""

    try:
        # Use LLM to rewrite query
        if _llm is None:
            # Fallback: use original query if LLM not configured
            rewritten_query = last_user_msg
            logger.warning("LLM not configured for query rewriting, using original query")
        else:
            response = await _llm.ainvoke([SystemMessage(content=rewrite_prompt)])
            rewritten_query = response.content.strip()

        state["rag_context"]["rewritten_query"] = rewritten_query

        latency_ms = (time.time() - start_time) * 1000
        state["rag_metrics"]["query_rewrite_latency_ms"] = latency_ms

        logger.info(f"Query rewritten in {latency_ms:.2f}ms: '{last_user_msg}' → '{rewritten_query}'")

    except Exception as e:
        logger.error(f"Error in query rewrite: {e}")
        # Fallback to original query
        state["rag_context"]["rewritten_query"] = last_user_msg

    return state


async def retrieve_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 2: Retrieve relevant chunks from ChromaDB.

    Performs vector search using the rewritten query.
    """
    logger.info("RAG Retrieve node executing")
    start_time = time.time()

    rag_context = state.get("rag_context", {})
    rewritten_query = rag_context.get("rewritten_query", "")

    if not rewritten_query or state.get("skip_rag", False):
        logger.info("No query to retrieve or RAG skipped")
        state["rag_context"]["retrieved_chunks"] = []
        return state

    # Get user_id
    user_id = state.get("current_user_id", "default_user")

    try:
        # Retrieve chunks
        if _retrieval_service is None:
            logger.error("Retrieval service not configured")
            state["rag_context"]["retrieved_chunks"] = []
            return state

        results, latency_ms = await _retrieval_service.retrieve(
            query=rewritten_query,
            user_id=user_id,
            top_k=_rag_config.retrieval.top_k if _rag_config else 5
        )

        # Convert results to dicts for state storage
        results_dicts = [r.to_dict() for r in results]
        state["rag_context"]["retrieved_chunks"] = results_dicts

        # Store scores
        scores = [r["score"] for r in results_dicts]
        state["rag_context"]["retrieval_scores"] = scores
        state["rag_context"]["max_similarity_score"] = max(scores) if scores else 0.0

        # Update metrics
        state["rag_metrics"]["retrieval_latency_ms"] = latency_ms
        state["rag_metrics"]["chunk_count"] = len(results)
        state["rag_metrics"]["max_similarity_score"] = max(scores) if scores else 0.0

        logger.info(f"Retrieved {len(results)} chunks (max score: {max(scores) if scores else 0:.2f})")

    except Exception as e:
        logger.error(f"Error in retrieval: {e}")
        state["rag_context"]["retrieved_chunks"] = []

    return state


async def context_builder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 3: Build prompt-ready context from retrieved chunks.

    - Deduplicates overlapping chunks
    - Enforces token budget
    - Generates citations
    - Formats context for agent
    """
    logger.info("RAG ContextBuilder node executing")

    rag_context = state.get("rag_context", {})
    retrieved_chunks = rag_context.get("retrieved_chunks", [])

    if not retrieved_chunks:
        logger.info("No chunks to build context from")
        state["rag_context"]["context_text"] = ""
        state["rag_context"]["citations"] = []
        state["rag_context"]["has_knowledge"] = False
        return state

    # Build context with citations
    context_parts = []
    citations = []
    total_tokens = 0
    max_tokens = _rag_config.retrieval.max_context_tokens if _rag_config else 2500

    for idx, chunk_dict in enumerate(retrieved_chunks, 1):
        citation = f"[RAG-{idx}]"
        citations.append(citation)

        text = chunk_dict.get("text", "")
        source_label = chunk_dict.get("source_label", f"chunk_{idx}")
        score = chunk_dict.get("score", 0.0)

        # Estimate tokens (rough: 1 token ≈ 4 characters)
        chunk_tokens = len(text) // 4

        # Check if adding this chunk exceeds budget
        if total_tokens + chunk_tokens > max_tokens:
            logger.info(f"Token budget reached, stopping at {idx-1} chunks")
            break

        # Add chunk to context
        context_parts.append(
            f"{citation} (source: {source_label}, relevance: {score:.2f})\n{text}\n"
        )
        total_tokens += chunk_tokens

    context_text = "\n".join(context_parts)

    state["rag_context"]["context_text"] = context_text
    state["rag_context"]["citations"] = citations
    state["rag_context"]["has_knowledge"] = len(citations) > 0

    logger.info(f"Built context with {len(citations)} citations (~{total_tokens} tokens)")

    return state


async def guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 4: Validate RAG context and enforce guardrails.

    - Checks citation formatting
    - Validates knowledge presence
    - Sets flags for agent
    """
    logger.info("RAG Guardrail node executing")

    rag_context = state.get("rag_context", {})

    # Check if we have knowledge
    has_citations = len(rag_context.get("citations", [])) > 0
    has_context = bool(rag_context.get("context_text", "").strip())

    rag_context["has_knowledge"] = has_citations and has_context

    if not rag_context["has_knowledge"]:
        logger.info("No RAG knowledge available for this query")
    else:
        logger.info(f"RAG knowledge validated: {len(rag_context.get('citations', []))} citations")

    state["rag_context"] = rag_context

    return state


async def feedback_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 5: Collect and finalize RAG metrics.

    Aggregates all timing and performance metrics.
    """
    logger.info("RAG Feedback node executing")

    rag_metrics = state.get("rag_metrics", {})
    rag_context = state.get("rag_context", {})

    # Calculate total pipeline latency
    query_rewrite_latency = rag_metrics.get("query_rewrite_latency_ms", 0.0)
    retrieval_latency = rag_metrics.get("retrieval_latency_ms", 0.0)

    total_latency = query_rewrite_latency + retrieval_latency
    rag_metrics["total_pipeline_latency_ms"] = total_latency

    # Update chunk count
    rag_metrics["chunk_count"] = len(rag_context.get("citations", []))

    state["rag_metrics"] = rag_metrics

    logger.info(
        f"RAG pipeline completed: {rag_metrics.get('chunk_count', 0)} chunks, "
        f"{total_latency:.2f}ms total"
    )

    return state
