"""
RAG subgraph for LangGraph.

Creates a compiled subgraph that can be invoked as a node in the main agent graph.

Flow: QueryRewrite → Retrieve → ContextBuilder → Guardrail → Feedback → END
"""

import logging
from langgraph.graph import StateGraph, END
from typing import Dict, Any

from .rag_nodes import (
    query_rewrite_node,
    retrieve_node,
    context_builder_node,
    guardrail_node,
    feedback_node,
    set_rag_dependencies
)

logger = logging.getLogger(__name__)


def create_rag_subgraph(retrieval_service, rag_config, llm):
    """
    Create compiled RAG subgraph.

    Args:
        retrieval_service: RetrievalService instance
        rag_config: RAGConfig instance
        llm: ChatOpenAI instance for query rewriting

    Returns:
        Compiled LangGraph that can be used as a node
    """
    # Set dependencies for nodes
    set_rag_dependencies(retrieval_service, rag_config, llm)

    # Create state graph
    # Note: We use Dict[str, Any] as state type since AgentState will be provided by main graph
    workflow = StateGraph(Dict[str, Any])

    # Add nodes
    workflow.add_node("query_rewrite", query_rewrite_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("context_builder", context_builder_node)
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("feedback", feedback_node)

    # Define edges (linear pipeline)
    workflow.set_entry_point("query_rewrite")
    workflow.add_edge("query_rewrite", "retrieve")
    workflow.add_edge("retrieve", "context_builder")
    workflow.add_edge("context_builder", "guardrail")
    workflow.add_edge("guardrail", "feedback")
    workflow.add_edge("feedback", END)

    # Compile graph
    compiled_graph = workflow.compile()

    logger.info("RAG subgraph compiled successfully")

    return compiled_graph
