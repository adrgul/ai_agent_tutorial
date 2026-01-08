# MCP Szerver Használat az Alkalmazásban

## Áttekintés

Az **MCP (Model Context Protocol)** egy nyílt protokoll, amely lehetővé teszi az AI ágensek számára, hogy külső eszközökhöz és adatforrásokhoz kapcsolódjanak. Ez az útmutató bemutatja, hogyan integráltuk az MCP szervereket az alkalmazásunkba.

## Mi az az MCP?

A Model Context Protocol (MCP) egy szabványosított módszer arra, hogy:
- AI ágensek külső szolgáltatásokhoz kapcsolódjanak
- Eszközök dinamikusan felfedezhetők és hívhatók legyenek
- Különböző adatforrások egységesen elérhetők legyenek
- Biztonságos kommunikáció valósuljon meg az ágens és a külső szolgáltatások között

## Jelenlegi MCP Szerverek

Az alkalmazásunk két MCP szervert használ:

### 1. AlphaVantage MCP Szerver
- **URL**: `https://mcp.alphavantage.co/mcp?apikey=5BBQJA8GEYVQ228V`
- **Cél**: Pénzügyi és valuta információk lekérése
- **Eszközök**: Valuta árfolyamok, kriptovaluta árak, tőzsdei adatok
- **Használat**: Amikor a felhasználó pénzügyi adatokat kér

### 2. DeepWiki MCP Szerver
- **URL**: `https://mcp.deepwiki.com/mcp`
- **Cél**: Tudásbázis lekérdezések
- **Eszközök**: `ask_question`, `read_wiki_structure`
- **Használat**: Amikor a felhasználó általános tudást igénylő kérdést tesz fel

## MCP Kliens Architektúra

### Fájlstruktúra

```
backend/
├── infrastructure/
│   └── tool_clients.py          # MCPClient implementáció
├── services/
│   ├── agent.py                 # MCP eszközök fetching
│   └── chat_service.py          # MCP eredmények kezelése
└── domain/
    ├── interfaces.py            # IMCPClient interfész
    └── models.py                # MCP-hez kapcsolódó modellek
```

### MCPClient Osztály

```python
class MCPClient(IMCPClient):
    """
    Alap MCP kliens implementáció.
    HTTP-alapú MCP szerverekhez kapcsolódik REST API-n keresztül.
    """
    
    def __init__(self):
        self.server_url: Optional[str] = None
        self.connected: bool = False
    
    async def connect(self, server_url: str) -> None:
        """Kapcsolódás HTTP-alapú MCP szerverhez."""
        
    async def list_tools(self) -> list:
        """Elérhető eszközök listázása az MCP szerverről."""
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Eszköz meghívása az MCP szerveren."""
```

## MCP Kommunikáció Lépései

### 1. Inicializálás (Alkalmazás Indítása)

Az alkalmazás indulásakor két MCP kliens példány jön létre:

```python
# backend/main.py
mcp_client = MCPClient()  # DeepWiki-hez
alphavantage_mcp_client = MCPClient()  # AlphaVantage-hez

# Átadás az ágensnek
agent = AIAgent(
    # ... egyéb paraméterek
    mcp_client=mcp_client,
    alphavantage_mcp_client=alphavantage_mcp_client
)
```

**Debug napló:**
```
2026-01-08 12:55:03,803 - main - INFO - Initialized MCP client for DeepWiki
2026-01-08 12:55:03,803 - main - INFO - Initialized MCP client for AlphaVantage
```

### 2. Felhasználói Üzenet Fogadása

Amikor egy felhasználói üzenet érkezik, az ágens munkafolyamat elindul:

```
Felhasználó → FastAPI Endpoint → ChatService → AIAgent
```

### 3. RAG Pipeline Végrehajtása

Az MCP eszközök fetchelése **előtt** a RAG (Retrieval-Augmented Generation) pipeline fut le:

```python
# Workflow sorrend:
1. RAG QueryRewrite node
2. RAG Retrieve node  
3. RAG ContextBuilder node
4. RAG Guardrail node
5. RAG Feedback node
```

**Debug napló:**
```
2026-01-08 13:02:43,547 - rag.rag_nodes - INFO - RAG QueryRewrite node executing
2026-01-08 13:02:45,700 - rag.rag_nodes - INFO - Query rewritten in 2152.41ms
2026-01-08 13:02:47,041 - rag.rag_nodes - INFO - RAG pipeline completed: 0 chunks, 3485.09ms total
```

### 4. AlphaVantage Eszközök Fetchelése

A RAG után **első lépésként** az AlphaVantage eszközök kerülnek fetchelésre:

```python
async def _fetch_alphavantage_tools_node(self, state: AgentState) -> AgentState:
    """AlphaVantage MCP szerverről eszközök lekérése."""
    
    # 1. Debug log hozzáadása
    state["debug_logs"].append("[MCP] Starting AlphaVantage MCP server connection...")
    
    # 2. Kapcsolódás ellenőrzése
    if not self.alphavantage_mcp_client.connected:
        state["debug_logs"].append("[MCP] Connecting to AlphaVantage server...")
        await self.alphavantage_mcp_client.connect(
            "https://mcp.alphavantage.co/mcp?apikey=5BBQJA8GEYVQ228V"
        )
        state["debug_logs"].append("[MCP] ✓ Connected to AlphaVantage MCP server")
    
    # 3. Eszközök listázása
    state["debug_logs"].append("[MCP] Fetching available tools from AlphaVantage...")
    alphavantage_tools = await self.alphavantage_mcp_client.list_tools()
    
    # 4. Eredmény tárolása
    tool_names = [tool.get("name", "unknown") for tool in alphavantage_tools]
    state["debug_logs"].append(
        f"[MCP] ✓ Fetched {len(alphavantage_tools)} tools: {', '.join(tool_names)}"
    )
    state["alphavantage_tools"] = alphavantage_tools
    
    return state
```

**Debug napló sikeres esetben:**
```
[MCP] Starting AlphaVantage MCP server connection...
[MCP] Connecting to AlphaVantage server (https://mcp.alphavantage.co/mcp)...
[MCP] ✓ Connected to AlphaVantage MCP server
[MCP] Fetching available tools from AlphaVantage...
[MCP] ✓ Fetched 5 tools from AlphaVantage: currency_exchange, crypto_price, stock_quote, ...
```

**Debug napló hiba esetén:**
```
[MCP] Starting AlphaVantage MCP server connection...
[MCP] Connecting to AlphaVantage server...
[MCP] ✗ Connection failed: HTTP 404 Not Found
```

### 5. DeepWiki Eszközök Fetchelése

AlphaVantage után **második lépésként** a DeepWiki eszközök:

```python
async def _fetch_deepwiki_tools_node(self, state: AgentState) -> AgentState:
    """DeepWiki MCP szerverről eszközök lekérése."""
    
    # Hasonló folyamat, mint AlphaVantage-nél
    state["debug_logs"].append("[MCP] Starting DeepWiki MCP server connection...")
    
    # Kapcsolódás és eszközök fetchelése
    # ...
    
    state["deepwiki_tools"] = deepwiki_tools
    return state
```

**Jelenlegi probléma:**
```
2026-01-08 13:02:48,266 - httpx - INFO - HTTP Request: POST https://mcp.deepwiki.com/mcp/list_tools "HTTP/1.1 404 Not Found"
2026-01-08 13:02:48,423 - services.agent - ERROR - Error fetching DeepWiki tools: Client error '404 Not Found'
```

### 6. Ágens Döntéshozatal

Az eszközök fetchelése után az ágens döntést hoz:

```python
async def _agent_decide_node(self, state: AgentState) -> AgentState:
    """
    Ágens dönt a következő lépésről.
    Elérhető eszközök:
    - Beépített eszközök (weather, crypto_price, fx_rates, stb.)
    - AlphaVantage MCP eszközök (state["alphavantage_tools"])
    - DeepWiki MCP eszközök (state["deepwiki_tools"])
    """
    
    # LLM meghívása az összes elérhető eszközzel
    response = await self.llm.ainvoke(state["messages"])
    
    # Döntés: eszközt hív vagy végső választ ad
    if response.tool_calls:
        return {"next_action": "call_tool"}
    else:
        return {"next_action": "final_answer"}
```

### 7. MCP Eszköz Meghívása

Ha az LLM MCP eszközt választ:

```python
# Példa: DeepWiki ask_question eszköz meghívása
tool_result = await mcp_client.call_tool(
    name="ask_question",
    arguments={"question": "Mi az időjárás Budapesten?"}
)
```

**HTTP kérés:**
```
POST https://mcp.deepwiki.com/mcp/call_tool
Content-Type: application/json

{
    "name": "ask_question",
    "arguments": {
        "question": "Mi az időjárás Budapesten?"
    }
}
```

## MCP Kliens Implementáció Részletei

### HTTP Transport

Az MCPClient HTTP POST kéréseket használ:

```python
async def list_tools(self) -> list:
    """Eszközök listázása HTTP-n keresztül."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{self.server_url}/list_tools",
            json={}
        )
        response.raise_for_status()
        result = response.json()
        
        tools = result.get('tools', []) if isinstance(result, dict) else []
        
        return [{
            "name": tool.get('name', ''),
            "description": tool.get('description', ''),
            "inputSchema": tool.get('inputSchema', {})
        } for tool in tools]
```

### Hibakezelés

```python
try:
    await mcp_client.connect(server_url)
    tools = await mcp_client.list_tools()
except ConnectionError as e:
    logger.error(f"MCP kapcsolódási hiba: {e}")
    state["debug_logs"].append(f"[MCP] ✗ Connection failed: {str(e)}")
except Exception as e:
    logger.error(f"MCP hiba: {e}")
    state["debug_logs"].append(f"[MCP] ✗ Error: {str(e)}")
```

## Debug Panel Integráció

A frontend-en a debug panel megjeleníti az MCP lépéseket:

```typescript
// Frontend: DebugPanel.tsx
{debugLogs && debugLogs.length > 0 && (
  <div className="debug-section">
    <h4>🔗 MCP Steps</h4>
    <div className="mcp-steps">
      {debugLogs.map((log, idx) => (
        <div key={idx} className="mcp-step">
          {log}
        </div>
      ))}
    </div>
  </div>
)}
```

**Megjelenített példa:**
```
🔗 MCP Steps
[MCP] Starting AlphaVantage MCP server connection...
[MCP] Connecting to AlphaVantage server (https://mcp.alphavantage.co/mcp)...
[MCP] ✓ Connected to AlphaVantage MCP server
[MCP] Fetching available tools from AlphaVantage...
[MCP] ✓ Fetched 5 tools from AlphaVantage: currency_exchange, stock_quote, ...
[MCP] Starting DeepWiki MCP server connection...
[MCP] Connecting to DeepWiki server (https://mcp.deepwiki.com/mcp)...
[MCP] ✗ Connection failed: Client error '404 Not Found'
```

## Jelenlegi Problémák és Megoldások

### Probléma 1: URL Formázás

**Hiba:**
```
POST https://mcp.alphavantage.co/mcp?apikey=5BBQJA8GEYVQ228V/list_tools
HTTP 202 Accepted (üres válasz)
```

**Ok:** Az MCPClient a szerver URL-hez hozzáfűzi a `/list_tools` végpontot, ami hibás URL-t eredményez.

**Megoldás:** Az MCP szerverek valószínűleg más protokollt vagy endpoint struktúrát használnak. Szükséges:
1. Az MCP protokoll specifikáció áttekintése
2. A helyes endpoint formátum meghatározása
3. A szerverek dokumentációjának ellenőrzése

### Probléma 2: HTTP vs SSE/WebSocket

**Ok:** Az MCP protokoll támogathat:
- HTTP/REST API-t
- Server-Sent Events (SSE)-t
- WebSocket-et
- stdio alapú kommunikációt

**Jelenlegi implementáció:** Csak HTTP POST kéréseket használ

**Lehetséges megoldás:**
```python
# SSE-alapú implementáció példa
async def list_tools_sse(self) -> list:
    """Eszközök listázása SSE-n keresztül."""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET",
            f"{self.server_url}/list_tools"
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    # Feldolgozás...
```

## LangGraph Workflow Integrációja

```python
def _build_graph(self) -> StateGraph:
    """LangGraph workflow építése MCP eszköz fetcheléssel."""
    
    workflow = StateGraph(AgentState)
    
    # RAG csomópontok
    workflow.add_node("rag_pipeline", self.rag_graph)
    
    # MCP eszköz fetchelés - FONTOS SORREND!
    workflow.add_node("fetch_alphavantage_tools", self._fetch_alphavantage_tools_node)
    workflow.add_node("fetch_deepwiki_tools", self._fetch_deepwiki_tools_node)
    
    # Ágens csomópontok
    workflow.add_node("agent_decide", self._agent_decide_node)
    workflow.add_node("agent_finalize", self._agent_finalize_node)
    
    # Eszköz csomópontok
    for tool_name in self.tools.keys():
        workflow.add_node(f"tool_{tool_name}", self._create_tool_node(tool_name))
    
    # WORKFLOW SORREND:
    workflow.set_entry_point("rag_pipeline")
    workflow.add_edge("rag_pipeline", "fetch_alphavantage_tools")  # 1. AlphaVantage
    workflow.add_edge("fetch_alphavantage_tools", "fetch_deepwiki_tools")  # 2. DeepWiki
    workflow.add_edge("fetch_deepwiki_tools", "agent_decide")  # 3. Döntés
    
    # Feltételes routing
    workflow.add_conditional_edges(
        "agent_decide",
        self._route_decision,
        {
            "call_tool": "execute_tool",
            "final_answer": "agent_finalize"
        }
    )
    
    return workflow.compile()
```

## MCP Szerver Tesztelés

### Manuális Tesztelés cURL-lel

```bash
# AlphaVantage MCP szerver tesztelése
curl -X POST https://mcp.alphavantage.co/mcp/list_tools \
  -H "Content-Type: application/json" \
  -d '{}'

# DeepWiki MCP szerver tesztelése
curl -X POST https://mcp.deepwiki.com/mcp/list_tools \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Docker Logok Ellenőrzése

```bash
# MCP kapcsolódási logok
docker logs ai-agent-backend | grep -i "mcp"

# Hibák szűrése
docker logs ai-agent-backend | grep -i "mcp.*error"

# AlphaVantage specifikus logok
docker logs ai-agent-backend | grep -i "alphavantage"
```

## Legjobb Gyakorlatok

### 1. Kapcsolat Újrafelhasználása

```python
class MCPClient:
    def __init__(self):
        self.server_url = None
        self.connected = False
        self._session = None  # Újrafelhasználható session
    
    async def connect(self, server_url: str):
        if self._session is None:
            self._session = httpx.AsyncClient(timeout=10.0)
        # ...
```

### 2. Timeout Kezelése

```python
async def list_tools(self) -> list:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(...)
            # ...
    except httpx.TimeoutException:
        logger.error("MCP szerver timeout")
        return []
```

### 3. Retry Logika

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def list_tools_with_retry(self) -> list:
    return await self.list_tools()
```

### 4. Caching

```python
class MCPClient:
    def __init__(self):
        self._tools_cache = {}
        self._cache_ttl = 300  # 5 perc
    
    async def list_tools(self) -> list:
        cache_key = self.server_url
        
        if cache_key in self._tools_cache:
            cached_time, tools = self._tools_cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                return tools
        
        # Friss lekérés
        tools = await self._fetch_tools()
        self._tools_cache[cache_key] = (time.time(), tools)
        return tools
```

## Troubleshooting

### MCP Eszközök Nem Jelennek Meg

**Ellenőrzés:**
1. Backend logok: `docker logs ai-agent-backend | grep MCP`
2. Debug panel a frontend-en
3. Hálózati kérések: Browser DevTools → Network

**Lehetséges okok:**
- MCP szerver nem elérhető
- Hibás endpoint URL
- Timeout
- Hibás autentikáció (API key)

### "NoneType object has no attribute 'append'" Hiba

**Ok:** `debug_logs` nincs inicializálva az állapotban

**Megoldás:**
```python
# agent.py - run() metódusban
initial_state: AgentState = {
    "messages": [HumanMessage(content=user_message)],
    "memory": memory,
    "tools_called": [],
    "debug_logs": [],  # ← Ez hiányzott!
    # ...
}
```

### HTTP 202 Válasz Üres Body-val

**Ok:** A szerver aszinkron feldolgozást jelezhet

**Megoldás:**
1. Polling mechanizmus implementálása
2. WebSocket vagy SSE használata
3. Szerver dokumentáció ellenőrzése

## További Fejlesztési Lehetőségek

### 1. MCP Szerver Registry

```python
class MCPRegistry:
    """Központi MCP szerver registry."""
    
    def __init__(self):
        self.servers = {
            "alphavantage": {
                "url": "https://mcp.alphavantage.co/mcp",
                "api_key": "5BBQJA8GEYVQ228V",
                "capabilities": ["currency", "stocks", "crypto"]
            },
            "deepwiki": {
                "url": "https://mcp.deepwiki.com/mcp",
                "capabilities": ["knowledge", "qa"]
            }
        }
    
    def get_server(self, name: str) -> dict:
        return self.servers.get(name)
```

### 2. Dinamikus Eszköz Binding

```python
async def bind_mcp_tools_to_llm(self):
    """MCP eszközök dinamikus bindolása az LLM-hez."""
    
    all_tools = []
    
    # Beépített eszközök
    all_tools.extend(self.builtin_tools)
    
    # MCP eszközök hozzáadása
    for tool in state["alphavantage_tools"]:
        all_tools.append(self._convert_mcp_tool(tool))
    
    for tool in state["deepwiki_tools"]:
        all_tools.append(self._convert_mcp_tool(tool))
    
    # LLM bindolás
    self.llm = self.llm.bind_tools(all_tools)
```

### 3. MCP Health Check

```python
async def check_mcp_health(self) -> Dict[str, bool]:
    """MCP szerverek állapotának ellenőrzése."""
    
    health = {}
    
    for name, client in [
        ("alphavantage", self.alphavantage_mcp_client),
        ("deepwiki", self.mcp_client)
    ]:
        try:
            await client.connect(client.server_url)
            await client.list_tools()
            health[name] = True
        except Exception:
            health[name] = False
    
    return health
```

## Kontextus Kezelés MCP Kommunikáció Során

Az alkalmazás **nem küld explicit kontextust** az MCP szervereknek. Az MCP protokoll jelenlegi implementációja **stateless** - minden eszközhívás független egymástól.

### Kontextus Architektúra

```
┌─────────────────────────────────────────────────────────────┐
│  ALKALMAZÁS (Stateful)                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐    ┌──────────────────────┐     │
│  │  Memory (AgentState)  │    │   RAG Context        │     │
│  ├──────────────────────┤    ├──────────────────────┤     │
│  │ • chat_history       │    │ • rewritten_query    │     │
│  │ • user_preferences   │    │ • retrieved_chunks   │     │
│  │ • workflow_state     │    │ • citations          │     │
│  │ • conversation_id    │    │ • context_text       │     │
│  └──────────────────────┘    └──────────────────────┘     │
│           │                            │                    │
│           └────────────┬───────────────┘                    │
│                        ▼                                    │
│              ┌─────────────────┐                           │
│              │  LLM (Claude)   │                           │
│              │  ────────────   │                           │
│              │  Kontextussal   │                           │
│              │  gazdagított    │                           │
│              │  döntéshozatal  │                           │
│              └─────────────────┘                           │
│                        │                                    │
│                        ▼                                    │
│              ┌─────────────────┐                           │
│              │ Eszköz Választás│                           │
│              └─────────────────┘                           │
│                        │                                    │
└────────────────────────┼────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │  MCP SZERVEREK (Stateless)    │
         ├───────────────────────────────┤
         │                               │
         │  call_tool(name, arguments)   │
         │                               │
         │  • NEM kap chat history-t     │
         │  • NEM kap user preferences-t │
         │  • NEM kap session_id-t       │
         │  • CSAK eszköz argumentumok   │
         │                               │
         └───────────────────────────────┘
```

### Kontextus Feldolgozási Flow

#### 1. Kontextus Aggregálás (Agent Decision Node)

```python
async def _agent_decide_node(self, state: AgentState) -> AgentState:
    """
    Ágens döntési csomópont - itt történik a kontextus összegyűjtése.
    """
    
    # 1. MEMÓRIA KONTEXTUS (Felhasználói előzmények)
    recent_history = state["memory"].chat_history[-5:]
    history_context = "\n".join([
        f"{msg.role}: {msg.content[:100]}" 
        for msg in recent_history
    ])
    
    # 2. RAG KONTEXTUS (Feltöltött dokumentumok)
    rag_context = state.get("rag_context", {})
    if rag_context and rag_context.get("has_knowledge"):
        context_text = rag_context.get("context_text", "")
        citations = rag_context.get("citations", [])
        rewritten_query = rag_context.get("rewritten_query", "")
        
        rag_section = f"""
        Retrieved Knowledge:
        {context_text}
        
        Citations: {", ".join(citations)}
        Query: "{rewritten_query}"
        """
    
    # 3. ESZKÖZ HÍVÁSI ELŐZMÉNYEK
    tools_called_info = [
        f"{tc.tool_name}({tc.arguments})"
        for tc in state["tools_called"]
    ]
    
    # 4. RENDSZER PROMPT (Személyiség és szabályok)
    system_prompt = self._build_system_prompt(state["memory"])
    
    # 5. ÖSSZES KONTEXTUS ÁTADÁSA AZ LLM-NEK
    decision_prompt = f"""
    {rag_section}
    
    Conversation history:
    {history_context}
    
    Tools already called: {tools_called_info}
    
    User request: {last_user_msg}
    
    Available tools: [weather, geocode, fx_rates, crypto_price, ...]
    
    Decide: Which tool to call next, or provide final answer?
    """
    
    # LLM DÖNT - KONTEXTUST FIGYELEMBE VÉVE
    llm_response = await self.llm.ainvoke(decision_prompt)
```

**Kulcspont:** A kontextus az **LLM döntéshozatalkor** kerül felhasználásra, **NEM** az MCP eszközhíváskor.

#### 2. MCP Eszköz Hívás (Kontextus Nélkül)

```python
async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP eszköz meghívása - CSAK név és argumentumok küldése.
    
    NINCS kontextus átadás:
    - ❌ Nincs chat_history
    - ❌ Nincs user_id
    - ❌ Nincs session_id
    - ❌ Nincs preferences
    - ✅ CSAK az eszköz specifikus argumentumok
    """
    
    # HTTP POST kérés MCP szerverhez
    response = await client.post(
        f"{self.server_url}/call_tool",
        json={
            "name": name,           # pl. "ask_question"
            "arguments": arguments  # pl. {"question": "What is Python?"}
        }
    )
    
    return response.json()
```

**Példa kérés:**
```json
POST https://mcp.deepwiki.com/mcp/call_tool
{
  "name": "ask_question",
  "arguments": {
    "question": "What is the weather like?"
  }
}
```

**NEM küldött adatok:**
```json
// Ezek NEM mennek az MCP szerverhez:
{
  "user_id": "user_123",
  "session_id": "session_456",
  "chat_history": [...],
  "preferences": {...},
  "previous_tool_calls": [...]
}
```

### Miért Stateless az MCP?

#### Előnyök:

1. **Egyszerűség**
   - MCP szerverek nem tárolnak állapotot
   - Nincs session management
   - Könnyebb skálázás

2. **Biztonság**
   - Minimális adattovábbítás
   - Nincs érzékeny kontextus az MCP szerveren
   - Felhasználói adatok az alkalmazásban maradnak

3. **Univerzalitás**
   - MCP eszközök újrafelhasználhatók különböző alkalmazásokban
   - Nincs alkalmazás-specifikus állapot kezelés
   - Standardizált interfész

#### Hátrányok és Megoldások:

| Probléma | Megoldás az Alkalmazásban |
|----------|---------------------------|
| MCP eszköz nem érti a kontextust | LLM "előfeldolgozza" a kérdést és explicit paramétereket ad át |
| Nincs chat history az MCP-nél | LLM használja a history-t döntéshozatalkor, és kontextualizált argumentumokat küld |
| Nem tudja, ki a felhasználó | Felhasználó-specifikus argumentumokat az LLM generálja (pl. város preferenciából) |
| Nincs emlékezet korábbi hívásokra | AgentState tárolja az összes tool_call-t, LLM látja ezeket |

### Kontextus "Ágyazás" az Argumentumokba

Az LLM **implicit módon beágyazza a kontextust** az eszköz argumentumaiba:

#### Példa 1: Felhasználói Preferencia Használata

```
Felhasználó: "Mi az időjárás?"

┌─────────────────────────────────────────┐
│ Kontextus (AgentState):                 │
│ - user.preferences.default_city = "Budapest" │
│ - memory.chat_history = [...]          │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ LLM Döntés:                             │
│ "User didn't specify city, but their    │
│  default_city is Budapest"              │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ MCP call_tool argumentum:               │
│ {                                       │
│   "name": "weather",                    │
│   "arguments": {                        │
│     "city": "Budapest"  ← Kontextusból! │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
```

#### Példa 2: Chat History Feldolgozás

```
Felhasználó 1: "Mennyi a BTC ára?"
Ágens: "Bitcoin ára: $45,000"

Felhasználó 2: "És az ETH?"

┌─────────────────────────────────────────┐
│ Kontextus:                              │
│ chat_history[-2:] = [                   │
│   "user: Mennyi a BTC ára?",            │
│   "assistant: Bitcoin ára: $45,000",    │
│   "user: És az ETH?"                    │
│ ]                                       │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ LLM Értelmezés:                         │
│ "User is asking about Ethereum price,   │
│  following up on crypto discussion"     │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ MCP call_tool argumentum:               │
│ {                                       │
│   "name": "crypto_price",               │
│   "arguments": {                        │
│     "symbol": "ETH",    ← History-ből!  │
│     "fiat": "USD"                       │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
```

#### Példa 3: RAG Kontextus Integrálás

```
Feltöltött dokumentum: "Q3 report mentions revenue increase"
Felhasználó: "Mennyi volt a bevétel növekedés?"

┌─────────────────────────────────────────┐
│ RAG Kontextus:                          │
│ context_text = "Q3 revenue increased    │
│                 by 23% to $4.2M..."     │
│ citations = ["report.pdf - Q3 Section"] │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ LLM Döntés:                             │
│ "RAG context HAS the answer,            │
│  no tool call needed!"                  │
│                                         │
│ Decision: "final_answer" (not tool call)│
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Válasz (MCP NINCS HÍVVA):               │
│ "A Q3 bevétel 23%-kal nőtt, elérve a   │
│  $4.2M-t [RAG-1]"                       │
│                                         │
│ ⚠️ MCP eszköz NEM lett meghívva, mert   │
│    a RAG kontextus tartalmazta a választ│
└─────────────────────────────────────────┘
```

### Kontextus Prioritási Sorrend

Az LLM döntéshozatalkor **hierarchikus prioritást** követ:

```
1. HIGHEST PRIORITY: RAG Context
   └─> Ha feltöltött dokumentumok tartalmaznak releváns infót
   └─> → "final_answer" (nincs tool call)

2. MEDIUM PRIORITY: Tool Call with Context
   └─> Ha nincs RAG válasz, de van kontextus (history/preferences)
   └─> → Kontextus beágyazása az argumentumokba

3. LOWEST PRIORITY: Direct Tool Call
   └─> Ha nincs kontextus, direkt paraméterek az user üzenetből
   └─> → Explicit argumentumok átadása
```

**Kód példa:**

```python
# Agent decision prompt részlet
decision_prompt = f"""
PRIORITY RULES:

1. If RAG context has the answer → "final_answer" immediately
   {rag_section}  ← HIGHEST PRIORITY

2. If user preferences available → embed in tool arguments
   User's default city: {user.default_city}
   User's language: {user.language}

3. If chat history gives context → interpret and use
   {history_context}

4. Otherwise → use explicit parameters from user message

Current user message: {last_user_msg}
"""
```

### Kontextus Visszavezetés (Tool Result Processing)

Amikor az MCP eszköz válaszol, az eredmény **visszakerül az AgentState-be**:

```python
# Tool execution node
async def _execute_tool_node(self, state: AgentState, tool_name: str):
    """
    Eszköz végrehajtása és eredmény tárolása STATE-ben.
    """
    
    # 1. MCP eszköz meghívása (stateless)
    result = await mcp_client.call_tool(
        name=tool_name,
        arguments=tool_args
    )
    
    # 2. Eredmény tárolása STATE-ben (stateful)
    tool_call_record = ToolCall(
        tool_name=tool_name,
        arguments=tool_args,
        result=result,
        timestamp=datetime.now()
    )
    
    state["tools_called"].append(tool_call_record)
    
    # 3. Eredmény hozzáadása az üzenet history-hoz
    state["messages"].append(ToolMessage(
        content=json.dumps(result),
        tool_call_id=tool_call_id
    ))
    
    # 4. KÖVETKEZŐ DÖNTÉSHOZATAL már látja ezt az eredményt!
    return state
```

**Következő döntésnél:**
```python
# Az előző tool call eredménye már a kontextusban van!
tools_called_info = [
    "crypto_price({'symbol': 'BTC'}) → $45,000",
    "crypto_price({'symbol': 'ETH'}) → $3,200"  ← Előző hívás
]

decision_prompt = f"""
Tools already called: {tools_called_info}

User: "Compare them"

# LLM látja mindkét eredményt, nem kell újra hívni!
"""
```

### Kontextus Perzisztencia

```
┌──────────────────────────────────────────────────────────┐
│  SESSION SZINTŰ PERZISZTENCIA                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  data/sessions/session_123.json:                        │
│  {                                                       │
│    "messages": [                                         │
│      {"role": "user", "content": "Mi az időjárás?"},    │
│      {"role": "tool", "content": "sunny, 25°C"},        │
│      {"role": "assistant", "content": "Napos, 25°C"}    │
│    ],                                                    │
│    "tools_called": [                                     │
│      {"tool_name": "weather", "result": {...}}          │
│    ]                                                     │
│  }                                                       │
│                                                          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  USER SZINTŰ PERZISZTENCIA                               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  data/users/user_123.json:                              │
│  {                                                       │
│    "user_id": "user_123",                               │
│    "language": "hu",                                     │
│    "default_city": "Budapest",                          │
│    "preferences": {                                      │
│      "temperature_unit": "celsius"                       │
│    }                                                     │
│  }                                                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Újra betöltés:**
```python
# Következő user message-nél
user_profile = await user_repo.load(user_id)
session_history = await conversation_repo.load(session_id)

# Kontextus újraépítése
memory = Memory(
    chat_history=session_history.messages,
    preferences=user_profile.preferences
)

# LLM ismét teljes kontextussal rendelkezik!
```

## Összefoglalás

### MCP Workflow az Alkalmazásban

```
1. Alkalmazás indul
   └─> MCP kliensek inicializálása (AlphaVantage, DeepWiki)

2. Felhasználói üzenet érkezik
   └─> ChatService → AIAgent

3. RAG pipeline végrehajtása
   └─> Dokumentumok lekérése (ha vannak)

4. MCP eszközök fetchelése
   ├─> AlphaVantage eszközök lekérése
   └─> DeepWiki eszközök lekérése

5. Ágens döntéshozatal (KONTEXTUSSAL)
   ├─> Memory context (chat_history, preferences)
   ├─> RAG context (retrieved documents)
   ├─> Tool history (már hívott eszközök)
   └─> LLM választ eszközök közül (beépített + MCP)

6. Eszköz végrehajtása (KONTEXTUS NÉLKÜL)
   ├─> Ha beépített eszköz → helyi végrehajtás
   └─> Ha MCP eszköz → MCP call_tool(name, args)
       ⚠️ CSAK név és argumentumok, NINCS kontextus!

7. Eredmény visszavezetés (KONTEXTUSBA)
   └─> Tool result tárolása AgentState-ben
   └─> Következő döntés látja az eredményt

8. Válasz generálása
   └─> Végső válasz a felhasználónak
```

### Kulcsfontosságú Pontok

- ✅ MCP eszközök **minden felhasználói kérésnél** fetchelődnek
- ✅ **Sorrend fontos**: RAG → AlphaVantage → DeepWiki → Döntés
- ✅ **Debug logok** követik az egész folyamatot
- ✅ **Hibakezelés** minden MCP műveletnél
- ❌ **Jelenlegi probléma**: MCP szerverek nem válaszolnak megfelelően

### Következő Lépések

1. MCP protokoll specifikáció tanulmányozása
2. Helyes endpoint struktúra kiderítése
3. Esetleg alternatív transport módszer (SSE/WebSocket)
4. MCP szerverek dokumentációjának ellenőrzése
5. Timeout és retry mechanizmusok finomhangolása
