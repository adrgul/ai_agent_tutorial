# RAG Pipeline Module

Complete Retrieval-Augmented Generation (RAG) implementation with multi-tenant support, hybrid search, and reranking.

## Features

- ✅ **Document Ingestion**: Path-based ingestion from filesystem
- ✅ **Overlapping Chunking**: Configurable chunk size and overlap for better context preservation
- ✅ **Multi-Tenant Isolation**: Complete tenant separation for data and indexes
- ✅ **Dense Retrieval**: Vector similarity search using OpenAI embeddings + ChromaDB
- ✅ **Sparse Retrieval**: BM25 lexical search using SQLite FTS5
- ✅ **Hybrid Search**: Weighted combination of dense and sparse scores
- ✅ **Two-Stage Reranking**: LLM-based or embedding-based reranking
- ✅ **RAG Answer Generation**: Context-aware answers with citations
- ✅ **Persistent Storage**: All data persists on disk
- ✅ **LangGraph Integration**: Ready-to-use tools for agent workflows

## Architecture

```
rag/
├── __init__.py              # Module initialization
├── config.py                # Configuration dataclasses
├── models.py                # Data models (Chunk, Document, etc.)
├── chunking.py              # Overlapping text chunker
├── embeddings.py            # OpenAI embedding service
├── vector_store.py          # ChromaDB vector store (dense)
├── sparse_index.py          # SQLite FTS5 sparse index (BM25)
├── hybrid_retriever.py      # Hybrid retrieval combiner
├── rerank.py                # Reranking strategies (LLM + embedding)
├── rag_pipeline.py          # Main pipeline orchestration
├── cli.py                   # Command-line interface
└── langgraph_tool.py        # LangGraph tool integration
```

## Quick Start

### 1. Environment Setup

Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-key-here"
```

### 2. Ingest Documents

Ingest a single file:
```bash
python -m rag.cli ingest \
  --tenant user123 \
  --path ./docs/manual.txt \
  --chunk-size 1000 \
  --chunk-overlap 200
```

Ingest multiple files:
```bash
python -m rag.cli ingest \
  --tenant user123 \
  --path ./docs \
  --recursive \
  --glob "*.txt"
```

Ingest from stdin:
```bash
cat document.txt | python -m rag.cli ingest \
  --tenant user123 \
  --stdin \
  --name document.txt
```

### 3. Retrieve Documents

Search with hybrid retrieval:
```bash
python -m rag.cli retrieve \
  --tenant user123 \
  --query "How does the authentication work?" \
  --top-k 5 \
  --mode hybrid
```

Search with reranking:
```bash
python -m rag.cli retrieve \
  --tenant user123 \
  --query "How does the authentication work?" \
  --mode hybrid \
  --rerank \
  --rerank-strategy llm \
  --top-k-candidates 30 \
  --top-k 5
```

### 4. Ask Questions (RAG)

Generate an answer with citations:
```bash
python -m rag.cli ask \
  --tenant user123 \
  --question "How does the authentication work?" \
  --top-k 5 \
  --mode hybrid
```

With reranking:
```bash
python -m rag.cli ask \
  --tenant user123 \
  --question "What are the system requirements?" \
  --mode hybrid \
  --rerank \
  --rerank-strategy llm
```

### 5. List Documents

```bash
python -m rag.cli list-docs --tenant user123
```

## Docker Usage

Build and run:
```bash
docker-compose up --build
```

Run CLI inside container:
```bash
docker exec -it embedding-demo python -m rag.cli ingest \
  --tenant default \
  --path /app/docs/sample.txt

docker exec -it embedding-demo python -m rag.cli ask \
  --tenant default \
  --question "Your question here"
```

## Configuration

Default configuration in [config.py](config.py):

```python
# Chunking
chunk_size: 1000        # characters
chunk_overlap: 200      # characters

# Hybrid retrieval
alpha: 0.7              # weight for dense (0.3 for sparse)

# Reranking
beta: 0.3               # weight for initial score (0.7 for rerank)
top_k_candidates: 30    # candidates to rerank
top_k_final: 5          # final results after rerank
```

## Retrieval Modes

### Dense (Vector Similarity)
Uses OpenAI embeddings and ChromaDB for semantic similarity:
```bash
--mode dense
```

### Sparse (BM25 Lexical)
Uses SQLite FTS5 for keyword-based search:
```bash
--mode sparse
```

### Hybrid (Recommended)
Combines dense and sparse with weighted scoring:
```bash
--mode hybrid  # alpha * dense + (1-alpha) * sparse
```

## Reranking

Two-stage retrieval improves precision:

**Stage 1**: Retrieve top-k candidates (e.g., 30)  
**Stage 2**: Rerank and select final top-k (e.g., 5)

### LLM-based Reranking
Uses OpenAI GPT model to score relevance:
```bash
--rerank --rerank-strategy llm
```

**Pros**: Highly accurate, understands semantic nuances  
**Cons**: More expensive, slower

### Embedding-based Reranking
Uses cosine similarity with query embedding:
```bash
--rerank --rerank-strategy embed
```

**Pros**: Fast, cheap  
**Cons**: Less accurate than LLM

## Multi-Tenancy

Complete isolation per tenant:

- **Vector store**: Separate ChromaDB collection per tenant
- **Sparse index**: Separate SQLite database per tenant
- **Document storage**: Separate directory per tenant
- **No cross-tenant leakage**: Queries only search within tenant scope

Example:
```bash
# User A's documents
python -m rag.cli ingest --tenant user_a --path ./docs/user_a_data.txt

# User B's documents (completely separate)
python -m rag.cli ingest --tenant user_b --path ./docs/user_b_data.txt

# Queries are isolated
python -m rag.cli ask --tenant user_a --question "..."  # Only searches user_a docs
python -m rag.cli ask --tenant user_b --question "..."  # Only searches user_b docs
```

## Storage Structure

```
data/rag/
└── <tenant_id>/
    ├── docs/
    │   ├── <doc_id>__<filename>.txt    # Raw document text
    │   └── <doc_id>.json               # Document metadata
    ├── chunks/
    │   └── <doc_id>.json               # Chunk metadata
    ├── vector_store/
    │   └── chroma.sqlite3              # ChromaDB storage
    └── sparse_index/
        └── sparse_index.db             # SQLite FTS5 database
```

## Security

Path ingestion is restricted to allowed roots:

```python
allowed_ingest_roots = [
    "/app/docs",           # Docker mounted directory
    "./docs",              # Local docs directory
    "./data/uploads"       # Upload directory
]
```

Attempts to ingest files outside these roots will be rejected.

## LangGraph Integration

Use RAG as a tool in your agent:

```python
from rag.langgraph_tool import create_rag_tool, RAG_TOOL_DESCRIPTIONS

# Create tool
rag_ask = create_rag_tool(default_tenant="user123")

# Use in LangGraph
result = rag_ask(
    question="How does authentication work?",
    top_k=5,
    mode="hybrid",
    rerank=True
)

print(result["answer"])
print(result["citations"])
```

Add to agent system prompt:
```python
from rag.langgraph_tool import RAG_TOOL_DESCRIPTIONS

system_prompt = f"""
You are a helpful assistant.

{RAG_TOOL_DESCRIPTIONS}

Use rag_ask when users ask about their uploaded documents.
"""
```

## Teaching Demonstrations

### 1. Chunking with Overlap

```bash
# Ingest with different chunk settings
python -m rag.cli ingest \
  --tenant demo \
  --path ./docs/sample.txt \
  --chunk-size 500 \
  --chunk-overlap 100
```

The chunker will show:
- Chunk boundaries (start/end offsets)
- Overlap regions between consecutive chunks
- Chunk text previews

### 2. Dense vs Sparse vs Hybrid Comparison

```bash
# Dense only
python -m rag.cli retrieve --tenant demo --query "authentication" --mode dense --top-k 5

# Sparse only
python -m rag.cli retrieve --tenant demo --query "authentication" --mode sparse --top-k 5

# Hybrid
python -m rag.cli retrieve --tenant demo --query "authentication" --mode hybrid --top-k 5
```

Compare the results to see:
- Dense finds semantically similar content (synonyms, paraphrases)
- Sparse finds exact keyword matches
- Hybrid balances both

### 3. Reranking Comparison

```bash
# Without reranking
python -m rag.cli retrieve \
  --tenant demo \
  --query "system requirements" \
  --mode hybrid \
  --top-k 5

# With reranking
python -m rag.cli retrieve \
  --tenant demo \
  --query "system requirements" \
  --mode hybrid \
  --rerank \
  --rerank-strategy llm \
  --top-k-candidates 30 \
  --top-k 5
```

Reranking output shows:
- **Candidates before rerank**: Top 10 with initial scores
- **Final after rerank**: Top 5 with rerank scores
- **Score breakdown**: dense, sparse, rerank, and combined scores
- **Rationale**: Why each chunk was scored (for LLM reranking)

### 4. RAG Answer with Citations

```bash
python -m rag.cli ask \
  --tenant demo \
  --question "What are the main features?" \
  --mode hybrid \
  --rerank \
  --top-k 3
```

Shows:
- Generated answer
- Citation labels (e.g., `manual.txt#chunk_0`)
- Retrieved chunks used for context
- Score breakdowns

## Performance Tuning

### For Better Recall
- Use `hybrid` mode with `alpha=0.5` (balanced)
- Increase `top_k_candidates` for reranking (e.g., 50)
- Use smaller `chunk_size` (e.g., 500)

### For Better Precision
- Enable reranking with `llm` strategy
- Use larger `top_k_candidates` (e.g., 30-50)
- Use `dense` mode for semantic search

### For Speed
- Use `dense` mode only (no sparse index)
- Skip reranking
- Use `embed` reranking instead of `llm`

### For Cost Savings
- Use `sparse` mode (no embeddings)
- Use `embed` reranking instead of `llm`
- Reduce `top_k` and `top_k_candidates`

## Troubleshooting

### No results returned
- Check if documents are ingested: `python -m rag.cli list-docs --tenant <tenant_id>`
- Verify tenant ID matches between ingest and query
- Try different retrieval modes

### Slow performance
- Reduce `top_k_candidates` for reranking
- Use `embed` reranking instead of `llm`
- Batch ingest large documents

### Out of memory
- Reduce `chunk_size`
- Reduce `top_k_candidates`
- Process files one at a time

### Path not allowed error
- Check that file path is within allowed roots
- Update `allowed_ingest_roots` in config
- Use absolute paths

## API Reference

See source code documentation in:
- [rag_pipeline.py](rag_pipeline.py) - Main pipeline API
- [hybrid_retriever.py](hybrid_retriever.py) - Retrieval API
- [rerank.py](rerank.py) - Reranking API

## License

Part of the vector_embeddings demonstration project.
