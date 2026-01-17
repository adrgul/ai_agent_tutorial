You are GitHub Copilot. Generate a complete minimal RAG project according to the following specification. Use clear, idiomatic Python 3.11+ and modern FastAPI patterns.

## Tech stack

* Python 3.11+
* FastAPI
* LangGraph for orchestration of nodes/edges
* Qdrant as the vector database
* Sentence-transformers (or similar) for embeddings
* LLM backend: **Ollama**, model: **`qwen2.5:14b-instruct`**

Assume:

* Ollama is running locally on `http://localhost:11434`.
* LLM calls use Ollama's HTTP API:

  * POST `http://localhost:11434/api/chat`
  * model: `qwen2.5:14b-instruct`

Project structure:

* `app/main.py`
* `app/graphs/store_graph.py`
* `app/graphs/chat_graph.py`
* `app/services/embeddings.py`
* `app/services/llm.py`
* `app/services/qdrant_client.py`
* `app/models.py`
* `app/config.py`

No Docker or CI required.

---

## LLM service: (Ollama + qwen2.5:14b-instruct)

Implement `LLMService` (`app/services/llm.py`) that:

* Calls Ollama `/api/chat` with payload:

```jsonc
{
  "model": "qwen2.5:14b-instruct",
  "stream": false,
  "messages": [
    {"role": "system", "content": "<system prompt>"},
    {"role": "user", "content": "<user prompt>"}
  ],
  "options": {
    "temperature": 0.2,
    "top_p": 0.9
  }
}
```

* Returns `data["message"]["content"]`.
* Async-friendly (httpx.AsyncClient).

Public method:

```python
async def generate(self, system_prompt: str, user_prompt: str) -> str
```

---

## Embedding service

`app/services/embeddings.py`:

* Wrap a sentence-transformers model (`BAAI/bge-m3` or `intfloat/multilingual-e5-small`).
* Methods:

```python
get_embedding(text: str) -> list[float]
get_embeddings(texts: list[str]) -> list[list[float]]
@property
dimension -> int
```

* Use cosine-normalized embeddings.

---

## Qdrant wrapper

`app/services/qdrant_client.py`:

* Wrap `qdrant-client`.
* Collection: from config (`rag_chunks`).
* Distance: cosine.
* Vectors: dimension of embedding model.

Methods:

```python
ensure_collection() -> None
upsert_chunks(tenant: str, document_id: str, chunks: list[dict]) -> int
search(tenant: str, query_vector: list[float], top_k: int) -> list[dict]
```

Payload fields per chunk:

* tenant
* document_id
* chunk_index
* text

---

## Models (app/models.py)

```python
class StoreRequest(BaseModel):
    tenant: str
    document_id: str
    ocr_text: str

class StoreResponse(BaseModel):
    success: Literal["ok"]
    chunks_count: int

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    tenant: str
    user_id: str
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    answer: str
    document_ids: List[str]
```

---

## Endpoint 1 – POST /store

Store OCR text, chunk it, embed it, and push to Qdrant via a LangGraph workflow.

### LangGraph workflow nodes (store_graph.py)

State type (`StoreState`):

```python
class StoreState(TypedDict, total=False):
    tenant: str
    document_id: str
    ocr_text: str
    cleaned_text: str
    chunks: List[dict]
    chunks_count: int
    response: dict
```

Nodes:

1. **cleaning**

   * Input: `ocr_text`
   * Clean OCR noise (trim, normalize whitespace, remove artifacts)
   * Output: `cleaned_text`

2. **chunk**

   * Input: `cleaned_text`
   * Split into sentences
   * Group into chunks of max ~600 tokens (~2400 chars approximation)
   * One-sentence overlap between chunks
   * Output: `chunks` with fields: tenant, document_id, text, index

3. **embedding**

   * Input: chunks
   * Compute embeddings
   * Upsert into Qdrant using QdrantService
   * Output: `chunks_count`

4. **response**

   * Build and output: `{"success": "ok", "chunks_count": n}`

Edges:

```
cleaning -> chunk -> embedding -> response
```

FastAPI `/store`:

* Validate request
* Initialize state {tenant, document_id, ocr_text}
* Run LangGraph
* Return response

---

## Endpoint 2 – POST /chat

Perform a RAG query for a given tenant and user's last question.

### LangGraph workflow nodes (chat_graph.py)

State type (`ChatState`):

```python
class ChatState(TypedDict, total=False):
    tenant: str
    user_id: str
    messages: List[ChatMessage]
    latest_user_message: str
    rewritten_query: str
    relevant_chunks: List[dict]
    document_ids: List[str]
    answer: str
```

Nodes:

1. **cleaning**

   * Extract `messages[-1].content`
   * Use LLMService.generate with system prompt:
     "You are a professional company assistant. Rewrite the user query clearly and concisely, preserving the original meaning. Output only the rewritten query."
   * Output: `rewritten_query`

2. **search**

   * Embed rewritten query
   * Qdrant search filtered by `tenant`
   * top_k = from config (e.g. 8)
   * Output: `relevant_chunks` and distinct `document_ids`

3. **answer**

   * Build context from chunks
   * Use LLMService.generate with system prompt:
     "You are a professional company assistant. Answer strictly based on the provided context chunks. If the answer is not in the context, say you do not have enough information."
   * Return concise answer

Edges:

```
cleaning -> search -> answer
```

FastAPI `/chat`:

* Validate request
* Build initial ChatState
* Run LangGraph
* Return `{answer, document_ids}`

---

## Config (app/config.py)

```python
QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "rag_chunks"

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b-instruct"

EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
TOP_K = 8
MAX_CONTEXT_CHARS = 8000
MAX_CHUNK_TOKENS = 600
```

---

## Requirements

* fastapi
* uvicorn[standard]
* langgraph
* qdrant-client
* sentence-transformers
* httpx
* pydantic

---

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

Now generate all Python files according to this specification.
