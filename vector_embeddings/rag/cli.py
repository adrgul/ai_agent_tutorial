"""
CLI for RAG pipeline operations.

Provides commands for ingestion, retrieval, and question answering.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

from rag.rag_pipeline import RAGPipeline
from rag.config import RAGConfig


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def cmd_ingest(args):
    """Ingest a document."""
    pipeline = RAGPipeline(args.tenant, RAGConfig())
    
    if args.stdin:
        # Read from stdin
        print("Reading from stdin... (Ctrl+D to finish)")
        text = sys.stdin.read()
        
        result = pipeline.ingest_text(
            text=text,
            filename=args.name or "stdin.txt",
            source_path="stdin",
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap
        )
    else:
        # Read from file
        if not args.path:
            print("Error: --path is required unless --stdin is specified")
            return
        
        path = Path(args.path)
        
        if path.is_dir():
            # Ingest multiple files
            if args.recursive:
                pattern = args.glob or "*.txt"
                files = list(path.rglob(pattern))
            else:
                pattern = args.glob or "*.txt"
                files = list(path.glob(pattern))
            
            print(f"Found {len(files)} files to ingest")
            
            for file_path in files:
                print(f"\nIngesting: {file_path}")
                try:
                    result = pipeline.ingest_file(
                        str(file_path),
                        chunk_size=args.chunk_size,
                        chunk_overlap=args.chunk_overlap
                    )
                    print(f"✓ Success: doc_id={result['doc_id']}, chunks={result['chunk_count']}")
                except Exception as e:
                    print(f"✗ Failed: {e}")
            
            return
        else:
            # Single file
            result = pipeline.ingest_file(
                args.path,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap
            )
    
    print("\n=== Ingestion Complete ===")
    print(f"Document ID: {result['doc_id']}")
    print(f"Filename: {result['filename']}")
    print(f"Chunk count: {result['chunk_count']}")
    print(f"Status: {result['status']}")


def cmd_retrieve(args):
    """Retrieve relevant chunks."""
    pipeline = RAGPipeline(args.tenant, RAGConfig())
    
    result = pipeline.retrieve(
        query=args.query,
        top_k=args.top_k,
        mode=args.mode,
        rerank=args.rerank,
        rerank_strategy=args.rerank_strategy,
        top_k_candidates=args.top_k_candidates
    )
    
    print(f"\n=== Retrieval Results (mode: {args.mode}, rerank: {args.rerank}) ===")
    print(f"Query: {args.query}\n")
    
    # Show candidates before rerank if available
    if result.get("candidates_before_rerank"):
        print("--- Top 10 Candidates Before Rerank ---")
        for i, r in enumerate(result["candidates_before_rerank"][:10], 1):
            print(f"\n[{i}] Score: {r.score:.4f}")
            if r.dense_score is not None:
                print(f"    Dense: {r.dense_score:.4f}")
            if r.sparse_score is not None:
                print(f"    Sparse: {r.sparse_score:.4f}")
            print(f"    Source: {r.chunk.get_source_label()}")
            print(f"    Text: {r.chunk.text[:150]}...")
    
    # Show final results
    print(f"\n--- Final Top {args.top_k} Results ---")
    for i, r in enumerate(result["results"], 1):
        print(f"\n[{i}] Score: {r.score:.4f}")
        if r.dense_score is not None:
            print(f"    Dense: {r.dense_score:.4f}")
        if r.sparse_score is not None:
            print(f"    Sparse: {r.sparse_score:.4f}")
        if r.rerank_score is not None:
            print(f"    Rerank: {r.rerank_score:.4f}")
            if r.rerank_rationale:
                print(f"    Rationale: {r.rerank_rationale}")
        print(f"    Source: {r.chunk.get_source_label()}")
        print(f"    Text: {r.chunk.text[:200]}...")
    
    # Show rerank metadata
    if result.get("rerank_metadata"):
        meta = result["rerank_metadata"]
        print(f"\n--- Rerank Metadata ---")
        print(f"Strategy: {meta['strategy']}")
        print(f"Model: {meta.get('model', 'N/A')}")
        print(f"Beta (mixing weight): {meta['beta']}")
        print(f"Candidates: {meta['top_k_candidates']}")
        print(f"Final: {meta['top_k_final']}")


def cmd_ask(args):
    """Ask a question using RAG."""
    pipeline = RAGPipeline(args.tenant, RAGConfig())
    
    answer = pipeline.ask(
        question=args.question,
        top_k=args.top_k,
        mode=args.mode,
        rerank=args.rerank,
        rerank_strategy=args.rerank_strategy,
        top_k_candidates=args.top_k_candidates
    )
    
    print(f"\n=== RAG Answer (mode: {args.mode}, rerank: {args.rerank}) ===")
    print(f"Question: {args.question}\n")
    
    print("Answer:")
    print(answer.answer)
    
    print(f"\nCitations: {', '.join(answer.citations)}")
    
    print(f"\n--- Retrieved Chunks ({len(answer.retrieved_chunks)}) ---")
    for i, r in enumerate(answer.retrieved_chunks, 1):
        print(f"\n[{i}] {r.chunk.get_source_label()} (score: {r.score:.4f})")
        print(f"    {r.chunk.text[:200]}...")
    
    if answer.rerank_metadata:
        print(f"\n--- Rerank Info ---")
        print(f"Strategy: {answer.rerank_metadata.strategy}")
        print(f"Candidates: {answer.rerank_metadata.top_k_candidates} → Final: {answer.rerank_metadata.top_k_final}")


def cmd_list_docs(args):
    """List ingested documents."""
    pipeline = RAGPipeline(args.tenant, RAGConfig())
    
    docs = pipeline.list_documents()
    
    print(f"\n=== Ingested Documents (tenant: {args.tenant}) ===")
    print(f"Total: {len(docs)}\n")
    
    for doc in docs:
        print(f"Document ID: {doc['doc_id']}")
        print(f"  Filename: {doc['filename']}")
        print(f"  Source: {doc['source_path']}")
        print(f"  Ingested: {doc['ingested_at']}")
        print(f"  Size: {doc['size_chars']} chars")
        print(f"  Chunks: {doc.get('chunk_count', 0)}")
        print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG Pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a document")
    ingest_parser.add_argument("--tenant", required=True, help="Tenant ID")
    ingest_parser.add_argument("--path", help="Path to file or directory")
    ingest_parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    ingest_parser.add_argument("--name", help="Filename for stdin input")
    ingest_parser.add_argument("--recursive", action="store_true", help="Recursive directory scan")
    ingest_parser.add_argument("--glob", default="*.txt", help="Glob pattern for files")
    ingest_parser.add_argument("--chunk-size", type=int, help="Chunk size (chars)")
    ingest_parser.add_argument("--chunk-overlap", type=int, help="Chunk overlap (chars)")
    ingest_parser.set_defaults(func=cmd_ingest)
    
    # Retrieve command
    retrieve_parser = subparsers.add_parser("retrieve", help="Retrieve relevant chunks")
    retrieve_parser.add_argument("--tenant", required=True, help="Tenant ID")
    retrieve_parser.add_argument("--query", required=True, help="Search query")
    retrieve_parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    retrieve_parser.add_argument("--mode", choices=["dense", "sparse", "hybrid"], default="hybrid")
    retrieve_parser.add_argument("--rerank", action="store_true", help="Enable reranking")
    retrieve_parser.add_argument("--rerank-strategy", choices=["llm", "embed"], default="llm")
    retrieve_parser.add_argument("--top-k-candidates", type=int, help="Candidates for reranking")
    retrieve_parser.set_defaults(func=cmd_retrieve)
    
    # Ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question (RAG)")
    ask_parser.add_argument("--tenant", required=True, help="Tenant ID")
    ask_parser.add_argument("--question", required=True, help="Question to ask")
    ask_parser.add_argument("--top-k", type=int, default=5, help="Number of chunks for context")
    ask_parser.add_argument("--mode", choices=["dense", "sparse", "hybrid"], default="hybrid")
    ask_parser.add_argument("--rerank", action="store_true", help="Enable reranking")
    ask_parser.add_argument("--rerank-strategy", choices=["llm", "embed"], default="llm")
    ask_parser.add_argument("--top-k-candidates", type=int, help="Candidates for reranking")
    ask_parser.set_defaults(func=cmd_ask)
    
    # List docs command
    list_parser = subparsers.add_parser("list-docs", help="List ingested documents")
    list_parser.add_argument("--tenant", required=True, help="Tenant ID")
    list_parser.set_defaults(func=cmd_list_docs)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        args.func(args)
    except Exception as e:
        print(f"\nError: {e}")
        logging.exception("Command failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
