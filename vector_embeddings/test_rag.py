"""
Quick verification test for RAG pipeline.
Run this to ensure all components work together.
"""

import os
import sys
from pathlib import Path

# Ensure we can import rag module
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.config import RAGConfig
from rag.rag_pipeline import RAGPipeline


def test_basic_rag():
    """Test basic RAG functionality."""
    print("Testing RAG Pipeline...")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return False
    
    print("✓ API key found")
    
    # Initialize pipeline
    tenant_id = "test_tenant"
    config = RAGConfig()
    pipeline = RAGPipeline(tenant_id, config)
    
    print(f"✓ Pipeline initialized for tenant: {tenant_id}")
    
    # Test text ingestion
    test_text = """
    This is a test document about artificial intelligence.
    Machine learning is a subset of AI that focuses on learning from data.
    Neural networks are inspired by biological neurons in the brain.
    Deep learning uses multiple layers to extract higher-level features.
    """
    
    print("\nIngesting test document...")
    result = pipeline.ingest_text(
        text=test_text,
        filename="test_doc.txt",
        source_path="test",
        chunk_size=100,
        chunk_overlap=20
    )
    
    print(f"✓ Ingested: doc_id={result['doc_id']}, chunks={result['chunk_count']}")
    
    # Test retrieval (dense only to save API calls)
    print("\nTesting retrieval...")
    retrieval_result = pipeline.retrieve(
        query="machine learning",
        top_k=2,
        mode="dense",
        rerank=False
    )
    
    print(f"✓ Retrieved {len(retrieval_result['results'])} results")
    
    if retrieval_result['results']:
        top_result = retrieval_result['results'][0]
        print(f"  Top result score: {top_result.score:.4f}")
        print(f"  Text preview: {top_result.chunk.text[:80]}...")
    
    # Test RAG answer (this will make an API call to OpenAI chat)
    print("\nTesting RAG answer generation...")
    answer = pipeline.ask(
        question="What is machine learning?",
        top_k=2,
        mode="dense",
        rerank=False
    )
    
    print(f"✓ Generated answer ({len(answer.answer)} chars)")
    print(f"  Citations: {', '.join(answer.citations)}")
    print(f"  Answer preview: {answer.answer[:150]}...")
    
    # Test document listing
    print("\nTesting document listing...")
    docs = pipeline.list_documents()
    print(f"✓ Found {len(docs)} documents")
    
    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print("\nNext steps:")
    print("1. Try the demo script: ./rag_demo.sh")
    print("2. Ingest real documents from ./docs/")
    print("3. Experiment with different retrieval modes")
    
    return True


if __name__ == "__main__":
    try:
        success = test_basic_rag()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
