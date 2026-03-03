#!/bin/bash
# RAG Demo Script - Shows key features

set -e

echo "================================================"
echo "RAG Pipeline Demo"
echo "================================================"
echo ""

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY environment variable not set"
    echo "Please run: export OPENAI_API_KEY='your-key-here'"
    exit 1
fi

TENANT="demo_user"

echo "Step 1: Ingesting sample documents..."
echo "--------------------------------------"
python -m rag.cli ingest \
  --tenant $TENANT \
  --path ./docs/authentication.txt \
  --chunk-size 1000 \
  --chunk-overlap 200

echo ""
echo "Step 2: Ingesting second document..."
echo "--------------------------------------"
python -m rag.cli ingest \
  --tenant $TENANT \
  --path ./docs/system_requirements.txt \
  --chunk-size 1000 \
  --chunk-overlap 200

echo ""
echo "Step 3: Listing ingested documents..."
echo "--------------------------------------"
python -m rag.cli list-docs --tenant $TENANT

echo ""
echo "Step 4: Hybrid retrieval (dense + sparse)..."
echo "--------------------------------------"
python -m rag.cli retrieve \
  --tenant $TENANT \
  --query "authentication token" \
  --mode hybrid \
  --top-k 3

echo ""
echo "Step 5: Comparing retrieval modes..."
echo "--------------------------------------"
echo "Dense only:"
python -m rag.cli retrieve \
  --tenant $TENANT \
  --query "system requirements" \
  --mode dense \
  --top-k 3

echo ""
echo "Sparse only:"
python -m rag.cli retrieve \
  --tenant $TENANT \
  --query "system requirements" \
  --mode sparse \
  --top-k 3

echo ""
echo "Step 6: RAG with reranking..."
echo "--------------------------------------"
python -m rag.cli retrieve \
  --tenant $TENANT \
  --query "authentication" \
  --mode hybrid \
  --rerank \
  --rerank-strategy llm \
  --top-k-candidates 10 \
  --top-k 3

echo ""
echo "Step 7: Asking questions with RAG..."
echo "--------------------------------------"
python -m rag.cli ask \
  --tenant $TENANT \
  --question "How does the authentication system work?" \
  --mode hybrid \
  --top-k 3

echo ""
python -m rag.cli ask \
  --tenant $TENANT \
  --question "What are the minimum hardware requirements?" \
  --mode hybrid \
  --top-k 3

echo ""
echo "Step 8: RAG with reranking for better precision..."
echo "--------------------------------------"
python -m rag.cli ask \
  --tenant $TENANT \
  --question "What security features are included?" \
  --mode hybrid \
  --rerank \
  --rerank-strategy llm \
  --top-k 3

echo ""
echo "================================================"
echo "Demo Complete!"
echo "================================================"
echo ""
echo "Key takeaways:"
echo "- Documents are chunked with overlap for better context"
echo "- Hybrid search combines dense (semantic) + sparse (keyword)"
echo "- Reranking improves precision using LLM scoring"
echo "- RAG answers include citations to sources"
echo "- Multi-tenant isolation keeps data separate per user"
echo ""
echo "Try your own queries:"
echo "  python -m rag.cli ask --tenant $TENANT --question 'Your question here'"
