"""LangGraph workflow for RAG-based chat with query rewriting and context retrieval."""

import logging
from typing import TypedDict, List, Dict, Any

from langgraph.graph import StateGraph, END

from app.models import ChatMessage
from app.config import TOP_K, MAX_CONTEXT_CHARS

logger = logging.getLogger(__name__)


class ChatState(TypedDict, total=False):
    """State for the chat workflow."""
    tenant: str
    user_id: str
    messages: List[ChatMessage]
    latest_user_message: str
    rewritten_query: str
    relevant_chunks: List[Dict[str, Any]]
    document_ids: List[str]
    answer: str


def cleaning_node(llm_service) -> callable:
    """
    Create cleaning node that extracts and rewrites the user query.
    
    Args:
        llm_service: LLMService instance
        
    Returns:
        Node function
    """
    async def node(state: ChatState) -> ChatState:
        """
        Extract the latest user message and rewrite it for better search.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with rewritten_query
        """
        logger.info("Cleaning and rewriting user query")
        
        messages = state.get("messages", [])
        
        if not messages:
            logger.warning("No messages in state")
            return {**state, "rewritten_query": ""}
        
        # Extract latest user message
        latest_user_message = ""
        for msg in reversed(messages):
            if msg.role == "user":
                latest_user_message = msg.content
                break
        
        if not latest_user_message:
            logger.warning("No user message found")
            return {**state, "rewritten_query": ""}
        
        # Rewrite query using LLM
        system_prompt = (
            "You are a professional company assistant. "
            "Rewrite the user query clearly and concisely, preserving the original meaning. "
            "Output only the rewritten query."
        )
        
        try:
            rewritten_query = await llm_service.generate(
                system_prompt=system_prompt,
                user_prompt=latest_user_message
            )
            rewritten_query = rewritten_query.strip()
        except Exception as e:
            logger.error(f"Failed to rewrite query: {e}")
            # Fallback to original query
            rewritten_query = latest_user_message
        
        logger.info(f"Rewritten query: {rewritten_query[:100]}...")
        
        return {
            **state,
            "latest_user_message": latest_user_message,
            "rewritten_query": rewritten_query
        }
    
    return node


def search_node(
    embedding_service,
    qdrant_service,
    top_k: int = TOP_K
) -> callable:
    """
    Create search node that retrieves relevant chunks from Qdrant.
    
    Args:
        embedding_service: EmbeddingService instance
        qdrant_service: QdrantService instance
        top_k: Number of chunks to retrieve
        
    Returns:
        Node function
    """
    def node(state: ChatState) -> ChatState:
        """
        Search for relevant chunks using the rewritten query.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with relevant_chunks and document_ids
        """
        logger.info("Searching for relevant chunks")
        
        rewritten_query = state.get("rewritten_query", "")
        tenant = state.get("tenant", "")
        
        if not rewritten_query:
            logger.warning("No rewritten query to search")
            return {
                **state,
                "relevant_chunks": [],
                "document_ids": []
            }
        
        # Generate embedding for query
        query_embedding = embedding_service.get_embedding(rewritten_query)
        
        # Search Qdrant
        search_results = qdrant_service.search(
            tenant=tenant,
            query_vector=query_embedding,
            top_k=top_k
        )
        
        # Extract unique document IDs
        document_ids = list(set(chunk["document_id"] for chunk in search_results))
        
        logger.info(f"Found {len(search_results)} chunks from {len(document_ids)} documents")
        
        return {
            **state,
            "relevant_chunks": search_results,
            "document_ids": document_ids
        }
    
    return node


def answer_node(
    llm_service,
    max_context_chars: int = MAX_CONTEXT_CHARS
) -> callable:
    """
    Create answer node that generates response based on context.
    
    Args:
        llm_service: LLMService instance
        max_context_chars: Maximum characters to include in context
        
    Returns:
        Node function
    """
    async def node(state: ChatState) -> ChatState:
        """
        Generate answer using LLM based on retrieved chunks.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with answer
        """
        logger.info("Generating answer")
        
        relevant_chunks = state.get("relevant_chunks", [])
        latest_user_message = state.get("latest_user_message", "")
        rewritten_query = state.get("rewritten_query", "")
        
        # Build context from chunks
        context_parts = []
        context_length = 0
        
        for i, chunk in enumerate(relevant_chunks):
            chunk_text = chunk.get("text", "")
            chunk_length = len(chunk_text)
            
            if context_length + chunk_length > max_context_chars:
                logger.info(f"Reached max context chars, using {i} chunks")
                break
            
            context_parts.append(f"[Chunk {i+1}] {chunk_text}")
            context_length += chunk_length
        
        if not context_parts:
            # No context available
            system_prompt = (
                "You are a professional company assistant. "
                "Answer the user's question. If you do not have enough information, "
                "say you do not have enough information to answer."
            )
            user_prompt = latest_user_message or rewritten_query
        else:
            # Build prompt with context
            context = "\n\n".join(context_parts)
            
            system_prompt = (
                "You are a professional company assistant. "
                "Answer strictly based on the provided context chunks. "
                "If the answer is not in the context, say you do not have enough information."
            )
            
            user_prompt = f"""Context:
{context}

Question: {latest_user_message or rewritten_query}

Provide a concise answer based only on the context above."""
        
        try:
            answer = await llm_service.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            answer = answer.strip()
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            answer = "I apologize, but I encountered an error generating the response."
        
        logger.info(f"Generated answer: {answer[:100]}...")
        
        return {
            **state,
            "answer": answer
        }
    
    return node


def create_chat_graph(
    llm_service,
    embedding_service,
    qdrant_service,
    top_k: int = TOP_K,
    max_context_chars: int = MAX_CONTEXT_CHARS
) -> StateGraph:
    """
    Create the LangGraph workflow for RAG-based chat.
    
    Args:
        llm_service: LLMService instance
        embedding_service: EmbeddingService instance
        qdrant_service: QdrantService instance
        top_k: Number of chunks to retrieve
        max_context_chars: Maximum context size
        
    Returns:
        Compiled StateGraph
    """
    # Create graph
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("cleaning", cleaning_node(llm_service))
    workflow.add_node("search", search_node(embedding_service, qdrant_service, top_k))
    workflow.add_node("answer", answer_node(llm_service, max_context_chars))
    
    # Add edges
    workflow.add_edge("cleaning", "search")
    workflow.add_edge("search", "answer")
    workflow.add_edge("answer", END)
    
    # Set entry point
    workflow.set_entry_point("cleaning")
    
    # Compile
    return workflow.compile()
