# Redis Cache Architecture - KnowledgeRouter

**Verziószám:** 1.0  
**Utolsó frissítés:** 2025-12-17

---

## 🎯 Áttekintés

A KnowledgeRouter Redis cache rendszert használ az OpenAI embedding API hívások és Qdrant keresési eredmények gyorsítótárazására. Ez jelentősen csökkenti a válaszidőt és a költségeket.

**Teljesítmény javulás:**
- ⚡ **32% gyorsabb** válaszidő (cache HIT esetén)
- 💰 **$0.00002 megtakarítás** query-nként
- 🚀 **200ms latency csökkenés** embedding cache HIT-nél

---

## 🏗️ Architektúra

### 4-Rétegű Cache Stratégia

```
┌─────────────────────────────────────────────────────────┐
│                    User Query                           │
│            "Mi a brand guideline?"                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │   Layer 1: Query Cache     │  🚀 FASTEST (512ms)
        │   Key: query:hash:domain   │
        │   TTL: 24 hours            │
        └────────┬───────────────────┘
                 │
            HIT? │ YES → Fetch by doc IDs (Qdrant)
                 │
                 │ NO
                 ▼
        ┌────────────────────────────┐
        │  Layer 2: Embedding Cache  │  ⚡ FAST (52ms)
        │  Key: embedding:hash       │
        │  TTL: 7 days               │
        └────────┬───────────────────┘
                 │
            HIT? │ YES → Skip OpenAI call
                 │
                 │ NO
                 ▼
        ┌────────────────────────────┐
        │   OpenAI Embedding API     │  ⏱️ BASELINE (250ms)
        │   $0.00002 / 1k tokens     │
        └────────┬───────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │  Layer 3: Qdrant Search    │
        │  Semantic Similarity       │
        └────────┬───────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │  Layer 4: Cache Results    │  💾 Store for next time
        │  embedding + query result  │
        └────────────────────────────┘
```

---

## 📦 Cache Típusok

### 1. Embedding Cache

**Cél:** OpenAI API hívások gyorsítása

**Konfiguráció:**
```python
TTL: 7 nap (604800 másodperc)
Size: ~6KB per embedding (1536 float32)
Max Keys: ~85,000 (512MB / 6KB)
Eviction: LRU (Least Recently Used)
```

**Key formátum:**
```
embedding:{SHA256_HASH_OF_QUERY}
```

**Példa:**
```python
# Query: "Mi a brand guideline?"
# Hash: sha256("Mi a brand guideline?")[:16] = "f3a2b1c4d5e6f7g8"
# Key: "embedding:f3a2b1c4d5e6f7g8"
# Value: [0.123, -0.456, ..., 0.789]  # 1536 floats
```

**Költségmegtakarítás:**
```
1 cache HIT = $0.00002 megtakarítás + 200ms latency csökkenés
1000 HIT/nap = $0.02/nap = ~$7.30/év
```

### 2. Query Result Cache

**Cél:** Qdrant keresés eredményeinek gyorsítása

**Konfiguráció:**
```python
TTL: 24 óra (86400 másodperc)
Size: ~200 bytes per query (csak doc IDs)
Max Keys: ~2.5 millió (512MB / 200B)
Eviction: LRU
```

**Key formátum:**
```
query:{SHA256_HASH}:{DOMAIN}
```

**Példa:**
```python
# Query: "Mi a brand guideline?", Domain: marketing
# Hash: "f3a2b1c4d5e6f7g8"
# Key: "query:f3a2b1c4d5e6f7g8:marketing"
# Value: {
#   "doc_ids": [123, 456, 789],
#   "metadata": {"count": 3, "cached_at": "2025-12-17T10:30:00Z"}
# }
```

**Cache HIT flow:**
```python
# 1. Check cache
cached_result = redis_cache.get_query_result(query, domain)

# 2. Fetch by IDs (Qdrant retrieve)
points = qdrant_client.retrieve(
    collection_name="multi_domain_kb",
    ids=cached_result["doc_ids"],  # [123, 456, 789]
    with_payload=True
)

# 3. Return citations (512ms total vs. 750ms MISS)
```

### 3. Hit Counter Cache

**Cél:** Query népszerűség tracking

**Konfiguráció:**
```python
TTL: Végtelen (nem jár le)
Type: Redis HASH
Size: ~50 bytes per query
```

**Key formátum:**
```
query_hits:{SHA256_HASH}:{DOMAIN}
```

**Tracking logika:**
```python
# Minden cache HIT-nél
redis_client.hincrby(f"query_hits:{hash}:{domain}", "hits", 1)
redis_client.hset(f"query_hits:{hash}:{domain}", "query", query[:100])
redis_client.hset(f"query_hits:{hash}:{domain}", "last_access", timestamp)
```

**Top queries API:**
```bash
GET /api/cache-stats/
→ Top 10 query based on hit count
```

---

## 🔧 Konfiguráció

### Docker Compose

```yaml
redis:
  image: redis:7-alpine
  container_name: knowledgerouter_redis
  ports:
    - "6380:6379"  # 6379 ütközött local Redis-szel
  volumes:
    - redis_data:/data
  command: >
    redis-server
    --appendonly yes              # AOF persistence
    --maxmemory 512mb            # Max RAM
    --maxmemory-policy allkeys-lru  # Eviction strategy
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 3s
    retries: 3
```

### Backend Environment

```bash
REDIS_HOST=redis
REDIS_PORT=6379
```

### Eviction Policy

**allkeys-lru (Least Recently Used):**
- Törli a legrégebben használt kulcsokat
- Hatékony embedding/query cache-hez
- Automatikus memory management

**Alternatívák:**
- `volatile-lru`: Csak TTL-lel rendelkező kulcsok
- `allkeys-lfu`: Legritkábban használt (frequency)
- `noeviction`: Hibát dob ha megtelt (nem ajánlott)

---

## 🔄 Cache Invalidálás

### Automatikus Invalidálás

**Dokumentum frissítés után:**
```bash
# sync_domain_docs.py automatikusan invalidálja a cache-t
python backend/scripts/sync_domain_docs.py --domain marketing --folder-id FOLDER_ID

# Output:
# ✅ Success: 3 files
# 🗑️ Redis cache invalidated for domain: marketing
```

**Implementáció:**
```python
# backend/scripts/sync_domain_docs.py (sor 318-323)
if redis_cache.is_available():
    redis_cache.invalidate_query_cache(domain=self.domain)
    logger.info(f"🗑️ Redis cache invalidated for domain: {self.domain}")
```

### Manuális Invalidálás

**Domain-specifikus törlés:**
```bash
curl -X DELETE "http://localhost:8001/api/cache-stats/?domain=marketing"
```

**Teljes cache törlés:**
```bash
curl -X DELETE "http://localhost:8001/api/cache-stats/"
```

**Python client:**
```python
from infrastructure.redis_client import redis_cache

# Domain cache invalidálás
redis_cache.invalidate_query_cache(domain="marketing")

# Minden törlése (óvatosan!)
redis_cache.clear_all()
```

---

## 📊 Monitoring

### Cache Stats Endpoint

```bash
GET /api/cache-stats/
```

**Response:**
```json
{
  "success": true,
  "data": {
    "stats": {
      "connected": true,
      "used_memory_mb": 45.2,
      "total_keys": 1234,
      "hit_rate": 0.68,
      "embedding_keys": 890,
      "query_keys": 344,
      "uptime_hours": 24.5
    },
    "top_queries": [
      {
        "query": "Mi a brand guideline?",
        "domain": "marketing",
        "hits": 45,
        "cached_at": "2025-12-17T10:30:15Z"
      }
    ]
  }
}
```

### Metrikák Magyarázata

| Metrika | Jelentés | Optimális Érték |
|---------|----------|-----------------|
| **hit_rate** | Cache találati arány | > 0.60 (60%) |
| **used_memory_mb** | Használt memória | < 450 MB |
| **total_keys** | Összes cache kulcs | Folyamatosan nő |
| **embedding_keys** | Embedding cache | 80-90% total keys |
| **query_keys** | Query result cache | 10-20% total keys |
| **connected** | Redis kapcsolat | `true` ✅ |

### Alert Thresholds

```python
#警告 (Warning)
if hit_rate < 0.30:
    alert("Low cache hit rate - consider cache warming")

if used_memory_mb > 450:
    info("LRU eviction starting (normal)")

# Critical
if not connected:
    alert("Redis connection lost - degraded mode active")
```

---

## 🧪 Tesztelés

### Cache HIT/MISS Ellenőrzés

**Első query (MISS):**
```bash
curl -X POST http://localhost:8001/api/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "session_id": "test_session",
    "query": "Mi a brand guideline?",
    "domain": "marketing"
  }'

# Backend logs:
# ❌ Embedding cache MISS: Mi a brand guideline?...
# ❌ Query cache MISS
# 💾 Embedding cached: 33.4KB
# 💾 Query result cached: marketing
```

**Második query (HIT):**
```bash
# Ugyanaz a query ismét

# Backend logs:
# ✅ Embedding cache HIT: Mi a brand guideline?...
# 🚀 FULL CACHE HIT - Fetching 5 docs by ID
```

### Performance Test

```python
import time
import requests

url = "http://localhost:8001/api/query/"
payload = {
    "user_id": "perf_test",
    "session_id": "perf_session",
    "query": "Mi a brand guideline?",
    "domain": "marketing"
}

# First call (MISS)
start = time.time()
response1 = requests.post(url, json=payload)
time1 = time.time() - start
print(f"First call (MISS): {time1*1000:.0f}ms")

# Second call (HIT)
start = time.time()
response2 = requests.post(url, json=payload)
time2 = time.time() - start
print(f"Second call (HIT): {time2*1000:.0f}ms")

# Improvement
improvement = (1 - time2/time1) * 100
print(f"Improvement: {improvement:.1f}%")
```

**Várható eredmény:**
```
First call (MISS): 750ms
Second call (HIT): 512ms
Improvement: 31.7%
```

---

## 🛠️ Troubleshooting

### Redis Connection Failed

**Hiba:**
```
⚠️ Redis connection failed: Connection refused. Cache will be disabled.
```

**Megoldás:**
```bash
# Ellenőrizd Redis fut-e
docker-compose ps | grep redis

# Ha nem fut:
docker-compose up -d redis

# Naplók ellenőrzése
docker-compose logs redis
```

### High Memory Usage

**Hiba:**
```
used_memory_mb: 510  # Közel a 512MB limithez
```

**Megoldás:**
```bash
# Opcó 1: Domain cache törlés (kevésbé használt domain)
curl -X DELETE "http://localhost:8001/api/cache-stats/?domain=general"

# Opcó 2: TTL csökkentés (docker-compose.yml)
command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

# Opcó 3: Memory limit növelés
command: redis-server --maxmemory 1024mb --maxmemory-policy allkeys-lru
```

### Low Hit Rate

**Probléma:**
```json
{"hit_rate": 0.15}  // Csak 15%
```

**Okok:**
1. **Változatos query-k**: User minden alkalommal más kérdést tesz fel
2. **Túl rövid TTL**: 24h túl rövid lehet
3. **Gyakori cache invalidálás**: Sok dokumentum update

**Megoldások:**
```python
# 1. Query normalizálás (jövőbeli fejlesztés)
normalized_query = query.lower().strip()

# 2. TTL növelés (óvatosan)
# redis_client.py: set_query_result(..., ttl=172800)  # 48 óra

# 3. Embedding cache warming (top 100 query)
top_queries = redis_cache.get_top_queries(limit=100)
for query in top_queries:
    warmup_cache(query['query'], query['domain'])
```

### Cache Stale Data

**Probléma:**
User régi választ kap frissített dokumentumok után.

**Megoldás:**
```bash
# MINDIG invalidáld a cache-t dokumentum update után
python backend/scripts/sync_domain_docs.py --domain marketing --folder-id FOLDER_ID
# → Automatikusan invalidálja marketing cache-t

# Manuális invalidálás szükség esetén
curl -X DELETE "http://localhost:8001/api/cache-stats/?domain=marketing"
```

---

## 🚀 Jövőbeli Fejlesztések (Roadmap)

### Fázis 2: Like/Dislike Feedback

**Cél:** User feedback alapján smart ranking

**Architektúra:**
```
Postgres (Source of Truth)
    ↓
feedback_cache (Redis, 5 min refresh)
    ↓
query_ranking materialized view
    ↓
Smart re-ranking in query results
```

**Implementáció:**
```python
# POST /api/feedback/
{
  "query": "Mi a brand guideline?",
  "doc_id": "123",
  "feedback": "like",  # or "dislike"
  "user_id": "emp_001"
}

# → Postgres INSERT
# → Redis cache update (feedback score)
# → Next query: Use feedback score for ranking
```

### Fázis 3: Cluster Mode

**Redis Sentinel (HA):**
```yaml
redis-master:
  image: redis:7-alpine
  command: redis-server --appendonly yes

redis-replica-1:
  image: redis:7-alpine
  command: redis-server --replicaof redis-master 6379

redis-sentinel-1:
  image: redis:7-alpine
  command: redis-sentinel /etc/sentinel.conf
```

**Előnyök:**
- Automatic failover
- High availability
- Zero downtime updates

---

## 📚 Kapcsolódó Dokumentumok

- [API.md](./API.md) - Cache-stats endpoint dokumentáció
- [INSTALLATION.md](../INSTALLATION.md) - Redis Docker setup
- [README.md](../README.md) - Projekt áttekintés
- [Redis Official Docs](https://redis.io/docs/)

---

**Utolsó frissítés:** 2025-12-17  
**Verzió:** 1.0  
**Karbantartó:** KnowledgeRouter Team
