# Teaching Memory Lab Implementáció - Teljes Összefoglaló

## Amit Elkészítettünk

Egy átfogó oktatási modul, amely **4 különböző LangGraph memóriakezelési stratégiát** mutat be egymás mellett:

1. **Csúszó Ablak (Rolling Window)** - Teljes üzenethistória token/fordulószám levágással
2. **Összefoglaló Puffer (Summary Buffer)** - Folyamatos összefoglaló agresszív üzenet levágással
3. **Tényalapú Kinyerés (Facts Extraction)** - Strukturált tény tárolás üzenet levágással
4. **Hibrid** - Kombinált összefoglaló + tények + igény szerinti RAG keresés

## Architektúra Áttekintés

```
teaching_memory_lab/
├── state.py              # AppState 6 explicit csatornával (messages, summary, facts, profile, trace, retrieved_context)
├── reducers.py           # Determinisztikus csatorna egyesítési logika konfliktus feloldással
├── router.py             # Feltételes útvonalválasztás memória mód és heurisztikák alapján
├── graph.py              # LangGraph építő, amely összeköti az összes node-ot
├── api.py                # FastAPI végpontok (chat, checkpoints, restore)
├── nodes/                # 6 specializált gráf node
│   ├── answer_node.py           # Végső válasz generálás memória kontextussal
│   ├── summarizer_node.py       # Delta összefoglaló frissítések + üzenet levágás
│   ├── facts_extractor_node.py  # Strukturált tény kinyerés (LLM-alapú)
│   ├── rag_recall_node.py       # Igény szerinti RAG keresés relevancia küszöbbel
│   ├── pii_filter_node.py       # PII maszkolás perzisztencia előtt
│   └── metrics_logger_node.py   # Token/késleltetés követés (JSONL logok)
├── persistence/          # Checkpoint tárolási háttérrendszerek
│   ├── interfaces.py     # ICheckpointStore absztrakt alaposztály
│   ├── file_store.py     # JSON fájl alapú tárolás (egyszerű, átlátható)
│   └── sqlite_store.py   # SQLite alapú tárolás (production szintű indexekkel)
├── utils/                # Segédmodulek
│   ├── token_estimator.py  # Közelítő token számolás (~4 karakter/token)
│   ├── pii_masker.py       # Regex alapú PII detektálás (email, telefon, IBAN, hitelkártya)
│   └── retry.py            # Exponenciális visszalépés külső API hívásokhoz
├── tests/                # Teszt suite (pytest)
│   ├── test_reducers.py     # Determinisztikus egyesítés, deduplikáció
│   ├── test_trimming.py     # Token/fordulószám alapú levágási logika
│   └── test_pii_masker.py   # PII minta detektálás
└── README.md             # Átfogó dokumentáció példákkal
```

## Kulcs Tervezési Elvek

### 1. Csatorna-Alapú Állapot
- **6 explicit csatorna** egyedi reducer-ekkel
- Nincs implicit állapot egyesítés - kiszámítható viselkedés
- Minden csatorna determinisztikus konfliktus feloldással rendelkezik

### 2. Determinisztikus Reducer-ek
```python
messages_reducer()   # Deduplikálás SHA256 hash alapján, rendezés időbélyeg szerint
facts_reducer()      # Utolsó írás nyer időbélyeg döntővel
trace_reducer()      # Hozzáfűzés max_size korláttal (100 bejegyzés)
summary_reducer()    # Csere (verzionált)
```

### 3. Idempotens Műveletek
- Ugyanaz a bemenet mindig ugyanazt a kimenetet produkálja
- Nincsenek versenyhelyzetek elosztott rendszerekben
- Biztonságos újrapróbálkozáshoz és párhuzamos végrehajtáshoz

### 4. Megfigyelhetőség Elsőbbsége
- **Trace csatorna** naplózza minden node végrehajtást
- **Metrika logger** JSONL logokat ír (token számok, késleltetés)
- **Checkpoint visszaállítás** lehetővé teszi az időutazásos debuggolást

## Gráf Végrehajtási Folyamat

### Csúszó Ablak Mód
```
Belépés → metrics_logger → pii_filter → answer → VÉGE
```

### Összefoglaló Mód
```
Belépés → metrics_logger → summarizer → pii_filter → answer → VÉGE
```

### Tények Mód
```
Belépés → metrics_logger → facts_extractor → pii_filter → answer → VÉGE
```

### Hibrid Mód
```
Belépés → metrics_logger → summarizer → facts_extractor → [rag_recall?] → pii_filter → answer → VÉGE
```

**Útvonalválasztási logika:**
- RAG keresés aktiválódik, ha a felhasználói üzenet kulcsszavakat tartalmaz: "remember", "recall", "earlier", "before", "you said"

## API Végpontok

### POST /api/teaching/chat
Fő chat végpont memória mód választással.

**Kérés:**
```json
{
  "session_id": "session_123",
  "user_id": "user_456",
  "message": "Mi a kedvenc színem?",
  "memory_mode": "facts",  // rolling, summary, facts, hybrid
  "pii_mode": "placeholder"  // placeholder, pseudonymize
}
```

**Válasz:**
```json
{
  "response": "A beszélgetésünk alapján a kedvenc színed a kék.",
  "memory_snapshot": {
    "messages_count": 8,
    "facts_count": 3,
    "has_summary": true,
    "summary_version": 2,
    "has_retrieved_context": false,
    "trace_length": 4
  },
  "trace": [
    {"step": "metrics_logger", "action": "logged_metrics", "details": "..."},
    {"step": "facts_extractor", "action": "extracted_facts", "details": "..."}
  ]
}
```

### GET /api/teaching/session/{session_id}/checkpoints
Az összes checkpoint listázása egy munkamenethez (időutazásos debuggolás).

### POST /api/teaching/session/{session_id}/restore/{checkpoint_id}
Munkamenet visszaállítása egy adott checkpoint állapotra.

## Memória Stratégiák Összehasonlítása

| Stratégia | Memória Növekedés | Kontextus Megőrzés | Késleltetés | Legjobb Használat |
|----------|--------------|-------------------|---------|----------|
| **Rolling** | Lineáris (növekszik a beszélgetéssel) | Tökéletes (összes üzenet) | Gyors | Rövid beszélgetések, debuggolás |
| **Summary** | Állandó (összefoglaló + 2 fordulós) | Jó általános kontextushoz | Közepes (1 LLM hívás) | Hosszú beszélgetések |
| **Facts** | Lassú (csak új tények) | Kiváló strukturált adathoz | Közepes (1 LLM hívás) | Felhasználói preferenciák, profilok |
| **Hybrid** | Közepes (összefoglaló + tények + 3 fordulós) | Legjobb összességében | Lassú (2-3 LLM hívás + RAG) | Komplex alkalmazások |

## PII Kezelés

Két mód az érzékeny adatok védelmére:

### Placeholder Mód (alapértelmezett)
```
"Írj emailt ide: janos@pelda.hu" → "Írj emailt ide: [EMAIL]"
"Hívj fel +36-20-123-4567" → "Hívj fel [PHONE]"
```

### Álnévesítés Mód
```
"Írj emailt ide: janos@pelda.hu" → "Írj emailt ide: email_a3f5b9c2d4e5f6..."
```

**Támogatott minták:**
- Email címek (regex: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`)
- Telefonszámok (`+36-20-123-4567`, `06.20.123.4567`)
- IBAN (`HU42117730161111101800000000`)
- Hitelkártyák (`4532-1234-5678-9010`, `4532123456789010`)

## Tesztelés

### Unit Tesztek
```bash
cd backend/teaching_memory_lab
pytest tests/ -v
```

**Teszt lefedettség:**
- `test_reducers.py` - Determinisztikus egyesítés, deduplikáció, ID generálás
- `test_trimming.py` - Token/fordulószám alapú levágás, rendszerüzenet megőrzés
- `test_pii_masker.py` - PII minta detektálás, placeholder/álnévesítés módok

### Integrációs Teszt Szkript
```bash
./test_teaching_lab.sh
```

Mind a 4 memória módot teszteli minta beszélgetésekkel.

## Hozzáadott Függőségek

```
langchain-chroma==0.1.0  # RAG recall node-hoz
aiosqlite==0.19.0        # SQLite checkpoint store-hoz
pytest==7.4.3            # Teszteléshez
pytest-asyncio==0.21.1   # Async tesztekhez
```

## Integráció a Főalkalmazással

Az oktatási modul **elszigetelt** a production kódtól:
- Külön `/api/teaching/*` végpontok
- Saját checkpoint tárolás (`data/teaching_checkpoints/`)
- Saját metrika logok (`data/teaching_metrics/`)
- Nincs hatással a meglévő chat szolgáltatásra

**Hozzáadva a main.py-hoz:**
```python
from teaching_memory_lab.api import router as teaching_router
app.include_router(teaching_router)
```

## Mit Figyeljünk Meg

Különböző memória módok tesztelésekor:

### 1. Memóriahasználat
- Rolling: Ellenőrizd az üzenetszám növekedést (nincs limit)
- Summary: Ellenőrizd az összefoglaló verzió növekedést, üzenetszám ~2-4 marad
- Facts: Ellenőrizd a tények számának növekedését (csak egyedi kulcsok)
- Hybrid: Ellenőrizd mind a hármat + retrieved_context

### 2. Kontextus Megőrzés
- Kérdezd: "Mit mondtam neked 10 fordulóval ezelőtt?"
- Rolling: Pontosan emlékezni kell
- Summary: Az általános témára emlékezni kell
- Facts: Ha tény volt, emlékezni kell rá
- Hybrid: Legjobb emlékezés minden szcenárióban

### 3. Token Használat
- Ellenőrizd a metrika logokat: `data/teaching_metrics/session_{id}.jsonl`
- Hasonlítsd össze a total_tokens-t különböző módokban ugyanarra a beszélgetésre

### 4. Késleltetés
- Ellenőrizd a trace bejegyzéseket a node végrehajtási időkért
- Summary/Facts: +1 LLM hívás overhead
- Hybrid: +2-3 LLM hívás + RAG lekérdezés

### 5. Válasz Minőség
- Tesztelj 20+ fordulós beszélgetéssel
- Hasonlítsd össze, hogyan kezeli minden mód a hosszú távú kontextust

## Példa Munkafolyamatok

### Tény Perzisztencia Tesztelése
```bash
# 1. forduló: Preferencia beállítása
curl -X POST http://localhost:8000/api/teaching/chat \
  -d '{"session_id": "teszt", "user_id": "user1", "message": "A sötét módot preferálom", "memory_mode": "facts"}'

# 2. forduló: Preferencia frissítése (felül kellene írnia)
curl -X POST http://localhost:8000/api/teaching/chat \
  -d '{"session_id": "teszt", "user_id": "user1", "message": "Valójában a világos módot preferálom", "memory_mode": "facts"}'

# 3. forduló: Visszakeresés (a legutóbbit kellene használnia)
curl -X POST http://localhost:8000/api/teaching/chat \
  -d '{"session_id": "teszt", "user_id": "user1", "message": "Melyik módot preferálom?", "memory_mode": "facts"}'
```

### Összefoglaló Delta Frissítések Tesztelése
```bash
# Beszélgetés felépítése
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/teaching/chat \
    -d "{\"session_id\": \"osszefoglalo_teszt\", \"user_id\": \"user1\", \"message\": \"Téma $i információ\", \"memory_mode\": \"summary\"}"
done

# Összefoglaló verzió és üzenetszám ellenőrzése
curl -X GET http://localhost:8000/api/teaching/session/osszefoglalo_teszt/checkpoints?user_id=user1 | jq '.[0].metadata'
```

### RAG Visszakeresés Tesztelése Hibrid Módban
```bash
# Először tölts fel egy dokumentumot
curl -X POST http://localhost:8000/api/rag/upload \
  -F "file=@teszt_dokumentum.txt" \
  -F "user_id=user1"

# Chat hibrid móddal + hivatkozási kulcsszó
curl -X POST http://localhost:8000/api/teaching/chat \
  -d '{"session_id": "hibrid_teszt", "user_id": "user1", "message": "Emlékszel mit mondott a dokumentum a LangGraph-ról?", "memory_mode": "hybrid"}'
```

## Létrehozott Fájlok (Összesen: 23 fájl)

1. `state.py` - 7 Pydantic modell (Message, Fact, Summary, stb.)
2. `reducers.py` - 7 reducer függvény + levágási segédprogramok
3. `router.py` - 6 útvonalválasztó függvény
4. `graph.py` - LangGraph építő
5. `api.py` - FastAPI router 3 végponttal
6. `nodes/answer_node.py` - Végső válasz generálás
7. `nodes/summarizer_node.py` - Delta összefoglaló frissítések
8. `nodes/facts_extractor_node.py` - Strukturált tény kinyerés
9. `nodes/rag_recall_node.py` - Igény szerinti RAG keresés
10. `nodes/pii_filter_node.py` - PII maszkolás
11. `nodes/metrics_logger_node.py` - Megfigyelhetőség
12. `persistence/interfaces.py` - ICheckpointStore interfész
13. `persistence/file_store.py` - JSON fájl alapú tárolás
14. `persistence/sqlite_store.py` - SQLite tárolás
15. `utils/token_estimator.py` - Token számolás
16. `utils/pii_masker.py` - PII detektálás/maszkolás
17. `utils/retry.py` - Exponenciális visszalépés
18. `tests/test_reducers.py` - Reducer tesztek
19. `tests/test_trimming.py` - Levágási tesztek
20. `tests/test_pii_masker.py` - PII maszkolási tesztek
21. `README.md` - Átfogó dokumentáció
22. `__init__.py` fájlok (több)
23. `test_teaching_lab.sh` - Integrációs teszt szkript

## Sorszám Összefoglaló

- **Összes sor:** ~2,800+ sor kód
- **State/Reducers:** ~300 sor
- **Node-ok:** ~600 sor
- **Perzisztencia:** ~400 sor
- **Segédprogramok:** ~200 sor
- **Tesztek:** ~400 sor
- **API:** ~250 sor
- **Dokumentáció:** ~650 sor

## Tanulási Eredmények

Ez a modul bemutatja:

1. **LangGraph állapotkezelés** - Csatorna-alapú egyedi reducer-ekkel
2. **Determinisztikus rendszerek** - Konfliktus-mentes egyesítés, idempotens műveletek
3. **Memória kompromisszumok** - Nincs tökéletes megoldás, kontextusfüggő
4. **Megfigyelhetőségi minták** - Trace-ek, metrikák, checkpoint-ok
5. **PII kezelés** - Adatvédelmi szempontok AI rendszerekben
6. **Tesztelési stratégiák** - Unit tesztek determinisztikus logikához
7. **Clean architektúra** - Felelősségek szétválasztása, SOLID elvek

## Következő Lépések Kísérletezéshez

1. **Egyedi memória stratégia hozzáadása** - Prioritás-alapú megőrzés implementálása
2. **RAG keresés fejlesztése** - Szemantikus hasonlóság küszöb finomhangolás hozzáadása
3. **Teljesítmény benchmark** - Késleltetés/token-ek összehasonlítása 100 fordulós beszélgetésekben
4. **Memória evolúció vizualizálása** - Üzenetszám, token használat ábrázolása idővel
5. **A/B tesztelés** - Válasz minőség összehasonlítása stratégiák között
6. **Több felhasználós szcenáriók** - Bérlő izoláció tesztelése checkpoint-okban
7. **Egyedi reducer-ek** - Domain-specifikus egyesítési logika implementálása

## Production Megfontolások

Ez egy **oktatási modul** - production használathoz fontold meg:

- **Elosztott checkpointing** - Redis/PostgreSQL használata fájlok helyett
- **Aszinkron LLM hívások** - Összefoglaló + tény kinyerés párhuzamosítása
- **Gyorsítótárazás** - Embedding-ek, összefoglalók gyorsítótárazása
- **Rate limiting** - Védelem visszaélés ellen
- **Monitoring** - Prometheus metrikák, elosztott tracing
- **Hibakezelés** - Circuit breaker-ek külső API-khoz
- **Skálázás** - Külön RAG szolgáltatás, terheléselosztás

## Következtetés

A Teaching Memory Lab egy **átfogó, gyakorlatorientált bemutatót** nyújt a LangGraph memóriakezelési mintákról. Mind a 4 stratégia production szintű kódminőséggel, kiterjedt dokumentációval és teszt lefedettséggel van implementálva. A modul teljesen integrált a főalkalmazásba, de elszigetelt, hogy ne zavarja a meglévő funkcionalitást.

**A diákok/fejlesztők tudnak:**
- Stratégiákat összehasonlítani egymás mellett
- Checkpoint-okat bármely ponton megvizsgálni
- Metrikákat és trace-eket elemezni
- Kódot módosítani és bővíteni
- Teszteket futtatni a viselkedés ellenőrzéséhez

Ez egy teljes referencia implementáció a LangGraph memóriakezeléshez.
