"""RAG Retrieval Service with query expansion and re-ranking.

Following SOLID principles:
- Single Responsibility: Handles knowledge retrieval
- Dependency Inversion: Depends on abstractions (vector store, embeddings)
"""

from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.models.schemas import Citation, TicketInput, TriageResult
from app.services.embeddings import EmbeddingService
from app.utils.vector_store import FAISSVectorStore


class RetrievalService:
    """Service for RAG-based knowledge retrieval."""

    def __init__(
        self,
        settings: Settings,
        vector_store: FAISSVectorStore,
        embedding_service: EmbeddingService,
    ):
        """Initialize retrieval service.

        Args:
            settings: Application settings
            vector_store: FAISS vector store instance
            embedding_service: Embedding service instance
        """
        self.settings = settings
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.temperature,
            openai_api_key=settings.openai_api_key,
        )

        # Query expansion prompt
        self.expansion_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a search query expert. Given a customer service ticket, generate 2-3 diverse search queries to find relevant knowledge base articles.

Consider:
- Different phrasings of the problem
- Related issues
- Underlying causes
- Solution-oriented queries

Return ONLY a valid JSON object:
{{
    "queries": ["query 1", "query 2", "query 3"]
}}"""),
            ("user", """Ticket:
Subject: {subject}
Message: {message}
Category: {category}

Generate search queries as JSON.""")
        ])

        # Re-ranking prompt
        self.rerank_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a relevance ranking expert. Given a customer ticket and retrieved KB articles, rank them by relevance.

Score each article from 0.0 to 1.0 based on:
- Direct relevance to the problem
- Solution applicability
- Information completeness

Return ONLY a valid JSON object:
{{
    "rankings": [
        {{"doc_id": "KB-1234", "score": 0.95}},
        {{"doc_id": "KB-5678", "score": 0.87}}
    ]
}}"""),
            ("user", """Ticket:
Subject: {subject}
Message: {message}
Category: {category}

Retrieved Articles:
{articles}

Rank articles by relevance as JSON.""")
        ])

        self.parser = JsonOutputParser()

    async def expand_query(
        self,
        ticket: TicketInput,
        triage_result: TriageResult,
    ) -> List[str]:
        """Expand query into multiple search queries.

        Args:
            ticket: Customer ticket
            triage_result: Triage classification

        Returns:
            List of expanded queries
        """
        chain = self.expansion_prompt | self.llm | self.parser

        result = await chain.ainvoke({
            "subject": ticket.subject,
            "message": ticket.message,
            "category": triage_result.category,
        })

        return result.get("queries", [ticket.message])

    def expand_query_sync(
        self,
        ticket: TicketInput,
        triage_result: TriageResult,
    ) -> List[str]:
        """Synchronous version of query expansion.

        Args:
            ticket: Customer ticket
            triage_result: Triage classification

        Returns:
            List of expanded queries
        """
        chain = self.expansion_prompt | self.llm | self.parser

        result = chain.invoke({
            "subject": ticket.subject,
            "message": ticket.message,
            "category": triage_result.category,
        })

        return result.get("queries", [ticket.message])

    async def retrieve_documents(
        self,
        queries: List[str],
        top_k: int = None,
    ) -> List[Citation]:
        """Retrieve documents using vector search.

        Args:
            queries: List of search queries
            top_k: Number of documents to retrieve per query

        Returns:
            List of citations
        """
        if top_k is None:
            top_k = self.settings.top_k_retrieval

        all_citations = []
        seen_doc_ids = set()

        for query in queries:
            # Embed query
            query_embedding = self.embedding_service.embed_text(query)

            # Search vector store
            citations = self.vector_store.search(query_embedding, top_k=top_k)

            # Deduplicate
            for citation in citations:
                if citation.doc_id not in seen_doc_ids:
                    all_citations.append(citation)
                    seen_doc_ids.add(citation.doc_id)

        return all_citations

    def retrieve_documents_sync(
        self,
        queries: List[str],
        top_k: int = None,
    ) -> List[Citation]:
        """Synchronous version of document retrieval.

        Args:
            queries: List of search queries
            top_k: Number of documents to retrieve per query

        Returns:
            List of citations
        """
        if top_k is None:
            top_k = self.settings.top_k_retrieval

        all_citations = []
        seen_doc_ids = set()

        for query in queries:
            # Embed query
            query_embedding = self.embedding_service.embed_text(query)

            # Search vector store
            citations = self.vector_store.search(query_embedding, top_k=top_k)

            # Deduplicate
            for citation in citations:
                if citation.doc_id not in seen_doc_ids:
                    all_citations.append(citation)
                    seen_doc_ids.add(citation.doc_id)

        return all_citations

    async def rerank_documents(
        self,
        ticket: TicketInput,
        triage_result: TriageResult,
        citations: List[Citation],
        top_k: int = None,
    ) -> List[Citation]:
        """Re-rank documents using LLM.

        Args:
            ticket: Customer ticket
            triage_result: Triage classification
            citations: Retrieved citations
            top_k: Number of top documents to return

        Returns:
            Re-ranked citations
        """
        if not citations:
            return []

        if top_k is None:
            top_k = self.settings.top_k_rerank

        # Format articles for prompt
        articles_text = "\n\n".join([
            f"[{c.doc_id}] {c.title}\n{c.content[:300]}..."
            for c in citations
        ])

        chain = self.rerank_prompt | self.llm | self.parser

        result = await chain.ainvoke({
            "subject": ticket.subject,
            "message": ticket.message,
            "category": triage_result.category,
            "articles": articles_text,
        })

        # Create score mapping
        score_map = {
            item["doc_id"]: item["score"]
            for item in result.get("rankings", [])
        }

        # Update citation scores and sort
        for citation in citations:
            if citation.doc_id in score_map:
                citation.score = score_map[citation.doc_id]

        # Sort by score and return top k
        citations.sort(key=lambda x: x.score, reverse=True)
        return citations[:top_k]

    def rerank_documents_sync(
        self,
        ticket: TicketInput,
        triage_result: TriageResult,
        citations: List[Citation],
        top_k: int = None,
    ) -> List[Citation]:
        """Synchronous version of document re-ranking.

        Args:
            ticket: Customer ticket
            triage_result: Triage classification
            citations: Retrieved citations
            top_k: Number of top documents to return

        Returns:
            Re-ranked citations
        """
        if not citations:
            return []

        if top_k is None:
            top_k = self.settings.top_k_rerank

        # Format articles for prompt
        articles_text = "\n\n".join([
            f"[{c.doc_id}] {c.title}\n{c.content[:300]}..."
            for c in citations
        ])

        chain = self.rerank_prompt | self.llm | self.parser

        result = chain.invoke({
            "subject": ticket.subject,
            "message": ticket.message,
            "category": triage_result.category,
            "articles": articles_text,
        })

        # Create score mapping
        score_map = {
            item["doc_id"]: item["score"]
            for item in result.get("rankings", [])
        }

        # Update citation scores and sort
        for citation in citations:
            if citation.doc_id in score_map:
                citation.score = score_map[citation.doc_id]

        # Sort by score and return top k
        citations.sort(key=lambda x: x.score, reverse=True)
        return citations[:top_k]
