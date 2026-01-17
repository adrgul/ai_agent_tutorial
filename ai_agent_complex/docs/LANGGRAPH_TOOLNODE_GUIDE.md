# LangGraph ToolNode Útmutató

## Áttekintés

A **ToolNode** egy specializált LangGraph csomópont, amely automatikusan kezeli az eszköz-/függvényhívásokat az ágensek munkafolyamataiban. Leegyszerűsíti az eszközök végrehajtását azáltal, hogy menedzseli az LLM eszközhívások és a tényleges függvényvégrehajtás közötti konverziót.

## Mi az a ToolNode?

A `ToolNode` egy előre elkészített LangGraph komponens, amely:
- Automatikusan kinyeri az eszközhívásokat az AI üzenetekből
- Végrehajtja a megfelelő Python függvényeket
- Visszaformázza az eredményeket üzenetekké az ágens számára
- Kecsesen kezeli a hibákat és kivételeket

## Alapvető Használat

### 1. Szükséges Komponensek Importálása

```python
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
```

### 2. Eszközök Definiálása

Az eszközök definiálhatók:
- Python függvényekként típusjelölésekkel
- LangChain Tool objektumokként
- Pydantic modellekként `__call__` metódussal

```python
from typing import Annotated

def weather_tool(city: Annotated[str, "A város neve"]) -> str:
    """Időjárás lekérése egy városhoz."""
    # Implementáció
    return f"Időjárás {city}-ben: Napos, 20°C"

def calculator(
    operation: Annotated[str, "matematikai művelet: add, subtract, multiply, divide"],
    a: Annotated[float, "első szám"],
    b: Annotated[float, "második szám"]
) -> float:
    """Alapvető számítások végrehajtása."""
    ops = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
        "divide": a / b if b != 0 else float('inf')
    }
    return ops.get(operation, 0)
```

### 3. ToolNode Létrehozása

```python
# ToolNode létrehozása az eszközeiddel
tools = [weather_tool, calculator]
tool_node = ToolNode(tools)
```

### 4. Gráf Építése

```python
from typing import TypedDict, Sequence
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Sequence[BaseMessage]

# Gráf létrehozása
workflow = StateGraph(AgentState)

# Csomópontok hozzáadása
workflow.add_node("agent", agent_node)  # LLM döntési csomópont
workflow.add_node("tools", tool_node)   # ToolNode kezeli az összes eszközt

# Élek hozzáadása
workflow.add_edge("tools", "agent")  # Eszközök után vissza az ágenshez
workflow.set_entry_point("agent")
```

## Hogyan Működik a ToolNode

### Automatikus Eszközhívás Észlelése

Amikor az LLM úgy dönt, hogy eszközt hív, egy `AIMessage`-t generál `tool_calls` mezővel:

```python
AIMessage(
    content="",
    tool_calls=[
        {
            "name": "weather_tool",
            "args": {"city": "Budapest"},
            "id": "call_123"
        }
    ]
)
```

### ToolNode Feldolgozás

A ToolNode automatikusan:
1. **Kinyeri** az eszközhívásokat az üzenetből
2. **Megtalálja** a megfelelő függvényt
3. **Végrehajtja** a függvényt a megadott argumentumokkal
4. **Becsomagolja** az eredményt egy `ToolMessage`-be
5. **Hozzáfűzi** az eredményt az állapothoz

```python
# ToolNode generálja:
ToolMessage(
    content="Időjárás Budapest-en: Napos, 20°C",
    tool_call_id="call_123"
)
```

## Haladó Minták

### 1. Egyéni Eszközvégrehajtó Csomópont

Ha több kontrollra van szükséged, hozz létre egyéni eszközvégrehajtó csomópontot:

```python
async def execute_tools_node(state: AgentState) -> AgentState:
    """Egyéni eszközvégrehajtás naplózással és hibakezeléssel."""
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_calls = last_message.tool_calls if hasattr(last_message, 'tool_calls') else []
    
    tool_messages = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        try:
            # Eszköz végrehajtása
            result = await tools_dict[tool_name](**tool_args)
            
            # Végrehajtás naplózása
            logger.info(f"{tool_name} eszköz sikeresen végrehajtva")
            
            # Tool message létrehozása
            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                )
            )
        except Exception as e:
            logger.error(f"{tool_name} eszköz sikertelen: {e}")
            tool_messages.append(
                ToolMessage(
                    content=f"Hiba: {str(e)}",
                    tool_call_id=tool_call["id"],
                    additional_kwargs={"error": True}
                )
            )
    
    return {"messages": messages + tool_messages}
```

### 2. Párhuzamos Eszközvégrehajtás

A LangGraph ToolNode-ja automatikusan kezeli a párhuzamos eszközvégrehajtást, amikor az LLM több eszközt kér:

```python
# Az LLM egyszerre több eszközt is meghívhat
AIMessage(
    content="",
    tool_calls=[
        {"name": "weather_tool", "args": {"city": "Budapest"}, "id": "call_1"},
        {"name": "weather_tool", "args": {"city": "Bécs"}, "id": "call_2"},
        {"name": "calculator", "args": {"operation": "add", "a": 5, "b": 3}, "id": "call_3"}
    ]
)

# A ToolNode mindet párhuzamosan végrehajtja és az összes eredményt visszaadja
```

### 3. Feltételes Eszköz Útvonalválasztás

Különböző eszköz csomópontokhoz irányítás az eszköz típusa alapján:

```python
def route_tools(state: AgentState) -> str:
    """Irányítás specifikus eszköz csomópontokhoz az eszköz típusa alapján."""
    last_message = state["messages"][-1]
    
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        tool_name = last_message.tool_calls[0]["name"]
        
        # Külső API eszközök külön irányítása
        if tool_name in ["weather_tool", "crypto_price"]:
            return "external_tools"
        
        # MCP eszközök külön irányítása
        elif tool_name in ["deepwiki_ask", "alphavantage_currency"]:
            return "mcp_tools"
        
        # Alapértelmezett eszköz csomópont
        return "tools"
    
    return "continue"

# Feltételes élek hozzáadása
workflow.add_conditional_edges(
    "agent",
    route_tools,
    {
        "tools": "tools",
        "external_tools": "external_tools_node",
        "mcp_tools": "mcp_tools_node",
        "continue": "finalize"
    }
)
```

## ToolNode vs Egyéni Eszközvégrehajtás

### ToolNode Használata Amikor:
- ✅ Standard Python függvényeid vannak eszközként
- ✅ Automatikus párhuzamos végrehajtást szeretnél
- ✅ Nincs szükséged egyéni hibakezelésre
- ✅ Egyszerű, deklaratív kódot szeretnél

### Egyéni Eszköz Csomópont Amikor:
- ✅ Egyéni naplózásra vagy metrikákra van szükséged
- ✅ Eszköz argumentumokat kell átalakítanod
- ✅ Komplex hibakezelésre van szükséged
- ✅ Külső rendszerekkel kell integrálnod (adatbázisok, MCP szerverek)
- ✅ Eszközhasználatot kell követned hibakereséshez

## Valós Példa: Ágens Eszközökkel

```python
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Állapot definiálása
class AgentState(TypedDict):
    messages: Sequence[BaseMessage]
    tools_called: list
    next_action: Literal["call_tool", "final_answer"]

# Eszközök definiálása
def search_web(query: str) -> str:
    """Weben való keresés információért."""
    return f"Keresési eredmények: {query}"

def calculate(expression: str) -> float:
    """Matematikai kifejezés kiértékelése."""
    return eval(expression)  # Éles környezetben használj ast.literal_eval vagy biztonságosabb módszert

tools = [search_web, calculate]

# LLM létrehozása eszközökkel
llm = ChatOpenAI(model="gpt-4", temperature=0)
llm_with_tools = llm.bind_tools(tools)

# Ágens csomópont definiálása
async def agent_node(state: AgentState) -> AgentState:
    """Az ágens döntéseket hoz."""
    response = await llm_with_tools.ainvoke(state["messages"])
    
    # Következő művelet meghatározása
    if hasattr(response, 'tool_calls') and response.tool_calls:
        next_action = "call_tool"
    else:
        next_action = "final_answer"
    
    return {
        "messages": state["messages"] + [response],
        "next_action": next_action
    }

# ToolNode létrehozása
tool_node = ToolNode(tools)

# Gráf építése
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

# Útvonalválasztó logika
def should_continue(state: AgentState) -> str:
    return state["next_action"]

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "call_tool": "tools",
        "final_answer": END
    }
)
workflow.add_edge("tools", "agent")
workflow.set_entry_point("agent")

# Fordítás és futtatás
app = workflow.compile()
result = await app.ainvoke({
    "messages": [HumanMessage(content="Mennyi 25 * 4 + 10?")],
    "tools_called": [],
    "next_action": "call_tool"
})
```

## Legjobb Gyakorlatok

### 1. Eszköz Függvény Tervezés
```python
def good_tool(
    param1: Annotated[str, "param1 világos leírása"],
    param2: Annotated[int, "param2 világos leírása"] = 0
) -> str:
    """
    Világos, tömör eszköz leírás.
    
    Az LLM ezt használja annak eldöntésére, mikor hívja meg az eszközt.
    Légy konkrét arról, mit csinál az eszköz.
    """
    # Implementáció
    return result
```

### 2. Hibakezelés az Eszközökben
```python
def robust_tool(city: str) -> dict:
    """Időjárási adatok lekérése megfelelő hibakezeléssel."""
    try:
        # Implementáció
        result = fetch_weather(city)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Időjárás eszköz hiba: {e}")
        return {"success": False, "error": str(e)}
```

### 3. Eszköz Eredmény Formázás
```python
def formatted_tool(query: str) -> str:
    """Strukturált, LLM-barát eredmények visszaadása."""
    results = search(query)
    
    # Formázás LLM fogyasztáshoz
    formatted = "Keresési Eredmények:\n"
    for i, result in enumerate(results[:5], 1):
        formatted += f"{i}. {result['title']}: {result['snippet']}\n"
    
    return formatted
```

### 4. Naplózás és Monitorozás
```python
async def monitored_tool_node(state: AgentState) -> AgentState:
    """Eszköz csomópont monitorozással."""
    start_time = time.time()
    
    # Eszközök végrehajtása
    result = await tool_node.ainvoke(state)
    
    # Metrikák naplózása
    execution_time = time.time() - start_time
    logger.info(f"Eszközök végrehajtva {execution_time:.2f}s alatt")
    
    # Eszközhasználat követése
    state["tools_called"].extend([
        call["name"] for call in state["messages"][-1].tool_calls
    ])
    
    return result
```

## Gyakori Minták

### 1. minta: Szekvenciális Eszközhívások
```python
# Ágens dönt → Eszköz 1 → Ágens dönt → Eszköz 2 → Végső válasz
workflow.add_edge("tools", "agent")
```

### 2. minta: Eszköz Kötegezés
```python
# Ágens több eszközt dönt → Mindent párhuzamosan végrehajt → Ágens dönt
# A ToolNode ezt automatikusan kezeli!
```

### 3. minta: Eszköz Tartalékok
```python
async def tool_with_fallback(state: AgentState) -> AgentState:
    """Elsődleges eszköz kipróbálása, tartalékra váltás."""
    try:
        return await primary_tool_node.ainvoke(state)
    except Exception:
        logger.warning("Elsődleges eszköz sikertelen, tartalék használata")
        return await fallback_tool_node.ainvoke(state)
```

## ToolNode Hibakeresés

### Részletes Naplózás Engedélyezése
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# LangGraph naplózni fogja:
# - Eszköz kiválasztást az LLM által
# - Eszköz végrehajtás kezdetét/végét
# - Eszköz eredményeket
# - Hibákat és kivételeket
```

### Állapot Vizsgálata Eszközvégrehajtás Után
```python
result = await app.ainvoke(initial_state)

# Üzenetek ellenőrzése
for msg in result["messages"]:
    print(f"{msg.__class__.__name__}: {msg.content}")
    if hasattr(msg, 'tool_calls'):
        print(f"  Eszközhívások: {msg.tool_calls}")
```

### Egyéni Eszköz Burkoló Hibakereséshez
```python
def debug_tool_wrapper(func):
    """Eszközök becsomagolása hibakereső naplózás hozzáadásához."""
    async def wrapper(*args, **kwargs):
        logger.debug(f"{func.__name__} hívása args={args}, kwargs={kwargs}")
        result = await func(*args, **kwargs)
        logger.debug(f"Eredmény: {result}")
        return result
    return wrapper

# Összes eszköz becsomagolása
debug_tools = [debug_tool_wrapper(tool) for tool in tools]
tool_node = ToolNode(debug_tools)
```

## Források

- [LangGraph Dokumentáció](https://python.langchain.com/docs/langgraph)
- [LangGraph ToolNode API Referencia](https://python.langchain.com/docs/langgraph/reference/prebuilt#toolnode)
- [LangChain Eszközök Útmutató](https://python.langchain.com/docs/modules/tools/)
- [Ágensek Építése LangGraph-fal](https://python.langchain.com/docs/langgraph/tutorials/introduction)

## Összefoglalás

A **ToolNode** leegyszerűsíti az eszközvégrehajtást LangGraph ágensekben azáltal, hogy:
- Automatikusan kezeli az eszközhívás észlelését és végrehajtást
- Támogatja a párhuzamos eszközvégrehajtást azonnal
- Konzisztens hibakezelést biztosít
- Csökkenti a boilerplate kódot

Használj ToolNode-ot standard eszközvégrehajtáshoz, és hozz létre egyéni eszköz csomópontokat, amikor finomhangolt kontrollt igényelsz a végrehajtási folyamat, naplózás vagy hibakezelés felett.
