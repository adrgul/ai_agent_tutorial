"""
RAG pipeline orchestration.

Provides complete ingestion, retrieval, and answer generation workflows.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

import requests

from rag.models import (
    Document, Chunk, RetrievalResult, RAGAnswer, RerankMetadata
)
from rag.config import (
    RAGConfig, ChunkingConfig, EmbeddingConfig,
    HybridConfig, RerankConfig, StorageConfig
)
from rag.chunking import OverlappingChunker
from rag.embeddings import EmbeddingService
from rag.vector_store import VectorStore
from rag.sparse_index import SparseIndex
from rag.hybrid_retriever import HybridRetriever
from rag.rerank import create_reranker


logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Complete RAG pipeline with ingestion, retrieval, and answer generation.
    
    Implements multi-tenant isolation and hybrid retrieval with optional reranking.
    """
    
    def __init__(self, tenant_id: str, config: RAGConfig = None):
        """
        Initialize RAG pipeline for a tenant.
        
        Args:
            tenant_id: Tenant ID for multi-tenancy.
            config: RAG configuration.
        """
        self.tenant_id = tenant_id
        self.config = config or RAGConfig()
        
        # Initialize components
        self.chunker = OverlappingChunker(self.config.chunking)
        self.embedding_service = EmbeddingService(self.config.embedding)
        self.vector_store = VectorStore(tenant_id, self.config.storage)
        self.sparse_index = SparseIndex(tenant_id, self.config.storage)
        self.retriever = HybridRetriever(
            tenant_id=tenant_id,
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
            sparse_index=self.sparse_index,
            config=self.config.hybrid,
            storage_config=self.config.storage
        )
    
    def ingest_file(
        self,
        file_path: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ingest a .txt file from filesystem.
        
        Args:
            file_path: Path to file to ingest.
            chunk_size: Optional chunk size override.
            chunk_overlap: Optional chunk overlap override.
        
        Returns:
            Dict with doc_id, chunk_count, and status.
        """
        # Validate path
        path = Path(file_path).resolve()
        
        if not self._is_path_allowed(str(path)):
            raise ValueError(f"Path not allowed: {file_path}")
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not path.is_file():
            raise ValueError(f"Not a file: {file_path}")
        
        # Read file content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            raise Exception(f"Failed to read file: {e}")
        
        # Ingest text
        return self.ingest_text(
            text=text,
            filename=path.name,
            source_path=str(path),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def ingest_text(
        self,
        text: str,
        filename: str,
        source_path: str = "",
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ingest raw text.
        
        Args:
            text: Text content to ingest.
            filename: Filename for metadata.
            source_path: Source path (optional).
            chunk_size: Optional chunk size override.
            chunk_overlap: Optional chunk overlap override.
        
        Returns:
            Dict with doc_id, chunk_count, and status.
        """
        logger.info(f"Ingesting document: {filename} (tenant: {self.tenant_id})")
        
        # Create document
        doc_id = Document.generate_id(self.tenant_id, filename)
        
        # Use override values if provided
        if chunk_size is not None:
            self.chunker.config.chunk_size = chunk_size
        if chunk_overlap is not None:
            self.chunker.config.chunk_overlap = chunk_overlap
        
        document = Document(
            doc_id=doc_id,
            tenant_id=self.tenant_id,
            filename=filename,
            source_path=source_path or filename,
            text=text,
            ingested_at=datetime.utcnow().isoformat(),
            size_chars=len(text),
            chunk_size=self.chunker.config.chunk_size,
            chunk_overlap=self.chunker.config.chunk_overlap,
            hash=Document.hash_text(text)
        )
        
        # Save raw document
        self._save_document(document)
        
        # Chunk the text
        chunks = self.chunker.chunk_document(document)
        document.chunk_count = len(chunks)
        
        logger.info(f"Created {len(chunks)} chunks")
        
        # Generate embeddings (batch)
        logger.info("Generating embeddings...")
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_service.get_embeddings_batch(chunk_texts)
        
        # Store in vector store (batch)
        logger.info("Storing in vector store...")
        self.vector_store.add_chunks_batch(chunks, embeddings)
        
        # Store in sparse index (batch)
        logger.info("Storing in sparse index...")
        self.sparse_index.add_chunks_batch(chunks)
        
        # Save chunk metadata
        self._save_chunks(document.doc_id, chunks)
        
        # Update document metadata with chunk count
        self._save_document(document)
        
        logger.info(f"Ingestion complete: {doc_id}")
        
        return {
            "doc_id": doc_id,
            "chunk_count": len(chunks),
            "filename": filename,
            "status": "success"
        }
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        mode: str = "hybrid",
        rerank: bool = False,
        rerank_strategy: str = "llm",
        top_k_candidates: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant chunks.
        
        Args:
            query: Query text.
            top_k: Number of final results.
            mode: Retrieval mode ("dense", "sparse", "hybrid").
            rerank: Whether to rerank results.
            rerank_strategy: Reranking strategy ("llm" or "embed").
            top_k_candidates: Number of candidates for reranking.
        
        Returns:
            Dict with retrieved chunks and metadata.
        """
        logger.info(f"Retrieving for query: {query} (mode: {mode}, rerank: {rerank})")
        
        if rerank:
            # Two-stage retrieval with reranking
            candidates_k = top_k_candidates or self.config.rerank.top_k_candidates
            
            # Stage 1: Retrieve candidates
            candidates = self.retriever.retrieve_candidates(
                query, candidates_k, mode
            )
            
            logger.info(f"Retrieved {len(candidates)} candidates")
            
            # Stage 2: Rerank
            reranker = create_reranker(
                rerank_strategy,
                self.embedding_service,
                self.config.rerank
            )
            
            logger.info(f"Reranking with {rerank_strategy} strategy...")
            results = reranker.rerank(query, candidates, top_k)
            
            # Keep top 10 candidates for comparison
            candidates_for_display = candidates[:min(10, len(candidates))]
            
            return {
                "results": results,
                "candidates_before_rerank": candidates_for_display,
                "rerank_metadata": {
                    "strategy": rerank_strategy,
                    "model": self.config.rerank.llm_model if rerank_strategy == "llm" else None,
                    "beta": self.config.rerank.beta,
                    "top_k_candidates": len(candidates),
                    "top_k_final": len(results)
                },
                "mode": mode
            }
        else:
            # Single-stage retrieval
            results = self.retriever.retrieve(query, top_k, mode)
            
            return {
                "results": results,
                "candidates_before_rerank": None,
                "rerank_metadata": None,
                "mode": mode
            }
    
    def ask(
        self,
        question: str,
        top_k: int = 5,
        mode: str = "hybrid",
        rerank: bool = False,
        rerank_strategy: str = "llm",
        top_k_candidates: Optional[int] = None
    ) -> RAGAnswer:
        """
        Answer a question using RAG.
        
        Args:
            question: Question to answer.
            top_k: Number of chunks to use for context.
            mode: Retrieval mode.
            rerank: Whether to rerank.
            rerank_strategy: Reranking strategy.
            top_k_candidates: Number of candidates for reranking.
        
        Returns:
            RAGAnswer object with answer and citations.
        """
        logger.info(f"Answering question: {question}")
        
        # Retrieve relevant chunks
        retrieval_result = self.retrieve(
            query=question,
            top_k=top_k,
            mode=mode,
            rerank=rerank,
            rerank_strategy=rerank_strategy,
            top_k_candidates=top_k_candidates
        )
        
        results = retrieval_result["results"]
        
        if not results:
            return RAGAnswer(
                answer="I don't have enough information to answer this question.",
                citations=[],
                retrieved_chunks=[],
                mode=mode,
                query=question
            )
        
        # Build context from retrieved chunks
        context_parts = []
        citations = []
        
        for i, result in enumerate(results):
            source_label = result.chunk.get_source_label()
            context_parts.append(
                f"[{i+1}] {result.chunk.text}\n(Source: {source_label})"
            )
            citations.append(source_label)
        
        context = "\n\n".join(context_parts)
        
        # Generate answer using OpenAI
        logger.info("Generating answer...")
        answer_text = self._generate_answer(question, context)
        
        # Build RAGAnswer
        rag_answer = RAGAnswer(
            answer=answer_text,
            citations=citations,
            retrieved_chunks=results,
            candidates_before_rerank=retrieval_result.get("candidates_before_rerank"),
            rerank_metadata=(
                RerankMetadata(**retrieval_result["rerank_metadata"])
                if retrieval_result.get("rerank_metadata") else None
            ),
            mode=mode,
            query=question
        )
        
        return rag_answer
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all ingested documents for this tenant.
        
        Returns:
            List of document metadata dicts.
        """
        docs_path = self.config.storage.get_docs_path(self.tenant_id)
        doc_files = list(docs_path.glob("*.json"))
        
        documents = []
        for doc_file in doc_files:
            try:
                with open(doc_file, 'r') as f:
                    doc_meta = json.load(f)
                    documents.append(doc_meta)
            except Exception as e:
                logger.error(f"Failed to read document metadata: {doc_file} - {e}")
        
        return documents
    
    def _save_document(self, document: Document) -> None:
        """Save document and its metadata."""
        docs_path = self.config.storage.get_docs_path(self.tenant_id)
        
        # Save raw text
        text_file = docs_path / f"{document.doc_id}__{document.filename}"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(document.text)
        
        # Save metadata
        meta_file = docs_path / f"{document.doc_id}.json"
        metadata = {
            "doc_id": document.doc_id,
            "tenant_id": document.tenant_id,
            "filename": document.filename,
            "source_path": document.source_path,
            "ingested_at": document.ingested_at,
            "size_chars": document.size_chars,
            "chunk_size": document.chunk_size,
            "chunk_overlap": document.chunk_overlap,
            "hash": document.hash,
            "chunk_count": document.chunk_count
        }
        
        with open(meta_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _save_chunks(self, doc_id: str, chunks: List[Chunk]) -> None:
        """Save chunk metadata."""
        chunks_path = self.config.storage.get_chunks_path(self.tenant_id)
        
        chunk_data = []
        for chunk in chunks:
            chunk_data.append({
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "tenant_id": chunk.tenant_id,
                "chunk_index": chunk.chunk_index,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "checksum": chunk.checksum,
                "metadata": chunk.metadata,
                "source_label": chunk.get_source_label()
            })
        
        chunks_file = chunks_path / f"{doc_id}.json"
        with open(chunks_file, 'w') as f:
            json.dump(chunk_data, f, indent=2)
    
    def _generate_answer(self, question: str, context: str) -> str:
        """
        Generate answer using OpenAI chat model.
        
        Args:
            question: User question.
            context: Context from retrieved chunks.
        
        Returns:
            Generated answer.
        """
        system_prompt = """You are a helpful assistant that answers questions based on provided context.
Use ONLY the information in the context to answer. If the context doesn't contain enough information, say so.
Include citation numbers [1], [2], etc. in your answer to reference the sources."""
        
        user_prompt = f"""Context:
{context}

Question: {question}

Answer based on the context above:"""
        
        headers = {
            "Authorization": f"Bearer {self.config.embedding.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            return answer
        
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            return f"Error generating answer: {e}"
    
    def _is_path_allowed(self, path: str) -> bool:
        """
        Check if a path is within allowed ingestion roots.
        
        Args:
            path: Absolute path to check.
        
        Returns:
            True if allowed, False otherwise.
        """
        path = Path(path).resolve()
        
        for allowed_root in self.config.storage.allowed_ingest_roots:
            allowed_path = Path(allowed_root).resolve()
            try:
                path.relative_to(allowed_path)
                return True
            except ValueError:
                continue
        
        return False
