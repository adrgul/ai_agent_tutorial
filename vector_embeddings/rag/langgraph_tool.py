"""
LangGraph tool integration for RAG.

Exposes RAG functionality as a tool that can be used by the agent.
"""

from typing import Dict, Any, Optional
from rag.rag_pipeline import RAGPipeline
from rag.config import RAGConfig


def create_rag_tool(default_tenant: str = "default"):
    """
    Create a RAG tool function for LangGraph.
    
    Args:
        default_tenant: Default tenant ID if not provided in tool call.
    
    Returns:
        Tool function.
    """
    
    def rag_ask_tool(
        question: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        top_k: int = 5,
        mode: str = "hybrid",
        rerank: bool = False
    ) -> Dict[str, Any]:
        """
        RAG Ask Tool - Search uploaded documents and answer questions.
        
        Use this tool when the user asks about:
        - Content in uploaded documents
        - Information from their files
        - Questions like "based on my documents", "in the text I uploaded", etc.
        
        Args:
            question: The question to answer.
            user_id: User ID (uses tenant_id if not provided).
            tenant_id: Tenant ID for document isolation (uses user_id if not provided).
            top_k: Number of chunks to retrieve (default: 5).
            mode: Retrieval mode - "dense", "sparse", or "hybrid" (default: "hybrid").
            rerank: Whether to rerank results using LLM (default: False).
        
        Returns:
            Dict with answer, citations, and retrieved chunks.
        """
        # Determine tenant_id
        if tenant_id is None:
            tenant_id = user_id if user_id else default_tenant
        
        # Initialize pipeline
        pipeline = RAGPipeline(tenant_id, RAGConfig())
        
        # Ask question
        answer = pipeline.ask(
            question=question,
            top_k=top_k,
            mode=mode,
            rerank=rerank,
            rerank_strategy="llm" if rerank else "embed"
        )
        
        # Format response for agent
        return {
            "answer": answer.answer,
            "citations": answer.citations,
            "sources_count": len(answer.retrieved_chunks),
            "sources": [
                {
                    "text": r.chunk.text[:300] + "..." if len(r.chunk.text) > 300 else r.chunk.text,
                    "source": r.chunk.get_source_label(),
                    "score": r.score
                }
                for r in answer.retrieved_chunks[:3]  # Top 3 for context
            ],
            "mode": answer.mode,
            "rerank_used": answer.rerank_metadata is not None
        }
    
    # Set tool metadata
    rag_ask_tool.__name__ = "rag_ask"
    rag_ask_tool.__doc__ = """Search uploaded documents and answer questions based on their content.
    
Use this tool when the user:
- Asks about content in documents they uploaded
- Says "based on my documents", "in the files", "search my uploads"
- Wants information from their ingested text

Retrieves relevant chunks and generates an answer with citations."""
    
    return rag_ask_tool


def create_rag_retrieve_tool(default_tenant: str = "default"):
    """
    Create a RAG retrieve tool (search only, no answer generation).
    
    Args:
        default_tenant: Default tenant ID.
    
    Returns:
        Tool function.
    """
    
    def rag_retrieve_tool(
        query: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        top_k: int = 5,
        mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        RAG Retrieve Tool - Search uploaded documents without generating an answer.
        
        Use this for simple document search when the user wants to see
        matching content without a synthesized answer.
        
        Args:
            query: Search query.
            user_id: User ID.
            tenant_id: Tenant ID (uses user_id if not provided).
            top_k: Number of results (default: 5).
            mode: Retrieval mode - "dense", "sparse", or "hybrid".
        
        Returns:
            Dict with search results.
        """
        if tenant_id is None:
            tenant_id = user_id if user_id else default_tenant
        
        pipeline = RAGPipeline(tenant_id, RAGConfig())
        
        result = pipeline.retrieve(
            query=query,
            top_k=top_k,
            mode=mode
        )
        
        return {
            "results_count": len(result["results"]),
            "results": [
                {
                    "text": r.chunk.text,
                    "source": r.chunk.get_source_label(),
                    "score": r.score,
                    "dense_score": r.dense_score,
                    "sparse_score": r.sparse_score
                }
                for r in result["results"]
            ],
            "mode": result["mode"]
        }
    
    rag_retrieve_tool.__name__ = "rag_retrieve"
    rag_retrieve_tool.__doc__ = """Search uploaded documents and return matching chunks.
    
Use for simple search without answer generation."""
    
    return rag_retrieve_tool


# Example usage with LangGraph
def register_rag_tools(graph_builder, default_tenant: str = "default"):
    """
    Register RAG tools with a LangGraph graph builder.
    
    Args:
        graph_builder: LangGraph StateGraph or similar.
        default_tenant: Default tenant ID.
    """
    rag_ask = create_rag_tool(default_tenant)
    rag_retrieve = create_rag_retrieve_tool(default_tenant)
    
    # Register tools
    # This depends on your LangGraph setup
    # Example:
    # graph_builder.add_tool("rag_ask", rag_ask)
    # graph_builder.add_tool("rag_retrieve", rag_retrieve)
    
    return {
        "rag_ask": rag_ask,
        "rag_retrieve": rag_retrieve
    }


# Tool descriptions for agent system prompt
RAG_TOOL_DESCRIPTIONS = """
## RAG Tools

You have access to the following tools for searching uploaded documents:

1. **rag_ask**: Search documents and generate an answer with citations
   - Use when user asks questions about their uploaded content
   - Returns: answer, citations, and source excerpts
   - Supports hybrid search (dense + sparse)

2. **rag_retrieve**: Search documents and return matching chunks
   - Use for simple content search without answer generation
   - Returns: ranked list of matching text chunks with scores

When to use RAG tools:
- User says: "based on my documents", "in the text I uploaded", "search my files"
- Questions about specific document content
- Requests to find information in uploaded materials

The system supports multi-tenant isolation, so each user's documents are separate.
"""
