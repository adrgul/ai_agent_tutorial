"""
RAG Recall Node - On-demand retrieval from RAG store.

For "hybrid" memory mode when user references past information.
Uses similarity search with relevance threshold.
Injects retrieved context into retrieved_context channel.
"""
import os
from typing import Dict, Any, List
from datetime import datetime
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from ..state import AppState, RetrievedContext, TraceEntry


# Initialize embeddings and vector store
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY")
)

# Use existing RAG vector store
vector_store = Chroma(
    collection_name="teaching_memory_docs",
    embedding_function=embeddings,
    persist_directory="data/rag/chroma"
)


async def rag_recall_node(state: AppState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant context from RAG store.
    
    Args:
        state: Current AppState
        config: Configuration (includes relevance_threshold)
    
    Returns:
        Update to retrieved_context channel with relevant docs
    """
    relevance_threshold = config.get("configurable", {}).get("relevance_threshold", 0.7)
    
    # Get last user message as query
    user_messages = [msg for msg in state.messages if msg.role == "user"]
    if not user_messages:
        return {"trace": [TraceEntry(step="rag_recall", action="skip", details="No user message")]}
    
    query = user_messages[-1].content
    
    try:
        # Perform similarity search
        results = vector_store.similarity_search_with_score(query, k=3)
        
        # Filter by relevance threshold
        relevant_results = [
            (doc, score)
            for doc, score in results
            if score >= relevance_threshold
        ]
        
        if not relevant_results:
            trace_entry = TraceEntry(
                step="rag_recall",
                action="no_relevant_docs",
                details=f"Threshold: {relevance_threshold}"
            )
            return {"trace": [trace_entry]}
        
        # Create retrieved context
        retrieved_docs = []
        for doc, score in relevant_results:
            retrieved_docs.append({
                "content": doc.page_content,
                "score": float(score),
                "metadata": doc.metadata
            })
        
        retrieved_context = RetrievedContext(
            query=query,
            documents=retrieved_docs,
            timestamp=datetime.now()
        )
        
        # Add trace entry
        trace_entry = TraceEntry(
            step="rag_recall",
            action="retrieved_docs",
            details=f"Found {len(retrieved_docs)} relevant documents"
        )
        
        return {
            "retrieved_context": retrieved_context,
            "trace": [trace_entry]
        }
        
    except Exception as e:
        print(f"Error retrieving from RAG: {e}")
        trace_entry = TraceEntry(
            step="rag_recall",
            action="error",
            details=f"Failed: {str(e)}"
        )
        return {"trace": [trace_entry]}
