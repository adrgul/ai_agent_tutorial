# RAG Application with LangGraph

A multi-tenant RAG (Retrieval-Augmented Generation) application using FastAPI, LangGraph for workflow orchestration, Qdrant for vector storage, and Ollama for LLM capabilities.

## Features

- **Multi-tenant architecture**: Complete data isolation per tenant
- **LangGraph orchestration**: Structured workflows for document processing and chat
- **Document storage**: Automatic text cleaning, chunking, and embedding
- **RAG-based chat**: Query rewriting, context retrieval, and answer generation
- **Semantic search**: Vector similarity search using sentence-transformers

## Architecture

- **FastAPI**: Web framework
- **LangGraph**: Workflow orchestration with state graphs
- **Qdrant**: Vector database for semantic search
- **Groq API**: Fast cloud LLM (llama-3.1-8b-instant) for text generation
- **Sentence-Transformers**: BAAI/bge-m3 for embeddings

## Project Structure

```
app/
├── main.py                   # FastAPI application
├── models.py                 # Pydantic models
├── config.py                 # Configuration
├── services/
│   ├── llm.py               # Ollama LLM service
│   ├── embeddings.py        # Sentence-transformers wrapper
│   └── qdrant_client.py     # Qdrant vector DB client
└── graphs/
    ├── store_graph.py       # Document storage workflow
    └── chat_graph.py        # RAG chat workflow
```

## Prerequisites

1. **Python 3.11+**
2. **Groq API Key**
   - Get your free API key from https://console.groq.com
   - Add to `.env` file: `GROQ_API_KEY=your_key_here`
3. **Qdrant** vector database running
   - Install from https://qdrant.tech/documentation/quick-start/
   - Or run with Docker: `docker run -p 6333:6333 qdrant/qdrant`
   - Should be accessible at http://localhost:6333

## Installation

Install Python dependencies:
```bash
pip install -r requirements.txt
```

The first run will download the BAAI/bge-m3 embedding model (~2GB).

## Running the Service

Start the FastAPI server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at http://localhost:8000

API documentation is available at http://localhost:8000/docs

## API Endpoints

### POST /store
Store a document with automatic chunking and embedding.

**Request:**
```json
{
  "tenant": "tenant-123",
  "document_id": "doc-456",
  "ocr_text": "Long OCR text from a document..."
}
```

**Response:**
```json
{
  "success": "ok",
  "chunks_count": 5
}
```

**Workflow (LangGraph):**
1. **cleaning** - Clean OCR text (remove artifacts, normalize whitespace)
2. **chunk** - Split into sentence-based chunks (~600 tokens, with overlap)
3. **embedding** - Generate embeddings and store in Qdrant
4. **response** - Build response

### POST /chat
Perform a RAG query with context retrieval and answer generation.

**Request:**
```json
{
  "tenant": "tenant-123",
  "user_id": "user-789",
  "messages": [
    {"role": "user", "content": "What is the company policy on remote work?"}
  ]
}
```

**Response:**
```json
{
  "answer": "Based on the provided documents, the company allows...",
  "document_ids": ["doc-456", "doc-789"]
}
```

**Workflow (LangGraph):**
1. **cleaning** - Extract latest user message and rewrite query using LLM
2. **search** - Embed query and retrieve top-k relevant chunks from Qdrant
3. **answer** - Generate answer using LLM with retrieved context

## Configuration

Edit `app/config.py` to customize:

```python
QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "rag_chunks"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

EMBEDDING_MODEL_NAME = "BAAI/bge-m3"

TOP_K = 8                    # Number of chunks to retrieve
MAX_CONTEXT_CHARS = 8000     # Max context size for LLM
MAX_CHUNK_TOKENS = 600       # Max tokens per chunk
```

## Multi-tenant Support

The application supports multi-tenancy with complete data isolation:
- Each tenant's data is filtered in Qdrant using tenant field
- Tenant identifier must be provided with every API call
- All searches are automatically scoped to the tenant

## LangGraph Workflows

### Store Graph
```
cleaning → chunk → embedding → response → END
```

### Chat Graph  
```
cleaning → search → answer → END
```

Each node in the workflow operates on a shared state dictionary, making the data flow explicit and easy to debug.

## Testing

A test script is provided to verify the application works correctly.

**Run the test:**
```bash
python test_rag.py
```

The test script will:
1. Store 5 sample documents (company policies, benefits, security guidelines, etc.)
2. Ask 5 questions related to the stored documents
3. Display answers and source documents for each question

**Sample output:**
```
✅ Stored 5 documents with 23 total chunks
💬 Answer: Employees are allowed to work remotely up to 3 days per week...
📚 Sources: doc-001
```
