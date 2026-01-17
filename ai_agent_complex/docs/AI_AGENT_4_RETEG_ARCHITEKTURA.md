# AI Agent 4 Rétegű Architektúra - Implementációs Útmutató

## Áttekintés

Egy összetett AI agent 4 fő rétegből épül fel, amelyek együttműködve biztosítják az intelligens, kontextus-tudatos működést. Ez a dokumentum részletesen bemutatja az alkalmazásunkban megvalósított architektúrát valós kódpéldákkal.

---

## 1. Reasoning Layer (LLM Gondolkodás / Döntések)

### Célja
Az LLM gondolkodási réteg felelős az intelligens döntéshozatalért: promptolás, chain-of-thought érvelés, triázs és routing.

### Kulcs Komponensek

#### 1.1 System Prompt Építés

A system prompt biztosítja a kontextust és a személyiséget:

```python
# backend/services/agent.py

def _build_system_prompt(self, memory: Memory) -> str:
    """Rendszer prompt építése memória kontextussal."""
    preferences = memory.preferences
    workflow = memory.workflow_state
    
    # Felhasználói információk gyűjtése
    user_info = []
    if preferences.get('name'):
        user_info.append(f"- Név: {preferences['name']}")
    user_info.append(f"- Nyelv: {preferences.get('language', 'hu')}")
    user_info.append(f"- Alapértelmezett város: {preferences.get('default_city', 'Budapest')}")
    
    prompt = f"""Te egy segítőkész AI asszisztens vagy, különböző eszközökkel.

Felhasználói preferenciák:
{chr(10).join(user_info)}
"""
    
    # Beszélgetési előzmények hozzáadása
    if memory.chat_history:
        recent_history = memory.chat_history[-10:]
        history_text = "\n".join([
            f"{msg.role}: {msg.content[:150]}"
            for msg in recent_history
        ])
        prompt += f"\nKorábbi beszélgetés:\n{history_text}\n\n"
    
    return prompt
```

#### 1.2 Chain-of-Thought Döntéshozatal

Az agent lépésről lépésre gondolkodik és választja ki a megfelelő eszközt:

```python
# backend/services/agent.py - _agent_decide_node()

async def _agent_decide_node(self, state: AgentState) -> AgentState:
    """
    LLM döntési csomópont - eszköz választás vagy végső válasz.
    
    Döntési folyamat:
    1. RAG kontextus ellenőrzése (ha van találat → használd!)
    2. Korábbi eszközhívások áttekintése (ne ismétlődj!)
    3. Elérhető eszközök listája
    4. Routing döntés: melyik eszköz vagy végső válasz?
    """
    
    # System prompt építése
    system_prompt = self._build_system_prompt(state["memory"])
    
    # RAG kontextus beágyazása (LEGMAGASABB PRIORITÁS)
    rag_section = ""
    rag_context = state.get("rag_context", {})
    if rag_context and rag_context.get("has_knowledge", False):
        context_text = rag_context.get("context_text", "")
        citations = rag_context.get("citations", [])
        
        rag_section = f"""
═══════════════════════════════════════════════════════════════
🔍 PRIORITÁS: TUDÁSBÁZIS KERESÉSI EREDMÉNYEK
═══════════════════════════════════════════════════════════════

Lekért Kontextus:
{context_text}

Elérhető Hivatkozások: {", ".join(citations)}

═══════════════════════════════════════════════════════════════
🎯 KRITIKUS SZABÁLYOK:
═══════════════════════════════════════════════════════════════

1. PREFERÁLD A LEKÉRT TUDÁST AZ ESZKÖZÖK HELYETT
   - Ha a kontextus válaszol a kérdésre → használd "final_answer"-t rögtön
   - CSAK akkor hívj eszközt, ha a tudásbázis nem elég

2. KÖTELEZŐ HIVATKOZÁS
   - Használd a formátumot: [RAG-1], [RAG-2], stb.
   - SOHA ne állíts olyat, hogy dokumentumból van, hivatkozás nélkül
"""

    # Döntési prompt - CSAK JSON választ várunk!
    decision_prompt = f"""
Elemezd a felhasználó kérését és válaszolj CSAK egy érvényes JSON objektummal.

{rag_section}

Elérhető eszközök:
- weather: Időjárás előrejelzés (paraméterek: city VAGY lat/lon)
- geocode: Cím → koordináták vagy fordítva
- GLOBAL_QUOTE: Részvényárak (AlphaVantage MCP)
- CPI: Fogyasztói árindex (AlphaVantage MCP)
...

Felhasználói kérés: {last_user_msg}

Már meghívott eszközök: {tools_called_info}

KRITIKUS SZABÁLYOK:
1. SOHA ne hívd meg ugyanazt az eszközt ugyanazokkal a paraméterekkel!
2. Ha egy eszköz nem tudta adni az adatot → ne próbáld újra, menj final_answer-re
3. Csak "final_answer" amikor MINDEN kért feladat kész VAGY lehetetlen

Válasz formátum (CSAK JSON, semmi más):
{{
  "action": "call_tool",
  "tool_name": "ESZKÖZ_NEVE",
  "arguments": {{...}},
  "reasoning": "rövid indoklás"
}}

Párhuzamos végrehajtáshoz (amikor az eszközök függetlenek):
{{
  "action": "call_tools_parallel",
  "tools": [
    {{"tool_name": "GLOBAL_QUOTE", "arguments": {{"symbol": "AAPL"}}}},
    {{"tool_name": "GLOBAL_QUOTE", "arguments": {{"symbol": "TSLA"}}}}
  ],
  "reasoning": "ezek az eszközök függetlenek, futhatnak egyszerre"
}}
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=decision_prompt)
    ]
    
    # LLM hívás
    response = await self.llm.ainvoke(messages)
    
    # JSON feldolgozás
    try:
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        
        decision = json.loads(content)
        logger.info(f"Agent döntés: {decision}")
        
        state["next_action"] = decision.get("action", "final_answer")
        state["tool_decision"] = decision
        
    except json.JSONDecodeError as e:
        logger.error(f"Nem sikerült feldolgozni a döntést: {e}")
        state["next_action"] = "final_answer"
    
    return state
```

#### 1.3 Routing Logika

A routing mechanizmus irányítja, hogy melyik node-hoz menjünk:

```python
# backend/services/agent.py

def _route_decision(self, state: AgentState) -> str:
    """
    Routing döntés: melyik node következik?
    
    Lehetséges utak:
    - "final_answer" → agent_finalize (befejezés)
    - "call_tool" → tool_xyz (eszköz futtatás)
    - "call_tools_parallel" → parallel_tool_execution
    - "mcp_tool_execution" → MCP eszköz
    """
    next_action = state.get("next_action", "final_answer")
    
    # Iterációs limit ellenőrzés (végtelen ciklus megelőzése)
    iteration_count = state.get("iteration_count", 0)
    if iteration_count >= MAX_ITERATIONS:
        logger.warning(f"Maximum iteráció ({MAX_ITERATIONS}) elérve, befejezés")
        return "final_answer"
    
    # Párhuzamos végrehajtás
    if next_action == "call_tools_parallel":
        return "parallel_tool_execution"
    
    # MCP eszköz
    if next_action == "mcp_tool_execution":
        return "mcp_tool_execution"
    
    # Beépített eszköz
    if next_action == "call_tool":
        tool_name = state.get("tool_decision", {}).get("tool_name")
        if tool_name in self.tools:
            return f"tool_{tool_name}"
    
    # Alapértelmezett: végső válasz
    return "final_answer"
```

---

## 2. Operational Layer (Workflow)

### Célja
A workflow réteg definiálja a node-okat, edge-eket és az állapot (state) kezelést a LangGraph segítségével.

### Kulcs Komponensek

#### 2.1 State Definiálás

Az AgentState tárolja az összes információt a workflow során:

```python
# backend/services/agent.py

from typing import List, Dict, Any, Annotated, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict, total=False):
    """LangGraph agent állapot RAG támogatással és párhuzamos végrehajtással."""
    
    # Üzenetek és memória
    messages: Sequence[BaseMessage]
    memory: Memory
    current_user_id: str
    
    # Eszköz végrehajtás
    tools_called: List[ToolCall]
    tool_decision: Dict[str, Any]
    next_action: str
    iteration_count: int  # Végtelen ciklus elleni védelem
    
    # RAG mezők
    rag_context: Dict[str, Any]  # Lekért kontextus dokumentumokból
    rag_metrics: Dict[str, Any]  # RAG teljesítmény metrikák
    skip_rag: bool  # RAG kihagyása (pl. "reset context")
    
    # MCP eszközök
    deepwiki_tools: List[Dict[str, Any]]
    alphavantage_tools: List[Dict[str, Any]]
    debug_logs: List[str]  # Debug információk frontendnek
    
    # Párhuzamos végrehajtás
    parallel_tasks: Annotated[List[Dict[str, Any]], parallel_results_reducer]
    parallel_results: Annotated[List[Dict[str, Any]], parallel_results_reducer]
```

#### 2.2 Graph Építése (Node-ok és Edge-ek)

A LangGraph workflow struktúra:

```python
# backend/services/agent.py

def _build_graph(self) -> StateGraph:
    """
    LangGraph workflow építése RAG integrációval.
    
    Node-ok:
    - rag_pipeline: RAG subgraph (ELSŐ lépés)
    - fetch_alphavantage_tools: MCP eszközök fetchelése
    - fetch_deepwiki_tools: MCP eszközök fetchelése
    - agent_decide: LLM döntéshozatal (ciklusban futhat!)
    - tool_*: Egyedi eszköz node-ok
    - parallel_tool_execution: Párhuzamos eszközök
    - agent_finalize: Végső válasz generálás
    
    Flow: 
    RAG → fetch_tools → agent_decide → tool → agent_decide (loop) → finalize
    """
    workflow = StateGraph(AgentState)
    
    # NODE-OK HOZZÁADÁSA
    # 1. RAG pipeline (ha konfigurálva van)
    if self.rag_subgraph is not None:
        workflow.add_node("rag_pipeline", self.rag_subgraph)
        logger.info("RAG pipeline integrálva az agent graph-ba")
    
    # 2. MCP eszköz fetchelés node-ok
    workflow.add_node("fetch_alphavantage_tools", self._fetch_alphavantage_tools_node)
    workflow.add_node("fetch_deepwiki_tools", self._fetch_deepwiki_tools_node)
    
    # 3. Agent döntési node-ok
    workflow.add_node("agent_decide", self._agent_decide_node)
    workflow.add_node("agent_finalize", self._agent_finalize_node)
    
    # 4. Eszköz végrehajtás node-ok
    workflow.add_node("mcp_tool_execution", self._mcp_tool_execution_node)
    workflow.add_node("parallel_tool_execution", self._parallel_tool_execution_node)
    
    # 5. Beépített eszközök node-jai
    for tool_name in self.tools.keys():
        workflow.add_node(f"tool_{tool_name}", self._create_tool_node(tool_name))
    
    # EDGE-EK DEFINIÁLÁSA
    # Belépési pont beállítása
    if self.rag_subgraph is not None:
        workflow.set_entry_point("rag_pipeline")
        workflow.add_edge("rag_pipeline", "fetch_alphavantage_tools")
    else:
        workflow.set_entry_point("fetch_alphavantage_tools")
    
    # Lineáris edge-ek (mindig ezekben a sorrendben)
    workflow.add_edge("fetch_alphavantage_tools", "fetch_deepwiki_tools")
    workflow.add_edge("fetch_deepwiki_tools", "agent_decide")
    
    # CONDITIONAL EDGES (routing a döntés alapján)
    workflow.add_conditional_edges(
        "agent_decide",
        self._route_decision,  # Routing függvény
        {
            "final_answer": "agent_finalize",
            "mcp_tool_execution": "mcp_tool_execution",
            "parallel_tool_execution": "parallel_tool_execution",
            **{f"tool_{name}": f"tool_{name}" for name in self.tools.keys()}
        }
    )
    
    # Visszatérő edge-ek (multi-step reasoning)
    for tool_name in self.tools.keys():
        workflow.add_edge(f"tool_{tool_name}", "agent_decide")
    
    workflow.add_edge("mcp_tool_execution", "agent_decide")
    workflow.add_edge("parallel_tool_execution", "agent_decide")
    
    # Végpont
    workflow.add_edge("agent_finalize", END)
    
    # Compile
    return workflow.compile()
```

#### 2.3 Workflow Vizualizáció

```
┌─────────────────────────────────────────────────────────────────┐
│                     LANGGRAPH WORKFLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  START                                                          │
│    │                                                            │
│    ▼                                                            │
│  ┌──────────────┐                                              │
│  │ rag_pipeline │  ← RAG subgraph (dokumentum keresés)         │
│  └──────┬───────┘                                              │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────────────────┐                                  │
│  │ fetch_alphavantage_tools │  ← MCP eszközök fetchelése       │
│  └──────────┬───────────────┘                                  │
│             │                                                   │
│             ▼                                                   │
│  ┌─────────────────────┐                                       │
│  │ fetch_deepwiki_tools│  ← MCP eszközök fetchelése            │
│  └──────────┬──────────┘                                       │
│             │                                                   │
│             ▼                                                   │
│  ┌──────────────────┐                                          │
│  │  agent_decide    │  ← LLM döntéshozatal                     │
│  └────┬─────────────┘                                          │
│       │                                                         │
│       ├──→ "final_answer" ──→ ┌─────────────────┐             │
│       │                        │ agent_finalize  │ → END       │
│       │                        └─────────────────┘             │
│       │                                                         │
│       ├──→ "call_tool" ──→ ┌──────────┐                       │
│       │                     │ tool_xyz │ ──┐                   │
│       │                     └──────────┘   │                   │
│       │                                     │                   │
│       ├──→ "call_tools_parallel" ──→ ┌─────────────────┐      │
│       │                              │ parallel_execute │ ─┐   │
│       │                              └─────────────────┘  │   │
│       │                                                    │   │
│       └──────────────────────────────────────────┐        │   │
│                                                   │        │   │
│              ┌────────────────────────────────────┘        │   │
│              │  ← LOOP: Multi-step reasoning              │   │
│              └────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Tool Execution Layer (Külső API-k)

### Célja
Külső API-k meghívása: adatlekérés, írás, számítás. MCP (Model Context Protocol) és beépített eszközök.

### Kulcs Komponensek

#### 3.1 Beépített Eszközök

```python
# backend/services/tools.py

class WeatherTool:
    """Időjárás eszköz - Open-Meteo API."""
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Időjárás lekérés paraméterek alapján.
        
        Args:
            arguments: {
                "city": "Budapest" VAGY
                "lat": 47.4979, "lon": 19.0402
            }
        """
        # Geocoding ha szükséges
        if "city" in arguments:
            geocode_result = await self._geocode(arguments["city"])
            lat, lon = geocode_result["lat"], geocode_result["lon"]
        else:
            lat, lon = arguments["lat"], arguments["lon"]
        
        # Open-Meteo API hívás
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weathercode",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "auto"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
```

#### 3.2 MCP Eszközök (AlphaVantage)

Az MCP protokoll lehetővé teszi dinamikus eszköz felfedezést:

```python
# backend/services/agent.py - _fetch_alphavantage_tools_node()

async def _fetch_alphavantage_tools_node(self, state: AgentState) -> AgentState:
    """
    AlphaVantage MCP szerver kapcsolat inicializálása.
    
    Lépések:
    1. Kapcsolódás az MCP szerverhez (initialize)
    2. Session ID fogadása
    3. Eszközök listázása (tools/list)
    4. 118 pénzügyi eszköz tárolása state-ben
    """
    logger.info("AlphaVantage MCP eszközök fetchelése")
    
    alphavantage_tools = []
    
    try:
        # Kapcsolódás ellenőrzése
        if not hasattr(self.alphavantage_mcp_client, 'connected') or not self.alphavantage_mcp_client.connected:
            import os
            api_key = os.getenv('ALPHAVANTAGE_API_KEY', '')
            logger.info("Kapcsolódás AlphaVantage MCP szerverhez")
            
            await self.alphavantage_mcp_client.connect(
                f"https://mcp.alphavantage.co/mcp?apikey={api_key}"
            )
        
        # Eszközök listázása
        alphavantage_tools = await self.alphavantage_mcp_client.list_tools()
        
        logger.info(f"Sikeresen fetchelve {len(alphavantage_tools)} AlphaVantage eszköz")
        logger.info(f"Elérhető eszközök: {[t.get('name') for t in alphavantage_tools[:10]]}")
        
    except Exception as e:
        logger.error(f"Hiba AlphaVantage eszközök fetchelése során: {e}")
        alphavantage_tools = []
    
    # Tárolás state-ben
    state["alphavantage_tools"] = alphavantage_tools
    
    return state
```

#### 3.3 MCP Eszköz Végrehajtás

```python
# backend/services/agent.py - _mcp_tool_execution_node()

async def _mcp_tool_execution_node(self, state: AgentState) -> AgentState:
    """
    MCP eszköz meghívása (DeepWiki vagy AlphaVantage).
    
    JSON-RPC 2.0 protokoll használata:
    POST /mcp
    {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "GLOBAL_QUOTE",
            "arguments": {"symbol": "AAPL"}
        }
    }
    """
    tool_decision = state.get("tool_decision", {})
    tool_name = tool_decision.get("tool_name")
    arguments = tool_decision.get("arguments", {})
    
    logger.info(f"MCP eszköz végrehajtása: {tool_name} args={arguments}")
    
    try:
        # Eszköz meghívása
        result = await self.alphavantage_mcp_client.call_tool(
            name=tool_name,
            arguments=arguments
        )
        
        # Eredmény tárolása
        tool_call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            timestamp=datetime.now()
        )
        
        state["tools_called"].append(tool_call)
        
        # System message hozzáadása az eredménnyel
        result_summary = json.dumps(result)[:500]  # Első 500 karakter
        system_msg = f"Eszköz '{tool_name}' eredménye:\n{result_summary}"
        state["messages"].append(SystemMessage(content=system_msg))
        
    except Exception as e:
        logger.error(f"MCP eszköz hiba: {e}")
        error_msg = f"Hiba '{tool_name}' eszköz futtatása során: {str(e)}"
        state["messages"].append(SystemMessage(content=error_msg))
    
    return state
```

#### 3.4 Párhuzamos Eszköz Végrehajtás

A független eszközök egyidejű futtatása jelentős teljesítménynövekedést eredményez:

```python
# backend/services/parallel_execution.py

async def execute_parallel_mcp_tools(
    tasks: List[Dict],
    alphavantage_client,
    session_id: str
) -> List[Dict]:
    """
    Több MCP eszköz párhuzamos futtatása asyncio.gather-rel.
    
    Példa:
    tasks = [
        {"tool_name": "GLOBAL_QUOTE", "arguments": {"symbol": "AAPL"}},
        {"tool_name": "GLOBAL_QUOTE", "arguments": {"symbol": "TSLA"}}
    ]
    
    Eredmény: 2 eszköz ~3 mp alatt (szekvenciális: ~6 mp)
    """
    
    async def execute_single_tool(task: Dict) -> Dict:
        try:
            result = await alphavantage_client.call_tool(
                name=task["tool_name"],
                arguments=task["arguments"],
                session_id=session_id
            )
            return {
                "tool_name": task["tool_name"],
                "arguments": task["arguments"],
                "result": result,
                "success": True
            }
        except Exception as e:
            return {
                "tool_name": task["tool_name"],
                "arguments": task["arguments"],
                "error": str(e),
                "success": False
            }
    
    # Párhuzamos futtatás - asyncio.gather!
    logger.info(f"Párhuzamos futtatás: {len(tasks)} MCP eszköz")
    
    results = await asyncio.gather(*[
        execute_single_tool(task) for task in tasks
    ])
    
    successful = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    
    logger.info(f"Párhuzamos végrehajtás kész: {successful} sikeres, {failed} sikertelen")
    
    return results
```

**Teljesítmény összehasonlítás:**
```
Szekvenciális:
  Tool 1: 3 mp
  Tool 2: 3 mp
  Total: 6 mp

Párhuzamos (asyncio.gather):
  Tool 1 + Tool 2 egyidejűleg: ~3 mp
  Speedup: 2x
```

---

## 4. Memory / RAG / Context Handling

### Célja
Stateful működés biztosítása: beszélgetési előzmények, felhasználói preferenciák, dokumentum-alapú kontextus (RAG), retrieval-before-tools stratégia.

### Kulcs Komponensek

#### 4.1 Memory Struktúra

```python
# backend/domain/models.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class Message(BaseModel):
    """Egyetlen üzenet a beszélgetésben."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class WorkflowState(BaseModel):
    """Workflow állapot követése."""
    flow: str = ""  # "onboarding", "weather_check", stb.
    step: int = 0
    total_steps: int = 0
    data: Dict[str, Any] = Field(default_factory=dict)

class Memory(BaseModel):
    """
    Felhasználói memória - perzisztens állapot.
    
    Tartalmazza:
    - chat_history: Beszélgetési előzmények
    - preferences: Felhasználói beállítások (város, nyelv, stb.)
    - workflow_state: Aktív workflow állapot
    """
    chat_history: List[Message] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    workflow_state: WorkflowState = Field(default_factory=WorkflowState)
```

#### 4.2 RAG Pipeline (Retrieval-Before-Tools)

A RAG pipeline **MINDEN kérés ELŐTT** fut, dokumentum alapú kontextust biztosítva:

```python
# backend/rag/rag_graph.py

from langgraph.graph import StateGraph, END

class RAGState(TypedDict):
    """RAG pipeline állapot."""
    messages: Sequence[BaseMessage]
    user_id: str
    
    # RAG feldolgozás mezők
    original_query: str
    rewritten_query: str  # Optimalizált keresési query
    retrieved_chunks: List[Dict[str, Any]]  # Lekért dokumentum darabok
    context_text: str  # Összefűzött kontextus
    citations: List[str]  # Hivatkozások
    has_knowledge: bool  # Van-e releváns tudás?

def build_rag_graph() -> StateGraph:
    """
    RAG subgraph építése.
    
    Pipeline:
    1. query_rewrite: Query optimalizálás (kérdés → kulcsszavak)
    2. retrieve: Dokumentum keresés vektoradatbázisban
    3. format_context: Kontextus formázása LLM-nek
    """
    workflow = StateGraph(RAGState)
    
    workflow.add_node("query_rewrite", query_rewrite_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("format_context", format_context_node)
    
    workflow.set_entry_point("query_rewrite")
    workflow.add_edge("query_rewrite", "retrieve")
    workflow.add_edge("retrieve", "format_context")
    workflow.add_edge("format_context", END)
    
    return workflow.compile()
```

#### 4.3 Query Rewriting

Az eredeti kérdés optimalizálása kereséshez:

```python
# backend/rag/rag_nodes.py

async def query_rewrite_node(state: RAGState) -> RAGState:
    """
    Query újraírás - beszélgetési kérdés → keresési kulcsszavak.
    
    Példa:
    User: "És mennyi a bevétele?"
    Chat history: "Kérdeztem az Apple-ről..."
    
    Rewritten: "Apple bevétel revenue earnings"
    """
    original_query = state["original_query"]
    
    # Chat history kontextus
    recent_history = state["messages"][-5:] if state["messages"] else []
    history_text = "\n".join([f"{msg.type}: {msg.content}" for msg in recent_history])
    
    prompt = f"""
Alakítsd át a felhasználói kérdést optimális keresési query-vé.

Beszélgetési kontextus:
{history_text}

Aktuális kérdés: {original_query}

Add vissza CSAK a keresési kulcsszavakat, semmi mást!
"""
    
    llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    state["rewritten_query"] = response.content.strip()
    logger.info(f"Query rewrite: '{original_query}' → '{state['rewritten_query']}'")
    
    return state
```

#### 4.4 Vector Store Keresés

```python
# backend/rag/retrieval_service.py

from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

class RetrievalService:
    """Dokumentum keresési szolgáltatás."""
    
    def __init__(self, vector_store_path: str, openai_api_key: str):
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.vector_store = Chroma(
            persist_directory=vector_store_path,
            embedding_function=self.embeddings
        )
    
    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Dokumentum keresés vektoradatbázisban.
        
        Args:
            query: Keresési query (már újraírt!)
            user_id: Felhasználó azonosító (szűréshez)
            top_k: Hány dokumentumot kérjünk le
        
        Returns:
            Lista dokumentum chunk-okról metaadatokkal
        """
        # Szűrő: csak az adott user dokumentumai
        filter_dict = {"user_id": user_id}
        
        # Similarity search
        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=top_k,
            filter=filter_dict
        )
        
        chunks = []
        for doc, score in results:
            chunks.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity_score": score,
                "citation": f"{doc.metadata.get('filename', 'Unknown')} - {doc.metadata.get('chunk_id', '')}"
            })
        
        logger.info(f"Lekérve {len(chunks)} chunk query-hez: '{query}'")
        
        return chunks
```

#### 4.5 Context Formázás

```python
# backend/rag/rag_nodes.py

async def format_context_node(state: RAGState) -> RAGState:
    """
    Lekért chunk-ok formázása LLM-nek.
    
    Output: Strukturált kontextus hivatkozásokkal.
    """
    chunks = state.get("retrieved_chunks", [])
    
    if not chunks:
        state["has_knowledge"] = False
        state["context_text"] = ""
        state["citations"] = []
        return state
    
    # Chunk-ok összefűzése
    context_parts = []
    citations = []
    
    for idx, chunk in enumerate(chunks, start=1):
        citation_id = f"RAG-{idx}"
        content = chunk["content"]
        citation_text = chunk["citation"]
        
        context_parts.append(f"[{citation_id}] {content}")
        citations.append(f"{citation_id}: {citation_text}")
    
    state["context_text"] = "\n\n".join(context_parts)
    state["citations"] = citations
    state["has_knowledge"] = True
    
    logger.info(f"Kontextus formázva: {len(chunks)} chunk, {len(citations)} hivatkozás")
    
    return state
```

#### 4.6 Retrieval-Before-Tools Stratégia

A RAG pipeline **mindig először** fut, az eszközök előtt:

```python
# backend/services/agent.py - _build_graph()

# Graph építés sorrend:
if self.rag_subgraph is not None:
    workflow.set_entry_point("rag_pipeline")  # ← ELSŐ LÉPÉS!
    workflow.add_edge("rag_pipeline", "fetch_alphavantage_tools")
else:
    workflow.set_entry_point("fetch_alphavantage_tools")

# Flow:
# 1. RAG pipeline (dokumentum keresés)
# 2. MCP tools fetch (eszköz felfedezés)
# 3. Agent decide (döntés: használd a dokumentumot VAGY hívj eszközt)
```

**Prioritási sorrend az LLM döntéshozatalban:**

```
1. LEGMAGASABB PRIORITÁS: RAG kontextus
   └─> Ha van találat → használd és hivatkozz rá!
   └─> Csak akkor hívj eszközt, ha a dokumentum NEM elég

2. KÖZEPES PRIORITÁS: Eszközhívás kontextussal
   └─> Chat history és preferenciák beágyazása az argumentumokba

3. LEGALACSONYABB PRIORITÁS: Direkt eszközhívás
   └─> Explicit paraméterek a felhasználói üzenetből
```

---

## Összefoglalás: 4 Réteg Együttműködése

### Teljes Folyamat Példa

**Felhasználói kérdés:** "Get stock prices for AAPL and TSLA"

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. REASONING LAYER (LLM)                                        │
├─────────────────────────────────────────────────────────────────┤
│ System Prompt: "Te egy AI asszisztens vagy..."                 │
│ Chain-of-Thought:                                               │
│   - RAG kontextus: Nincs releváns dokumentum                    │
│   - Elérhető eszközök: GLOBAL_QUOTE (AlphaVantage MCP)         │
│   - Döntés: 2 független eszköz → párhuzamos futtatás!          │
│                                                                 │
│ Output JSON:                                                    │
│ {                                                               │
│   "action": "call_tools_parallel",                             │
│   "tools": [                                                    │
│     {"tool_name": "GLOBAL_QUOTE", "arguments": {"symbol": "AAPL"}},│
│     {"tool_name": "GLOBAL_QUOTE", "arguments": {"symbol": "TSLA"}} │
│   ]                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. OPERATIONAL LAYER (Workflow)                                 │
├─────────────────────────────────────────────────────────────────┤
│ StateGraph routing:                                             │
│   agent_decide → _route_decision()                              │
│   → next_action = "call_tools_parallel"                         │
│   → Route to: "parallel_tool_execution" node                    │
│                                                                 │
│ State update:                                                   │
│   state["parallel_tasks"] = [AAPL task, TSLA task]             │
│   state["iteration_count"] += 1                                 │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. TOOL EXECUTION LAYER (Külső API-k)                           │
├─────────────────────────────────────────────────────────────────┤
│ Párhuzamos végrehajtás (asyncio.gather):                        │
│                                                                 │
│   Task 1: MCP call_tool(GLOBAL_QUOTE, AAPL)                    │
│   ├─ POST https://mcp.alphavantage.co/mcp                      │
│   ├─ JSON-RPC: tools/call                                       │
│   └─ Result: {"symbol": "AAPL", "price": "225.33", ...}        │
│                                                                 │
│   Task 2: MCP call_tool(GLOBAL_QUOTE, TSLA)                    │
│   ├─ POST https://mcp.alphavantage.co/mcp                      │
│   ├─ JSON-RPC: tools/call                                       │
│   └─ Result: {"symbol": "TSLA", "price": "242.84", ...}        │
│                                                                 │
│ Total time: ~3 másodperc (szekvenciális: ~6 mp)                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. MEMORY / CONTEXT HANDLING                                    │
├─────────────────────────────────────────────────────────────────┤
│ State update (stateful működés):                                │
│                                                                 │
│ state["tools_called"].append(                                   │
│   ToolCall(                                                     │
│     tool_name="GLOBAL_QUOTE",                                   │
│     arguments={"symbol": "AAPL"},                               │
│     result={...},                                               │
│     timestamp=datetime.now()                                    │
│   )                                                             │
│ )                                                               │
│                                                                 │
│ memory.chat_history.append(                                     │
│   Message(                                                      │
│     role="system",                                              │
│     content="Tool results: AAPL=$225.33, TSLA=$242.84"          │
│   )                                                             │
│ )                                                               │
│                                                                 │
│ Következő iterációnál:                                          │
│   - LLM látja a korábbi tool call-t                             │
│   - NEM ismétli meg ugyanazt                                    │
│   - Összegzi az eredményt                                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
                      LOOP BACK TO:
                    agent_decide node
                            ↓
                  Döntés: "final_answer"
                            ↓
                  agent_finalize node
                            ↓
         Végső válasz: "AAPL: $225.33, TSLA: $242.84"
```

---

## Kulcs Tanulságok

### 1. Reasoning Layer
- **System Prompt**: Személyiség + kontextus + szabályok
- **Chain-of-Thought**: Lépésről lépésre gondolkodás
- **JSON Output**: Strukturált döntéshozatal
- **Routing**: Intelligens node kiválasztás

### 2. Operational Layer
- **StateGraph**: LangGraph workflow definiálás
- **Node-ok**: Funkcionális egységek (RAG, eszköz, döntés)
- **Edge-ek**: Workflow irányítás (lineáris + conditional)
- **State**: Információ perzisztencia node-ok között

### 3. Tool Execution Layer
- **Beépített Eszközök**: Python kód végrehajtás
- **MCP Eszközök**: Dinamikus felfedezés + JSON-RPC hívás
- **Párhuzamos Futtatás**: asyncio.gather teljesítménynövekedéshez
- **Hibakezelés**: Try-except minden eszköznél

### 4. Memory / RAG / Context
- **Retrieval-Before-Tools**: Dokumentumok ELŐSZÖR
- **Vector Store**: Szemantikus keresés
- **Query Rewriting**: Beszélgetés → kulcsszavak
- **Citations**: Kötelező hivatkozás dokumentumokra
- **Stateful Memory**: Chat history + preferences perzisztencia

---

**Verzió:** 1.0 (2026-01-13)  
**Szerző:** AI Agent Development Team  
**Alapul:** Claude Sonnet 4 + LangGraph + MCP Protocol
