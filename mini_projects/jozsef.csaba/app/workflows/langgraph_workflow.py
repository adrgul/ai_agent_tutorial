"""LangGraph Workflow for Customer Service Triage.

Following SOLID principles:
- Single Responsibility: Orchestrates the workflow
- Dependency Inversion: Depends on service abstractions
- Open/Closed: Can add new nodes without modifying existing ones
"""

from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from langgraph.graph import StateGraph, END

from app.core.config import Settings
from app.models.schemas import (
    TicketInput,
    TicketResponse,
    WorkflowState,
)
from app.services.draft_generator import DraftGeneratorService
from app.services.embeddings import EmbeddingService
from app.services.intent_detection import IntentDetectionService
from app.services.policy_checker import PolicyCheckerService
from app.services.retrieval import RetrievalService
from app.services.triage import TriageService
from app.utils.vector_store import FAISSVectorStore


class TriageWorkflow:
    """LangGraph workflow for customer service triage."""

    def __init__(
        self,
        settings: Settings,
        vector_store: FAISSVectorStore,
        embedding_service: EmbeddingService,
    ):
        """Initialize workflow.

        Args:
            settings: Application settings
            vector_store: FAISS vector store
            embedding_service: Embedding service
        """
        self.settings = settings

        # Initialize services
        self.intent_service = IntentDetectionService(settings)
        self.triage_service = TriageService(settings)
        self.retrieval_service = RetrievalService(
            settings, vector_store, embedding_service
        )
        self.draft_service = DraftGeneratorService(settings)
        self.policy_service = PolicyCheckerService(settings)

        # Build graph
        self.workflow = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph state graph.

        Returns:
            Compiled state graph
        """
        # Create graph
        workflow = StateGraph(Dict[str, Any])

        # Add nodes
        workflow.add_node("intent_detection", self._intent_detection_node)
        workflow.add_node("triage", self._triage_node)
        workflow.add_node("query_expansion", self._query_expansion_node)
        workflow.add_node("retrieval", self._retrieval_node)
        workflow.add_node("reranking", self._reranking_node)
        workflow.add_node("draft_generation", self._draft_generation_node)
        workflow.add_node("policy_check", self._policy_check_node)

        # Define edges (workflow sequence)
        workflow.set_entry_point("intent_detection")
        workflow.add_edge("intent_detection", "triage")
        workflow.add_edge("triage", "query_expansion")
        workflow.add_edge("query_expansion", "retrieval")
        workflow.add_edge("retrieval", "reranking")
        workflow.add_edge("reranking", "draft_generation")
        workflow.add_edge("draft_generation", "policy_check")
        workflow.add_edge("policy_check", END)

        return workflow.compile()

    # Node implementations

    def _intent_detection_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Intent detection node.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        ticket = TicketInput(**state["ticket_input"])
        intent_result = self.intent_service.detect_intent_sync(ticket)

        return {
            **state,
            "intent_result": intent_result.model_dump(),
        }

    def _triage_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Triage classification node.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        from app.models.schemas import IntentDetectionResult

        ticket = TicketInput(**state["ticket_input"])
        intent_result = IntentDetectionResult(**state["intent_result"])

        triage_result = self.triage_service.classify_ticket_sync(
            ticket, intent_result
        )

        return {
            **state,
            "triage_result": triage_result.model_dump(),
        }

    def _query_expansion_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Query expansion node.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        from app.models.schemas import TriageResult

        ticket = TicketInput(**state["ticket_input"])
        triage_result = TriageResult(**state["triage_result"])

        queries = self.retrieval_service.expand_query_sync(ticket, triage_result)

        return {
            **state,
            "search_queries": queries,
        }

    def _retrieval_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Document retrieval node.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        queries = state["search_queries"]

        citations = self.retrieval_service.retrieve_documents_sync(queries)

        return {
            **state,
            "retrieved_docs": [c.model_dump() for c in citations],
        }

    def _reranking_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Document re-ranking node.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        from app.models.schemas import Citation, TriageResult

        ticket = TicketInput(**state["ticket_input"])
        triage_result = TriageResult(**state["triage_result"])
        citations = [Citation(**c) for c in state["retrieved_docs"]]

        reranked = self.retrieval_service.rerank_documents_sync(
            ticket, triage_result, citations
        )

        return {
            **state,
            "reranked_docs": [c.model_dump() for c in reranked],
        }

    def _draft_generation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Draft generation node.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        from app.models.schemas import Citation, TriageResult

        ticket = TicketInput(**state["ticket_input"])
        triage_result = TriageResult(**state["triage_result"])
        citations = [Citation(**c) for c in state["reranked_docs"]]

        draft = self.draft_service.generate_draft_sync(
            ticket, triage_result, citations
        )

        return {
            **state,
            "answer_draft": draft.model_dump(),
        }

    def _policy_check_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Policy check node.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        from app.models.schemas import AnswerDraft, TriageResult

        draft = AnswerDraft(**state["answer_draft"])
        triage_result = TriageResult(**state["triage_result"])

        policy_check = self.policy_service.check_policy_sync(draft, triage_result)

        # Generate ticket ID
        ticket_id = f"TKT-{datetime.utcnow().strftime('%Y-%m-%d')}-{uuid4().hex[:4]}"

        return {
            **state,
            "policy_check": policy_check.model_dump(),
            "ticket_id": ticket_id,
        }

    def process_ticket(self, ticket: TicketInput) -> TicketResponse:
        """Process a customer ticket through the workflow.

        Args:
            ticket: Customer ticket input

        Returns:
            Complete ticket response
        """
        # Initialize state
        initial_state = {
            "ticket_input": ticket.model_dump(),
        }

        # Run workflow
        final_state = self.workflow.invoke(initial_state)

        # Build response
        from app.models.schemas import (
            AnswerDraft,
            Citation,
            PolicyCheck,
            TriageResult,
        )

        response = TicketResponse(
            ticket_id=final_state["ticket_id"],
            timestamp=datetime.utcnow(),
            triage=TriageResult(**final_state["triage_result"]),
            answer_draft=AnswerDraft(**final_state["answer_draft"]),
            citations=[Citation(**c) for c in final_state["reranked_docs"]],
            policy_check=PolicyCheck(**final_state["policy_check"]),
        )

        return response
