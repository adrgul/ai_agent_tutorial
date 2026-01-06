"""LangGraph workflow for document storage with chunking and embedding."""

import logging
import re
from typing import TypedDict, List, Dict, Any

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


class StoreState(TypedDict, total=False):
    """State for the document storage workflow."""
    tenant: str
    document_id: str
    ocr_text: str
    cleaned_text: str
    chunks: List[Dict[str, Any]]
    chunks_count: int
    response: Dict[str, Any]


def cleaning_node(state: StoreState) -> StoreState:
    """
    Clean OCR text by removing artifacts and normalizing whitespace.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with cleaned_text
    """
    logger.info("Cleaning OCR text")
    
    ocr_text = state.get("ocr_text", "")
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', ocr_text)
    
    # Remove common OCR artifacts
    cleaned = re.sub(r'[^\w\s\.,!?;:\-()"\'\n]', '', cleaned)
    
    # Normalize line breaks
    cleaned = re.sub(r'\n+', '\n', cleaned)
    
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    logger.info(f"Cleaned text length: {len(cleaned)} chars")
    
    return {
        **state,
        "cleaned_text": cleaned
    }


def chunk_node(state: StoreState) -> StoreState:
    """
    Split cleaned text into chunks with sentence-based splitting.
    Max ~600 tokens per chunk (~2400 chars approximation).
    One-sentence overlap between chunks.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with chunks
    """
    logger.info("Chunking text")
    
    cleaned_text = state.get("cleaned_text", "")
    tenant = state.get("tenant", "")
    document_id = state.get("document_id", "")
    
    if not cleaned_text:
        logger.warning("No cleaned text to chunk")
        return {**state, "chunks": []}
    
    # Simple sentence splitting
    sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)
    
    if not sentences:
        return {**state, "chunks": []}
    
    chunks = []
    current_chunk = []
    current_length = 0
    max_chars = 2400  # Approximation of ~600 tokens
    
    previous_sentence = None
    
    for sentence in sentences:
        sentence_length = len(sentence)
        
        # If adding this sentence would exceed the limit
        if current_length + sentence_length > max_chars and current_chunk:
            # Save current chunk
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                "tenant": tenant,
                "document_id": document_id,
                "text": chunk_text,
                "chunk_index": len(chunks)
            })
            
            # Start new chunk with overlap (previous sentence)
            if previous_sentence:
                current_chunk = [previous_sentence, sentence]
                current_length = len(previous_sentence) + sentence_length
            else:
                current_chunk = [sentence]
                current_length = sentence_length
        else:
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_length += sentence_length
        
        previous_sentence = sentence
    
    # Add the last chunk if not empty
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        chunks.append({
            "tenant": tenant,
            "document_id": document_id,
            "text": chunk_text,
            "chunk_index": len(chunks)
        })
    
    logger.info(f"Created {len(chunks)} chunks")
    
    return {
        **state,
        "chunks": chunks
    }


def embedding_node(
    embedding_service,
    qdrant_service
) -> callable:
    """
    Create embedding node that computes embeddings and stores in Qdrant.
    
    Args:
        embedding_service: EmbeddingService instance
        qdrant_service: QdrantService instance
        
    Returns:
        Node function
    """
    def node(state: StoreState) -> StoreState:
        """
        Compute embeddings for chunks and upsert to Qdrant.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with chunks_count
        """
        logger.info("Computing embeddings and storing in Qdrant")
        
        chunks = state.get("chunks", [])
        tenant = state.get("tenant", "")
        document_id = state.get("document_id", "")
        
        if not chunks:
            logger.warning("No chunks to embed")
            return {**state, "chunks_count": 0}
        
        # Extract texts
        texts = [chunk["text"] for chunk in chunks]
        
        # Compute embeddings
        embeddings = embedding_service.get_embeddings(texts)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
        
        # Store in Qdrant
        chunks_count = qdrant_service.upsert_chunks(
            tenant=tenant,
            document_id=document_id,
            chunks=chunks
        )
        
        logger.info(f"Stored {chunks_count} chunks")
        
        return {
            **state,
            "chunks_count": chunks_count
        }
    
    return node


def response_node(state: StoreState) -> StoreState:
    """
    Build final response.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with response
    """
    logger.info("Building response")
    
    chunks_count = state.get("chunks_count", 0)
    
    response = {
        "success": "ok",
        "chunks_count": chunks_count
    }
    
    return {
        **state,
        "response": response
    }


def create_store_graph(embedding_service, qdrant_service) -> StateGraph:
    """
    Create the LangGraph workflow for document storage.
    
    Args:
        embedding_service: EmbeddingService instance
        qdrant_service: QdrantService instance
        
    Returns:
        Compiled StateGraph
    """
    # Create graph
    workflow = StateGraph(StoreState)
    
    # Add nodes
    workflow.add_node("cleaning", cleaning_node)
    workflow.add_node("chunk", chunk_node)
    workflow.add_node("embedding", embedding_node(embedding_service, qdrant_service))
    workflow.add_node("response", response_node)
    
    # Add edges
    workflow.add_edge("cleaning", "chunk")
    workflow.add_edge("chunk", "embedding")
    workflow.add_edge("embedding", "response")
    workflow.add_edge("response", END)
    
    # Set entry point
    workflow.set_entry_point("cleaning")
    
    # Compile
    return workflow.compile()
