# KnowledgeRouter API Documentation

**Version:** 2.2  
**Base URL:** `http://localhost:8001/api/`  
**Content-Type:** `application/json`  
**Orchestration:** LangGraph StateGraph (4 nodes)

> **Note:** Minden `/api/query/` hívás egy teljes LangGraph workflow-n megy keresztül:
> Intent Detection → Retrieval (RAG) → Generation (LLM) → Workflow Execution

---

## 📋 Table of Contents

- [Authentication](#authentication)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [POST /api/query/](#post-apiquery)
  - [GET /api/sessions/{session_id}/](#get-apisessionssession_id)
  - [POST /api/reset-context/](#post-apireset-context)
  - [GET /api/usage-stats/](#get-apiusage-stats)
  - [DELETE /api/usage-stats/](#delete-apiusage-stats)
  - [GET /api/cache-stats/](#get-apicache-stats)
  - [DELETE /api/cache-stats/](#delete-apicache-stats)
  - [POST /api/feedback/citation/](#post-apifeedbackcitation) **NEW**
  - [GET /api/feedback/stats/](#get-apifeedbackstats) **NEW**
  - [GET /api/google-drive/files/](#get-apigoogle-drivefiles)
- [Data Models](#data-models)
- [Cache Invalidation Strategy](#cache-invalidation-strategy)
- [Feedback System](#feedback-system) **NEW**
- [Status Codes](#status-codes)
- [Rate Limits & Retry](#rate-limits--retry)

---

## 🔐 Authentication

Jelenleg nincs authentication (development mode). Production környezetben ajánlott:
- API Key authentication (Header: `X-API-Key`)
- JWT tokens session-alapú auth-hoz
- OAuth 2.0 enterprise integrációhoz

---

## ⚠️ Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {
    "field": "Additional context"
  }
}
```

### Common Error Codes

| HTTP Code | Error Code | Jelentés |
|-----------|------------|----------|
| 400 | `INVALID_REQUEST` | Hibás request paraméterek |
| 400 | `EMPTY_QUERY` | Üres query string |
| 404 | `SESSION_NOT_FOUND` | Session nem létezik |
| 413 | `QUERY_TOO_LONG` | Query meghaladja a token limitet |
| 500 | `INTERNAL_ERROR` | Backend hiba |
| 503 | `SERVICE_UNAVAILABLE` | OpenAI API nem elérhető |

---

## 📡 Endpoints

### POST `/api/query/`

**Multi-domain RAG query feldolgozás LangGraph StateGraph orchestrációval.**

Feldolgoz egy felhasználói kérdést **LangGraph StateGraph** segítségével, amely 4 node-on keresztül vezérli a folyamatot:

1. **Intent Detection Node** - Domain klasszifikáció (keyword match + LLM fallback)
2. **Retrieval Node** - Domain-specifikus RAG keresés Qdrant-ban
3. **Generation Node** - LLM válasz generálás (GPT-4o-mini)
4. **Workflow Execution Node** - Domain-specifikus workflow triggering (HR/IT)

**Domain Detection Stratégia:**
- **Keyword-alapú**: Gyors, költségmentes pre-classification (pl. "brand" → marketing)
- **LLM-alapú**: Fallback komplex querykhez (pl. "VPN problem" → it)
- **Supported Domains**: HR, IT, Finance, Legal, Marketing, General

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "user_id": "string",
  "session_id": "string",
  "query": "string",
  "organisation": "string (optional)"
}
```

**Parameters:**

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `user_id` | string | Yes | Felhasználó egyedi azonosítója | `"emp_001"` |
| `session_id` | string | Yes | Session azonosító (conversation tracking) | `"session_abc123"` |
| `query` | string | Yes | Felhasználó kérdése (max 10,000 tokens) | `"Mi a brand guideline sorhossz?"` |
| `organisation` | string | No | Szervezet neve (optional metadata) | `"ACME Corp"` |

**Constraints:**
- `query` nem lehet üres
- `query` max 10,000 tokens (~40,000 characters)
- `session_id` formátum: alphanumeric + underscore

#### Response

**Success (200 OK):**

```json
{
  "success": true,
  "data": {
    "domain": "marketing",
    "answer": "A brand guideline sorhosszra vonatkozó javaslat:\n\n### Maximális sorhossz\n- **70-80 karakter** a javasolt maximális érték\n- Megfelelő mennyiségű üres tér alkalmazása kötelező",
    "citations": [
      {
        "doc_id": "1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk2",
        "title": "Aurora_Digital_Brand_Guidelines_eng.docx",
        "score": 0.89,
        "url": null,
        "content": "Maximális sorhossz: 70–80 karakter..."
      }
    ],
    "workflow": {
      "action": "marketing_info_provided",
      "type": "information_query",
      "status": "completed",
      "next_step": null
    }
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Request sikerességét jelzi |
| `data.domain` | string | Detektált domain (`hr`, `it`, `finance`, `legal`, `marketing`, `general`) |
| `data.answer` | string | Generált válasz (Markdown formátumban) |
| `data.citations` | array | Forrás dokumentumok listája |
| `data.citations[].doc_id` | string | Dokumentum egyedi azonosítója |
| `data.citations[].title` | string | Dokumentum címe/fájlneve |
| `data.citations[].score` | float | Relevancia score (0.0-1.0) |
| `data.citations[].url` | string\|null | Google Drive link (ha elérhető) |
| `data.citations[].content` | string | Chunk szöveg tartalma |
| `data.workflow` | object\|null | Workflow információk (ha triggerlődött) |
| `data.workflow.action` | string | Workflow action név |
| `data.workflow.type` | string | Workflow típus |
| `data.workflow.status` | string | Workflow státusz (`draft`, `pending`, `completed`) |
| `data.workflow.next_step` | string\|null | Következő lépés leírása |

**Error Responses:**

**400 Bad Request - Empty Query:**
```json
{
  "success": false,
  "error": "Query cannot be empty",
  "code": "EMPTY_QUERY"
}
```

**413 Request Too Large:**
```json
{
  "success": false,
  "error": "Query is too long. Please shorten your question to under 10,000 tokens (~40,000 characters).",
  "code": "QUERY_TOO_LONG",
  "details": {
    "estimated_tokens": 13500,
    "max_tokens": 10000
  }
}
```

**503 Service Unavailable:**
```json
{
  "success": false,
  "error": "OpenAI API is currently unavailable. Please try again later.",
  "code": "SERVICE_UNAVAILABLE"
}
```

#### LangGraph Execution Flow

```
User Query: "Mi a brand guideline sorhossz?"
    ↓
[LangGraph StateGraph Execution]
    ↓
[Node 1: Intent Detection]
├─ Keyword match: "brand" → domain = "marketing"
└─ state["domain"] = "marketing" ✅
    ↓
[Node 2: Retrieval]
├─ Read: state["domain"] = "marketing"
├─ Qdrant filter: {"domain": "marketing"}
├─ Semantic search: top_k=5
└─ state["citations"] = [marketing_docs] ✅
    ↓
[Node 3: Generation]
├─ Read: state["citations"]
├─ Build context from marketing docs
├─ LLM prompt + generation (GPT-4o-mini)
└─ state["output"] = {answer, citations} ✅
    ↓
[Node 4: Workflow]
├─ Read: state["domain"] = "marketing"
├─ No workflow for marketing queries
└─ state["workflow"] = null
    ↓
[Response] → {domain, answer, citations, workflow}
```

**State Management:**
- AgentState TypedDict carries data between nodes
- Each node reads/writes to shared state
- No manual state passing required (LangGraph orchestration)

#### Example Usage

**cURL:**
```bash
curl -X POST http://localhost:8001/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "emp_001",
    "session_id": "session_12345",
    "query": "Mi a brand guideline sorhossz ajánlása?"
  }'
```

**Python:**
```python
import requests

response = requests.post(
    "http://localhost:8001/api/query/",
    json={
        "user_id": "emp_001",
        "session_id": "session_12345",
        "query": "Mi a brand guideline sorhossz ajánlása?"
    }
)

data = response.json()
print(f"Domain: {data['data']['domain']}")
print(f"Answer: {data['data']['answer']}")
print(f"Citations: {len(data['data']['citations'])}")
```

**PowerShell:**
```powershell
$body = @{
    user_id = "emp_001"
    session_id = "session_12345"
    query = "Mi a brand guideline sorhossz?"
} | ConvertTo-Json

$response = Invoke-WebRequest `
  -Uri "http://localhost:8001/api/query/" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body

$data = ($response.Content | ConvertFrom-Json).data
Write-Host "Domain: $($data.domain)"
Write-Host "Answer: $($data.answer)"
```

---

### POST `/api/regenerate/` **NEW**

**⚡ Cached regeneration - Gyors válasz újragenerálás RAG nélkül.**

Újragenerálja a választ **ugyanazzal a RAG kontextussal** (domain + citations) mint az előző query, de új LLM generálással. Kihagyja az intent detection és RAG retrieval node-okat, csak a generation + workflow node-okat futtatja.

**Use Cases:**
- 🔄 Refresh answer: Ugyanaz a kérdés, más megfogalmazással
- 🎯 Retry generation: Válasz minőség javítása
- 💰 Cost savings: 80% olcsóbb mint full pipeline
- ⚡ Speed: 38% gyorsabb (~3500ms vs ~5600ms)

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "session_id": "string",
  "query": "string",
  "user_id": "string"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | Session ID (kell legyen előző bot message) |
| `query` | string | Yes | Újragenerálandó kérdés |
| `user_id` | string | Yes | Felhasználó azonosítója |

**Constraints:**
- Session-ben kell lennie minimum 1 bot message-nek
- Bot message-ben kell lennie `domain` és `citations` mezőknek

#### Response

**Success (200 OK):**

```json
{
  "success": true,
  "data": {
    "domain": "marketing",
    "answer": "Regenerált válasz: A brand guideline sorhosszra...",
    "citations": [
      {
        "doc_id": "1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk2",
        "title": "Aurora_Digital_Brand_Guidelines_eng.docx",
        "score": 0.89,
        "content": "Maximális sorhossz: 70–80 karakter..."
      }
    ],
    "workflow": null,
    "regenerated": true,
    "cache_info": {
      "skipped_nodes": ["intent_detection", "retrieval"],
      "executed_nodes": ["generation", "workflow"],
      "cached_citations_count": 5,
      "cached_domain": "marketing"
    }
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `regenerated` | boolean | Mindig `true` - jelzi, hogy cached regeneration |
| `cache_info` | object | Metadata a cache használatról |
| `cache_info.skipped_nodes` | array | Kihagyott node-ok (intent, retrieval) |
| `cache_info.executed_nodes` | array | Futtatott node-ok (generation, workflow) |
| `cache_info.cached_citations_count` | int | Cache-elt citations száma |

#### LangGraph Execution Flow (Cached)

```
User clicks ⚡ Refresh → POST /api/regenerate/
    ↓
[Read Session History]
├─ Last bot message extraction
├─ domain = "marketing" (FROM CACHE)
└─ citations = [...] (FROM CACHE)
    ↓
[LangGraph Partial Execution]
    ↓
[SKIP: Intent Detection] ❌
├─ Savings: ~100 tokens + LLM call
└─ Use cached domain = "marketing"
    ↓
[SKIP: RAG Retrieval] ❌
├─ Savings: ~1500 tokens + Qdrant query
└─ Use cached citations = [...]
    ↓
[Node 3: Generation] ✅ EXECUTED
├─ Read: cached citations
├─ Build context (SAME as before)
├─ LLM regenerates answer (FRESH)
└─ state["output"] = {new_answer, same_citations}
    ↓
[Node 4: Workflow] ✅ EXECUTED
├─ Read: cached domain
└─ Execute workflow (if applicable)
    ↓
[Response] → {regenerated: true, cache_info}
```

**Performance Comparison:**

| Metric | Full Pipeline | Cached Regeneration | Savings |
|--------|--------------|---------------------|---------|
| **Time** | ~5600ms | ~3500ms | **38% faster** |
| **Tokens** | ~2500 | ~500 | **80% cheaper** |
| **LLM Calls** | 2 | 1 | **50% less** |
| **Qdrant** | 1 query | 0 queries | **100% saved** |
| **Nodes** | 4 | 2 | **50% skipped** |

#### Example Usage

**cURL:**
```bash
curl -X POST http://localhost:8001/api/regenerate/ \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_12345",
    "query": "Mi a brand guideline sorhossz?",
    "user_id": "emp_001"
  }'
```

**Python:**
```python
response = requests.post(
    "http://localhost:8001/api/regenerate/",
    json={
        "session_id": "session_12345",
        "query": "Mi a brand guideline sorhossz?",
        "user_id": "emp_001"
    }
)

data = response.json()["data"]
print(f"Regenerated: {data['regenerated']}")  # True
print(f"Skipped nodes: {data['cache_info']['skipped_nodes']}")
print(f"Savings: {data['cache_info']['cached_citations_count']} citations reused")
```

**PowerShell:**
```powershell
$body = @{
    session_id = "session_12345"
    query = "Mi a brand guideline sorhossz?"
    user_id = "emp_001"
} | ConvertTo-Json

$response = Invoke-WebRequest `
  -Uri "http://localhost:8001/api/regenerate/" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body

$data = ($response.Content | ConvertFrom-Json).data
Write-Host "⚡ Regenerated: $($data.regenerated)"
Write-Host "Cached citations: $($data.cache_info.cached_citations_count)"
```

**Error Responses:**

**400 Bad Request (No bot messages in session):**
```json
{
  "success": false,
  "error": "No previous bot messages found in session",
  "code": "NO_CACHE_AVAILABLE"
}
```

**404 Not Found (Session doesn't exist):**
```json
{
  "success": false,
  "error": "Session not found",
  "code": "SESSION_NOT_FOUND"
}
```

---

### GET `/api/sessions/{session_id}/`

**Session conversation history lekérdezése.**

Visszaadja egy session összes üzenetét időrendi sorrendben.

#### Request

**URL Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session egyedi azonosítója |

**Example:**
```
GET /api/sessions/session_abc123/
```

#### Response

**Success (200 OK):**

```json
{
  "success": true,
  "data": {
    "session_id": "session_abc123",
    "created_at": "2025-12-16T10:30:00Z",
    "updated_at": "2025-12-16T14:45:00Z",
    "message_count": 4,
    "messages": [
      {
        "role": "user",
        "content": "Mi a brand guideline sorhossz?",
        "timestamp": "2025-12-16T10:30:00Z"
      },
      {
        "role": "assistant",
        "content": "A brand guideline sorhosszra vonatkozó javaslat...",
        "timestamp": "2025-12-16T10:30:05Z",
        "citations": [
          {
            "doc_id": "...",
            "title": "Aurora_Digital_Brand_Guidelines_eng.docx",
            "score": 0.89
          }
        ]
      }
    ]
  }
}
```

**Error Responses:**

**404 Not Found:**
```json
{
  "success": false,
  "error": "Session not found",
  "code": "SESSION_NOT_FOUND",
  "details": {
    "session_id": "session_abc123"
  }
}
```

#### Example Usage

**cURL:**
```bash
curl http://localhost:8001/api/sessions/session_abc123/
```

**Python:**
```python
import requests

response = requests.get(
    "http://localhost:8001/api/sessions/session_abc123/"
)

data = response.json()
print(f"Messages: {data['data']['message_count']}")
for msg in data['data']['messages']:
    print(f"{msg['role']}: {msg['content'][:50]}...")
```

---

### POST `/api/reset-context/`

**Session context törlése.**

Törli a session beszélgetési előzményeit, de a user profil megmarad.

#### Request

**Body:**
```json
{
  "session_id": "string"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | Törölni kívánt session ID |

#### Response

**Success (200 OK):**

```json
{
  "success": true,
  "message": "Context reset successfully",
  "data": {
    "session_id": "session_abc123",
    "cleared_messages": 12
  }
}
```

**Error Responses:**

**404 Not Found:**
```json
{
  "success": false,
  "error": "Session not found",
  "code": "SESSION_NOT_FOUND"
}
```

#### Example Usage

**cURL:**
```bash
curl -X POST http://localhost:8001/api/reset-context/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "session_abc123"}'
```

---

### GET `/api/usage-stats/`

**OpenAI API token használat és költség tracking.**

Visszaadja az összes API hívás token használatát és költségét az utolsó reset óta.

#### Request

**No parameters required.**

#### Response

**Success (200 OK):**

```json
{
  "success": true,
  "data": {
    "calls": 127,
    "prompt_tokens": 45200,
    "completion_tokens": 12800,
    "total_tokens": 58000,
    "total_cost_usd": 0.0874,
    "average_tokens_per_call": 456.69,
    "models_used": {
      "gpt-4o-mini": {
        "calls": 127,
        "tokens": 58000,
        "cost_usd": 0.0874
      }
    }
  },
  "message": "Token usage statistics since last reset",
  "meta": {
    "last_reset": "2025-12-16T10:00:00Z",
    "tracking_duration_hours": 4.75
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `calls` | integer | Összes API hívás száma |
| `prompt_tokens` | integer | Input tokens összesen |
| `completion_tokens` | integer | Output tokens összesen |
| `total_tokens` | integer | Összes token (prompt + completion) |
| `total_cost_usd` | float | Becsült költség USD-ben (GPT-4o-mini pricing) |
| `average_tokens_per_call` | float | Átlagos token/hívás |

**Pricing (GPT-4o-mini per 1M tokens):**
- Input: $0.15
- Output: $0.60

#### Example Usage

**cURL:**
```bash
curl http://localhost:8001/api/usage-stats/
```

**Python:**
```python
import requests

response = requests.get("http://localhost:8001/api/usage-stats/")
data = response.json()['data']

print(f"Total calls: {data['calls']}")
print(f"Total cost: ${data['total_cost_usd']:.4f}")
print(f"Avg tokens/call: {data['average_tokens_per_call']:.1f}")
```

---

### DELETE `/api/usage-stats/`

**Usage statistics nullázása.**

Visszaállítja a token tracking számláló(ka)t nullára.

#### Request

**No parameters required.**

#### Response

**Success (200 OK):**

```json
{
  "success": true,
  "message": "Usage statistics reset successfully",
  "data": {
    "previous_stats": {
      "calls": 127,
      "total_tokens": 58000,
      "total_cost_usd": 0.0874
    },
    "new_stats": {
      "calls": 0,
      "total_tokens": 0,
      "total_cost_usd": 0.0
    }
  }
}
```

#### Example Usage

**cURL:**
```bash
curl -X DELETE http://localhost:8001/api/usage-stats/
```

**Python:**
```python
import requests

response = requests.delete("http://localhost:8001/api/usage-stats/")
print(response.json()['message'])
```

---

### GET `/api/cache-stats/`

**Redis cache statisztikák lekérdezése.**

Visszaadja a Redis cache állapotát, memória használatot, találati arányt és a leggyakoribb query-ket.

#### Request

**No parameters required.**

#### Response

**Success (200 OK):**

```json
{
  "success": true,
  "data": {
    "stats": {
      "connected": true,
      "used_memory_mb": 1.06,
      "total_keys": 125,
      "hit_rate": 0.68,
      "embedding_keys": 89,
      "query_keys": 36,
      "uptime_hours": 24.5
    },
    "top_queries": [
      {
        "query": "Mi a brand guideline?",
        "domain": "marketing",
        "hits": 45,
        "cached_at": "2025-12-17T10:30:15Z"
      },
      {
        "query": "Szabadság igénylés",
        "domain": "hr",
        "hits": 32,
        "cached_at": "2025-12-17T09:15:22Z"
      }
    ]
  },
  "message": "Cache statistics and popular queries"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `stats.connected` | boolean | Redis kapcsolat állapota |
| `stats.used_memory_mb` | float | Használt memória MB-ban |
| `stats.total_keys` | integer | Összes cache kulcs |
| `stats.hit_rate` | float | Cache találati arány (0.0-1.0) |
| `stats.embedding_keys` | integer | Embedding cache kulcsok száma |
| `stats.query_keys` | integer | Query result cache kulcsok száma |
| `stats.uptime_hours` | float | Redis uptime órákban |
| `top_queries` | array | Top 10 leggyakoribb query |
| `top_queries[].hits` | integer | Hányszor találat volt erre a query-re |

**Cache Stratégia:**
- **Embedding Cache**: 7 nap TTL, ~6KB/embedding
- **Query Result Cache**: 24 óra TTL, ~200B/query (doc IDs)
- **Max Memory**: 512MB (LRU eviction)
- **Költségmegtakarítás**: ~$0.00002/cache hit + 200ms latency javulás

**Error Response (Redis unavailable):**
```json
{
  "success": true,
  "data": {
    "stats": {
      "connected": false
    },
    "top_queries": []
  },
  "message": "Redis cache is not available"
}
```

#### Example Usage

**cURL:**
```bash
curl http://localhost:8001/api/cache-stats/
```

**Python:**
```python
import requests

response = requests.get("http://localhost:8001/api/cache-stats/")
data = response.json()['data']

print(f"Cache connected: {data['stats']['connected']}")
print(f"Hit rate: {data['stats']['hit_rate']*100:.1f}%")
print(f"Memory used: {data['stats']['used_memory_mb']:.2f} MB")
print(f"\\nTop queries:")
for query in data['top_queries'][:5]:
    print(f"  {query['hits']}x - {query['query']} [{query['domain']}]")
```

---

### DELETE `/api/cache-stats/`

**Redis cache törlése vagy domain-specifikus invalidálás.**

Törli az összes cache-t vagy csak egy adott domain cache-ét.

#### Request

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `domain` | string | No | Domain név (hr, it, finance, marketing, legal, general) |

**Examples:**
```
DELETE /api/cache-stats/              # Töröl mindent
DELETE /api/cache-stats/?domain=marketing  # Csak marketing cache
```

#### Response

**Success (200 OK) - Full Clear:**

```json
{
  "success": true,
  "message": "All cache cleared successfully",
  "data": {
    "keys_deleted": 125,
    "domains_affected": ["hr", "it", "marketing", "finance"]
  }
}
```

**Success (200 OK) - Domain Clear:**

```json
{
  "success": true,
  "message": "Cache invalidated for domain: marketing",
  "data": {
    "keys_deleted": 36,
    "domain": "marketing"
  }
}
```

**Use Cases:**
- **Full Clear**: Deployment után vagy major config change
- **Domain Clear**: Dokumentum update után (pl. `sync_domain_docs.py` futtatás)

#### Example Usage

**cURL - Teljes törlés:**
```bash
curl -X DELETE http://localhost:8001/api/cache-stats/
```

**cURL - Domain-specifikus:**
```bash
curl -X DELETE "http://localhost:8001/api/cache-stats/?domain=marketing"
```

**Python:**
```python
import requests

# Marketing domain cache törlése
response = requests.delete(
    "http://localhost:8001/api/cache-stats/",
    params={"domain": "marketing"}
)
print(response.json()['message'])
```

**PowerShell:**
```powershell
# Teljes cache törlés
Invoke-RestMethod -Uri "http://localhost:8001/api/cache-stats/" -Method DELETE

# Marketing cache törlés
Invoke-RestMethod -Uri "http://localhost:8001/api/cache-stats/?domain=marketing" -Method DELETE
```

---

### GET `/api/google-drive/files/`

**Google Drive marketing folder fájlok listázása.**

Visszaadja a marketing dokumentumokat tartalmazó Google Drive folder összes fájlját.

#### Request

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `folder_id` | string | No | `1Jo5doFrRgTscczqR0c6bsS2H0a7pS2ZR` | Google Drive folder ID |

**Example:**
```
GET /api/google-drive/files/?folder_id=1Jo5doFrRgTscczqR0c6bsS2H0a7pS2ZR
```

#### Response

**Success (200 OK):**

```json
{
  "success": true,
  "folder_id": "1Jo5doFrRgTscczqR0c6bsS2H0a7pS2ZR",
  "file_count": 3,
  "files": [
    {
      "id": "150jnsbIl3HreheZyiCDU3fUt9cdL_EFS",
      "name": "Aurora_Digital_Arculati_Kezikonyv_HU.pdf",
      "mimeType": "application/pdf",
      "size": "163689",
      "createdTime": "2025-12-16T13:59:26.841Z",
      "modifiedTime": "2025-12-16T13:58:59.000Z",
      "webViewLink": "https://drive.google.com/file/d/150jnsbIl3HreheZyiCDU3fUt9cdL_EFS/view?usp=drivesdk",
      "thumbnailLink": "https://lh3.googleusercontent.com/...",
      "iconLink": "https://drive-thirdparty.googleusercontent.com/..."
    },
    {
      "id": "1utetoO-ApR4lmOpY1HS63va_gqmjDfsA",
      "name": "Aurora_Digital_Arculati_Kezikonyv_HU.docx",
      "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "size": "38007",
      "createdTime": "2025-12-16T13:59:26.702Z",
      "modifiedTime": "2025-12-16T13:58:36.000Z",
      "webViewLink": "https://docs.google.com/document/d/1utetoO-ApR4lmOpY1HS63va_gqmjDfsA/edit?usp=drivesdk"
    },
    {
      "id": "1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv",
      "name": "Aurora_Digital_Brand_Guidelines_eng.docx",
      "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "size": "37820",
      "createdTime": "2025-12-16T13:56:46.664Z",
      "modifiedTime": "2025-12-16T13:55:28.000Z",
      "webViewLink": "https://docs.google.com/document/d/1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv/edit?usp=drivesdk"
    }
  ]
}
```

**Error Responses:**

**503 Service Unavailable:**
```json
{
  "success": false,
  "error": "Google Drive API is not available",
  "code": "SERVICE_UNAVAILABLE"
}
```

#### Example Usage

**cURL:**
```bash
curl "http://localhost:8001/api/google-drive/files/"
```

**Python:**
```python
import requests

response = requests.get("http://localhost:8001/api/google-drive/files/")
data = response.json()

print(f"Total files: {data['file_count']}")
for file in data['files']:
    print(f"- {file['name']} ({file['mimeType']})")
```

---

## 📊 Data Models

### Citation

```typescript
interface Citation {
  doc_id: string;          // Unique document/chunk ID
  title: string;           // Document title/filename
  score: number;           // Relevance score (0.0-1.0)
  url: string | null;      // Google Drive link (optional)
  content: string;         // Chunk text content
}
```

### Workflow

```typescript
interface Workflow {
  action: string;          // Workflow action name
  type: string;            // Workflow type (vacation_request, ticket, etc.)
  status: string;          // Status (draft, pending, completed)
  next_step: string | null; // Next step description
}
```

### Message

```typescript
interface Message {
  role: "user" | "assistant"; // Message sender
  content: string;            // Message text
  timestamp: string;          // ISO 8601 timestamp
  citations?: Citation[];     // Citations (assistant only)
  workflow?: Workflow;        // Workflow info (assistant only)
}
```

### Session

```typescript
interface Session {
  session_id: string;
  created_at: string;       // ISO 8601 timestamp
  updated_at: string;       // ISO 8601 timestamp
  message_count: number;
  messages: Message[];
}
```

---

## 🚦 Status Codes

| Code | Name | Description | Usage |
|------|------|-------------|-------|
| **200** | OK | Request successful | Successful query, session fetch |
| **201** | Created | Resource created | (Future: file upload) |
| **400** | Bad Request | Invalid parameters | Empty query, malformed JSON |
| **401** | Unauthorized | Missing/invalid auth | (Future: API key auth) |
| **404** | Not Found | Resource not exists | Session not found, file not found |
| **413** | Request Too Large | Payload too big | Query >10k tokens |
| **429** | Too Many Requests | Rate limit exceeded | (Future: rate limiting) |
| **500** | Internal Server Error | Backend exception | Unhandled error |
| **503** | Service Unavailable | External service down | OpenAI API timeout/error |

---

## 🔄 Rate Limits & Retry

### Automatic Retry Logic

A rendszer automatikus retry-t alkalmaz az alábbi esetekben:

**Retry Stratégia:**

```python
@retry_with_exponential_backoff(
    max_retries=3,
    initial_delay=1.0,
    exponential_base=2.0,
    jitter=True
)
```

**Retry Táblázat:**

| Error Type | Retry? | Backoff | Max Attempts |
|------------|--------|---------|--------------|
| RateLimitError (429) | ✅ Yes | Exponential (1s, 2s, 4s) | 3 |
| APITimeoutError | ✅ Yes | Exponential | 3 |
| APIConnectionError | ✅ Yes | Exponential | 3 |
| Server Error (5xx) | ✅ Yes | Exponential | 3 |
| Client Error (4xx) | ❌ No | - | 1 (immediate fail) |
| AuthenticationError | ❌ No | - | 1 (immediate fail) |

**Exponential Backoff Formula:**
```
delay = initial_delay * (exponential_base ^ attempt) * jitter
jitter = random(0.5, 1.5)  # 50-150% of base delay

# Examples:
Attempt 1: 1.0s * 2^0 * 1.2 = 1.2s
Attempt 2: 1.0s * 2^1 * 0.8 = 1.6s
Attempt 3: 1.0s * 2^2 * 1.3 = 5.2s
```

**Retry-After Header Support:**

RateLimitError esetén a rendszer tiszteletben tartja az OpenAI `Retry-After` headerét:

```python
if retry_after := error.retry_after:
    wait_time = float(retry_after)
else:
    wait_time = exponential_backoff(attempt)
```

### Rate Limits (OpenAI API)

**GPT-4o-mini (default model):**
- **TPM**: 200,000 tokens/minute
- **RPM**: 500 requests/minute
- **TPD**: 2,000,000 tokens/day

**Védelem:**
- Input validation: Max 10k tokens/query
- Prompt truncation: Max 100k tokens context
- Auto-retry with backoff

---

## 📝 Notes

### Multi-Domain Architecture

A rendszer egyetlen Qdrant collection-t használ (`multi_domain_kb`) domain-specifikus szűréssel:

```python
# Domain filter példa
domain_filter = Filter(
    must=[
        FieldCondition(
            key="domain",
            match=MatchValue(value="marketing")
        )
    ]
)

# Keresés domain filter-rel
results = qdrant_client.search(
    collection_name="multi_domain_kb",
    query_vector=embedding,
    query_filter=domain_filter,  # Csak marketing docs!
    limit=5
)
```

**Előnyök:**
- ✅ Skálázható több domain-re
- ✅ Gyors domain filtering (payload index)
- ✅ Egyetlen collection management
- ✅ Hybrid search ready (semantic + BM25)

### Token Estimation

**Approximation formula:**
```python
def estimate_tokens(text: str) -> int:
    return len(text) // 4  # 1 token ≈ 4 chars
```

**Accuracy:**
- English: ~90% accurate
- Hungarian: ~85% accurate (longer words)
- Code: ~70% accurate (special chars)

**Production recommendation:**
```python
from tiktoken import encoding_for_model

enc = encoding_for_model("gpt-4o-mini")
tokens = len(enc.encode(text))  # Exact token count
```

### Cost Optimization Tips

**1. Input Validation:**
```python
# Block oversized queries early
check_token_limit(query, max_tokens=10000)
# Saves: ~$0.015 per rejected 100k char query
```

**2. Prompt Truncation:**
```python
# Use top 3 docs only, truncate rest
if len(context) > 100000:
    context = top_3_docs_full + rest_truncated
# Saves: ~30% token cost
```

**3. Caching:**
```python
# Embedding cache: 7 days TTL
# Query result cache: 24 hours TTL
# Saves: $0.00002 per cache hit + 200ms latency
```

---

## 🔄 Cache Invalidation Strategy

### Probléma

Amikor a Qdrant vector database-ben dokumentumokat frissítesz/törlöl, a Redis cache elavult eredményeket szolgálhat ki:

**Példa szcenárió:**
1. User query: "Mi a brand guideline?" → **cache HIT** (doc IDs: [123, 456])
2. Admin **frissíti** marketing dokumentumokat → Qdrant tartalom változik
3. User ugyanaz: "Mi a brand guideline?" → **elavult cache** ❌

### Megoldás

**Automatikus cache invalidálás dokumentum szinkronizálás után:**

```bash
# sync_domain_docs.py automatikusan invalidálja a cache-t
python backend/scripts/sync_domain_docs.py --domain marketing --folder-id FOLDER_ID
# → Qdrant frissítés
# → Redis cache invalidálás (marketing domain)
```

**Implementáció:**
```python
# backend/scripts/sync_domain_docs.py
from infrastructure.redis_client import redis_cache

# Sync befejezése után
if redis_cache.is_available():
    redis_cache.invalidate_query_cache(domain=self.domain)
    logger.info(f"🗑️ Redis cache invalidated for domain: {self.domain}")
```

### Cache Rétegek

**4-rétegű cache stratégia:**

```
Layer 1: Query Result Cache → Qdrant doc IDs (24h TTL)
         ├─ HIT:  Fetch by IDs (512ms) ✅ FASTEST
         └─ MISS: ↓ Layer 2

Layer 2: Embedding Cache → OpenAI embedding (7d TTL)
         ├─ HIT:  Use cached embedding (1ms)
         └─ MISS: Generate embedding (200ms) ↓ Layer 3

Layer 3: Qdrant Search → Semantic similarity (250ms)
         └─ Results ↓ Layer 4

Layer 4: Cache Results → Store for next query
```

### Invalidálási Use Cases

| Esemény | Akció | Parancs |
|---------|-------|---------|
| **Marketing docs frissítve** | Domain-specifikus invalidálás | `DELETE /api/cache-stats/?domain=marketing` |
| **Minden domain frissítve** | Teljes cache törlés | `DELETE /api/cache-stats/` |
| **Deployment** | Teljes cache törlés (óvatosan) | `DELETE /api/cache-stats/` |
| **Redis config change** | Teljes cache törlés | `DELETE /api/cache-stats/` |

### Best Practices

**✅ DO:**
- Invalidáld a domain cache-t minden `sync_domain_docs.py` futtatás után
- Monitor cache hit rate (`GET /api/cache-stats/`)
- Használj domain-specifikus invalidálást (precision)

**❌ DON'T:**
- Ne töröld az összes cache-t production-ben (túl gyakori full clear → cold start)
- Ne felejtsd el invalidálni cache-t dokumentum update után
- Ne cache-elj "real-time" adatokat (pl. live inventory)

### Cache TTL Értékek

| Cache Típus | TTL | Indoklás |
|-------------|-----|----------|
| **Embedding** | 7 nap | Dokumentum szöveg ritkán változik |
| **Query Result** | 24 óra | Balansz: freshness vs. performance |
| **Hit Counter** | Végtelen | Statisztika (nem invalidálódik) |

### Monitoring

```bash
# Nézd meg cache health-t
curl http://localhost:8001/api/cache-stats/

# Várható eredmény:
{
  "hit_rate": 0.68,          # 68% találat → jó
  "used_memory_mb": 45.2,    # 512MB alatt → rendben
  "total_keys": 1234         # Növekszik idővel
}
```

**Alert threshold-ok:**
- Hit rate < 30% → Cache warming szükséges
- Memory > 450MB → LRU eviction kezdődik (rendben)
- Connected: false → Redis down ⚠️

---

## 📊 Feedback System

### POST `/api/feedback/citation/`

**Submit user feedback (like/dislike) for a specific citation.**

Aszinkron háttérfolyamatban menti az adatbázisba (PostgreSQL), nem blokkolja a választ. Támogatja domain-specifikus feedback aggregációt és citation ranking-et.

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "citation_id": "string",
  "domain": "string",
  "user_id": "string",
  "session_id": "string",
  "query_text": "string",
  "feedback_type": "like" | "dislike",
  "query_embedding": [float] (optional),
  "citation_rank": integer (optional)
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `citation_id` | string | Yes | Document ID (Qdrant point ID) |
| `domain` | string | Yes | Domain (marketing, hr, it, etc.) |
| `user_id` | string | Yes | User identifier |
| `session_id` | string | Yes | Conversation session ID |
| `query_text` | string | Yes | Original user query |
| `feedback_type` | string | Yes | "like" or "dislike" |
| `query_embedding` | array | No | 1536-dim embedding for context-aware scoring |
| `citation_rank` | integer | No | Position in citation list (1, 2, 3, ...) |

#### Response

**Success (201 Created):**
```json
{
  "success": true,
  "message": "Feedback received and will be processed"
}
```

**Error (400 Bad Request):**
```json
{
  "success": false,
  "error": "Missing required field: citation_id"
}
```

**Error (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "Failed to save feedback"
}
```

#### Example

```bash
curl -X POST http://localhost:8001/api/feedback/citation/ \
  -H "Content-Type: application/json" \
  -d '{
    "citation_id": "marketing_doc_001",
    "domain": "marketing",
    "user_id": "emp_123",
    "session_id": "sess_abc",
    "query_text": "What is our brand color?",
    "feedback_type": "like",
    "citation_rank": 1
  }'
```

**Notes:**
- Feedback mentése aszinkron (background thread)
- Duplicate feedback (user + citation + session) felülírja az előzőt
- Stats materialized view auto-refresh (best effort)

---

### GET `/api/feedback/stats/`

**Get aggregated feedback statistics.**

Visszaadja az összesített like/dislike statisztikákat domain-szűréssel. Materialized view-ból olvas (gyors query).

#### Request

**Query Parameters:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `domain` | string | No | Filter by specific domain | `?domain=marketing` |

#### Response

**Success (200 OK):**
```json
{
  "success": true,
  "domain_filter": "marketing",
  "data": {
    "total_feedbacks": 156,
    "like_count": 128,
    "dislike_count": 28,
    "like_ratio": 0.82,
    "by_domain": {
      "marketing": {
        "total": 156,
        "likes": 128,
        "dislikes": 28,
        "like_percentage": 82.05
      }
    },
    "top_liked_citations": [
      {
        "citation_id": "marketing_doc_001",
        "likes": 45,
        "dislikes": 2,
        "like_percentage": 95.74
      }
    ],
    "top_disliked_citations": [
      {
        "citation_id": "marketing_doc_099",
        "likes": 3,
        "dislikes": 12,
        "like_percentage": 20.0
      }
    ]
  }
}
```

**Error (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "Failed to retrieve feedback stats"
}
```

#### Examples

```bash
# All domains
curl http://localhost:8001/api/feedback/stats/

# Marketing only
curl http://localhost:8001/api/feedback/stats/?domain=marketing

# HR only
curl http://localhost:8001/api/feedback/stats/?domain=hr
```

**Notes:**
- Stats frissülnek minden új feedback után (REFRESH MATERIALIZED VIEW)
- Domain filter case-insensitive
- Empty result ha nincs feedback

---

## 🔗 Related Documentation

- [Main README](../README.md)
- [Redis Cache Architecture](REDIS_CACHE.md)
- [Installation Guide](../INSTALLATION.md)
- [Error Handling Architecture](ERROR_HANDLING.md) (coming soon)
- [Google Drive Setup](GOOGLE_DRIVE_SETUP.md)

---

**Last Updated:** December 17, 2025  
**Maintained by:** KnowledgeRouter Team
