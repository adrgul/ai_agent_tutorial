# Multi-Agent Minták LangGraph-ban

## Áttekintés

Ez a dokumentum az 5 leggyakoribb multi-agent tervezési mintát mutatja be, amelyek ebben az AI ügyfélszolgálati alkalmazásban vannak implementálva. Minden minta különböző megközelítést kínál ugyanarra a problémára: hogyan strukturáljuk az intelligens ágensek közötti munkamegosztást.

---

## 1. Router Minta

### Koncepció

**Input → Osztályozás → Specialisták → Szintézis**

A Router minta egy központi osztályozó node-dal kezdődik, amely meghatározza, hogy melyik specialista ágenshez kell irányítani a kérést. Támogatja a párhuzamos végrehajtást (fan-out) vegyes szándékok esetén.

### Főbb jellemzők:
- ✅ **Vertikális tudás**: Minden specialista egy adott területre fókuszál (pl. számlázás, technikai, fiók)
- ✅ **Párhuzamos fan-out**: A `Send` használatával több specialista dolgozhat egyszerre
- ✅ **Külön routing logika**: Egyértelmű szétválasztás a döntéshozatal és a végrehajtás között

### Implementáció

```python
# backend/app/application/orchestration/patterns/router.py

from langgraph.graph import StateGraph, END, Send

def classify_intent(state: SupportState) -> SupportState:
    """
    Osztályozza a felhasználói szándékot, hogy meghatározza az útvonalat.
    
    Ez a node demonstrálja: feltételes él döntéshozatalt.
    """
    message = state["messages"][-1]["content"]
    
    # Egyszerű osztályozás kulcsszavak alapján
    message_lower = message.lower()
    
    # Vegyes szándék ellenőrzése (fan-out trigger)
    is_billing = any(kw in message_lower for kw in ["számlázás", "díj", "fizetés"])
    is_technical = any(kw in message_lower for kw in ["technikai", "hiba", "nem működik"])
    is_account = any(kw in message_lower for kw in ["fiók", "bejelentkezés", "jelszó"])
    
    # Útvonal meghatározása
    if is_billing and is_technical:
        route = "mixed_billing_tech"  # Párhuzamos végrehajtást vált ki
    elif is_billing:
        route = "billing"
    elif is_technical:
        route = "technical"
    else:
        route = "general"
    
    state["routing_decision"] = route
    return state


def fanout_specialists(state: SupportState) -> list[Send]:
    """
    Fan-out több specialistához Send használatával.
    
    Ez demonstrálja: Send a párhuzamos végrehajtáshoz.
    A LangGraph mindkét specialistát EGYSZERRE futtatja.
    """
    route = state["routing_decision"]
    
    sends = []
    
    if "billing" in route:
        sends.append(Send("billing_specialist", state))
    if "tech" in route:
        sends.append(Send("tech_specialist", state))
    
    # Fan-out esemény rögzítése a trace-ben
    state["trace"].append(
        TraceEvent.send_fanout({
            "specialists": [s.node for s in sends],
            "reason": "Vegyes szándék észlelve"
        })
    )
    
    return sends


def billing_specialist(state: SupportState) -> SupportState:
    """Számlázási specialista ágens."""
    state["trace"].append(TraceEvent.node_start("billing_specialist"))
    
    llm = OpenAIProvider()
    message = state["messages"][-1]["content"]
    
    # KB cikkek lekérése
    articles, kb_event = retrieve_kb_articles(f"billing {message}", top_k=2)
    state["trace"].append(kb_event)
    state["sources"].extend(format_kb_sources(articles))
    
    # Specialista válasz generálása
    kb_context = "\n".join([f"- {a['title']}: {a['content']}" for a in articles])
    
    response = llm.chat_completion([{
        "role": "user", 
        "content": f"Számlázási kérdés: {message}\n\nTudásbázis:\n{kb_context}"
    }])
    
    # Eredmény tárolása
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["billing"] = response
    
    return state


def synthesize_response(state: SupportState) -> SupportState:
    """
    Összesíti a specialista válaszokat.
    
    Ez a node egyesíti a párhuzamos eredményeket egy egységes válasszá.
    """
    specialist_results = state.get("specialist_results", {})
    
    if len(specialist_results) > 1:
        # Több specialista - válaszok egyesítése
        combined = "\n\n".join([
            f"**{spec.title()} Csapat:**\n{response}"
            for spec, response in specialist_results.items()
        ])
        
        final_answer = f"Szakértői csapatainkat konzultáltam:\n\n{combined}"
    else:
        # Egyetlen specialista
        final_answer = list(specialist_results.values())[0]
    
    state["final_answer"] = final_answer
    return state


def create_router_graph() -> StateGraph:
    """
    Router minta gráf létrehozása.
    
    Kulcs koncepciók:
    - Feltételes élek (route_to_specialist)
    - Send a fan-out-hoz (fanout_specialists)
    - Több specialista node
    - Párhuzamos eredmények szintézise
    """
    graph = StateGraph(SupportState)
    
    # Node-ok hozzáadása
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("billing_specialist", billing_specialist)
    graph.add_node("tech_specialist", tech_specialist)
    graph.add_node("synthesize", synthesize_response)
    
    # Belépési pont
    graph.set_entry_point("classify_intent")
    
    # Feltételes routing él
    graph.add_conditional_edges(
        "classify_intent",
        route_to_specialist,  # Függvény, amely eldönti a következő node-ot
        {
            "billing_specialist": "billing_specialist",
            "tech_specialist": "tech_specialist",
            "fanout_specialists": "fanout_specialists",
            "synthesize": "synthesize",
        }
    )
    
    # Fan-out node (dinamikus)
    graph.add_conditional_edges("classify_intent", fanout_specialists)
    
    # Minden specialista a szintézishez folyik
    graph.add_edge("billing_specialist", "synthesize")
    graph.add_edge("tech_specialist", "synthesize")
    
    # Szintézis a végponthoz
    graph.add_edge("synthesize", END)
    
    return graph
```

### Mikor használjuk?
- ✅ Több különálló szakterülettel rendelkező rendszerek
- ✅ Párhuzamos feldolgozás szükséges
- ✅ Egyértelmű domain határok vannak

---

## 2. Subagents Minta

### Koncepció

**Fő agent hív al-ügynököket toolként**

Egyetlen orchestrator ágens dönti el, hogy melyik specializált subagent-et hívja meg a kérés feldolgozásához. A subagent-ek függvényekként/toolokként működnek.

### Főbb jellemzők:
- ✅ **LLM dönt**: Az AI dönti el, melyik subagent szükséges
- ✅ **Egyszerű UX**: Egyetlen "fő agent" interfész
- ✅ **Kontrollpont**: Központi koordináció és felügyelet

### Implementáció

```python
# backend/app/application/orchestration/patterns/subagents.py

class TriageSubagent:
    """Subagent a ticket osztályozáshoz."""
    
    @staticmethod
    def execute(message: str) -> TicketTriage:
        """Osztályozza és priorizálja a ticketet."""
        message_lower = message.lower()
        
        # Kategória meghatározása
        if any(kw in message_lower for kw in ["számlázás", "díj", "visszatérítés"]):
            category = "Billing"
            team = "Számlázási Csapat"
        elif any(kw in message_lower for kw in ["technikai", "hiba", "bug"]):
            category = "Technical"
            team = "Technikai Támogatás"
        else:
            category = "Other"
            team = "Általános Támogatás"
        
        # Prioritás meghatározása
        urgent_keywords = ["sürgős", "azonnal", "vészhelyzet"]
        if any(kw in message_lower for kw in urgent_keywords):
            priority = "P1"
        else:
            priority = "P2"
        
        return TicketTriage(
            category=category,
            priority=priority,
            sentiment="neutral",
            routing_team=team,
            tags=["subagents_pattern"],
            confidence=0.85,
        )


class KnowledgeSubagent:
    """Subagent a tudásbázis lekérdezéshez és válaszgeneráláshoz."""
    
    @staticmethod
    def execute(message: str) -> tuple[str, list[str]]:
        """KB lekérés és megalapozott válasz generálása."""
        llm = OpenAIProvider()
        
        # Releváns cikkek lekérése
        articles, _ = retrieve_kb_articles(message, top_k=3)
        sources = format_kb_sources(articles)
        
        # Megalapozott válasz generálása
        kb_context = "\n".join([
            f"[{a['id']}] {a['title']}: {a['content']}"
            for a in articles
        ])
        
        prompt = f"""Válaszolj a kérdésre CSAK a megadott tudásbázis cikkek alapján.
Hivatkozz a cikk ID-kra.

Kérdés: {message}

Tudásbázis:
{kb_context}

Adj pontos, hivatkozásokkal ellátott választ."""
        
        answer = llm.chat_completion([{"role": "user", "content": prompt}])
        
        return answer, sources


def orchestrator_node(state: SupportState) -> SupportState:
    """
    Orchestrator node, amely eldönti, melyik subagent-eket hívja meg.
    
    Ez demonstrálja a Subagents mintát, ahol egy LLM-alapú orchestrator
    dönt arról, hogy melyik specializált subagent-et kell meghívni.
    """
    state["trace"].append(TraceEvent.node_start("orchestrator"))
    
    message = state["messages"][-1]["content"]
    llm = OpenAIProvider()
    
    # LLM dönt, melyik subagent-eket hívja
    decision_prompt = f"""Ügyfélszolgálati orchestrator vagy.
Döntsd el, melyik subagent-eket kell hívni ehhez az üzenethez.

Elérhető subagent-ek:
- triage: Ticket kategorizálás, prioritás, hangulat
- knowledge: KB cikkek lekérése és megalapozott válasz
- agent_assist: Válasz draft, ügyösszefoglaló, következő lépések

Ügyfél üzenet: {message}

Melyik subagent-eket kell hívni? Válaszolj vesszővel elválasztott listával.
Legtöbb esetben mindhárom. Formátum: triage,knowledge,agent_assist"""
    
    decision = llm.chat_completion([{"role": "user", "content": decision_prompt}])
    subagents_to_call = [s.strip() for s in decision.lower().split(",")]
    
    state["trace"].append(TraceEvent.node_end("orchestrator", {
        "subagents": subagents_to_call
    }))
    
    # Triage subagent hívása
    if "triage" in subagents_to_call:
        state["trace"].append(TraceEvent.tool_call("triage_subagent"))
        triage_result = TriageSubagent.execute(message)
        state["ticket"] = triage_result
        state["trace"].append(TraceEvent.tool_result("triage_subagent", {
            "category": triage_result.category,
            "priority": triage_result.priority,
        }))
    
    # Knowledge subagent hívása
    if "knowledge" in subagents_to_call:
        state["trace"].append(TraceEvent.tool_call("knowledge_subagent"))
        answer, sources = KnowledgeSubagent.execute(message)
        state["final_answer"] = answer
        state["sources"].extend(sources)
        state["trace"].append(TraceEvent.tool_result("knowledge_subagent", {
            "sources_count": len(sources)
        }))
    
    return state


def create_subagents_graph() -> StateGraph:
    """
    Subagents minta gráf létrehozása.
    
    Kulcs koncepciók:
    - Egyetlen orchestrator node
    - Subagent-ek toolként/függvényként hívva
    - LLM dönt, melyik subagent-eket hívja
    - Trace mutatja a subagent tool hívásokat
    """
    graph = StateGraph(SupportState)
    
    # Egyetlen orchestrator node
    graph.add_node("orchestrator", orchestrator_node)
    
    # Belépés és kilépés
    graph.set_entry_point("orchestrator")
    graph.add_edge("orchestrator", END)
    
    return graph
```

### Mikor használjuk?
- ✅ Központi koordináció szükséges
- ✅ Dinamikus subagent kiválasztás
- ✅ Egyszerű felhasználói felület kell

---

## 3. Handoffs Minta

### Koncepció

**Átadás/átkapcsolás állapot alapján**

Az ágensek közötti váltás az állapot alapján történik. Szabályok határozzák meg, mikor kell átvált (pl. önkiszolgálóról emberi ügynökre).

### Főbb jellemzők:
- ✅ **Agent-váltás workflow közben**: Dinamikus agent váltás
- ✅ **Állapotváltoző indítja**: `active_agent` mező vezérli
- ✅ **Ügyfélszolgálat, triage**: Ideális eszkalációs folyamatokhoz

### Implementáció

```python
# backend/app/application/orchestration/patterns/handoffs.py

def self_service_agent(state: SupportState) -> SupportState:
    """
    Önkiszolgáló ágens megpróbálja megoldani az ügyfél problémáját.
    """
    state["trace"].append(TraceEvent.node_start("self_service_agent"))
    
    message = state["messages"][-1]["content"]
    llm = OpenAIProvider()
    
    # KB cikkek lekérése
    articles, kb_event = retrieve_kb_articles(message, top_k=3)
    state["trace"].append(kb_event)
    state["sources"].extend(format_kb_sources(articles))
    
    # Válasz generálása
    kb_context = "\n".join([f"- {a['title']}: {a['content']}" for a in articles])
    
    answer = llm.chat_completion([{
        "role": "user",
        "content": f"Önkiszolgáló támogató vagy. Válaszolj:\n\n{message}\n\nTB:\n{kb_context}"
    }])
    
    state["final_answer"] = answer
    
    # Egyszerű triage
    message_lower = message.lower()
    if any(kw in message_lower for kw in ["számlázás", "díj"]):
        category = "Billing"
    elif any(kw in message_lower for kw in ["technikai", "hiba"]):
        category = "Technical"
    else:
        category = "Other"
    
    state["ticket"] = TicketTriage(
        category=category,
        priority="P2",
        sentiment="neutral",
        routing_team="Önkiszolgáló",
        tags=["self_service"],
        confidence=0.75,
    )
    
    state["trace"].append(TraceEvent.node_end("self_service_agent"))
    return state


def check_handoff_needed(state: SupportState) -> SupportState:
    """
    Ellenőrzi, hogy szükséges-e emberhez átadás a szabályok alapján.
    
    Ez a node értékeli az átadási szabályokat és beállítja az active_agent-et.
    """
    state["trace"].append(TraceEvent.node_start("check_handoff"))
    
    message = state["messages"][-1]["content"]
    sentiment = state["ticket"].sentiment if state.get("ticket") else None
    
    # Átadási szabály ellenőrzése
    handoff_policy = check_handoff_policy(message, sentiment)
    
    if handoff_policy:
        # Átadás indítása
        state["active_agent"] = "HUMAN"
        
        # Handoff esemény rögzítése
        state["trace"].append(TraceEvent.handoff(
            from_agent="self_service_agent",
            to_agent="human_agent",
            reason=handoff_policy.reason
        ))
        
        # Prioritás frissítése
        if state.get("ticket"):
            state["ticket"].priority = handoff_policy.priority
            state["ticket"].tags.append("escalated")
    else:
        # Nincs átadás, marad önkiszolgáló
        state["active_agent"] = "SELF_SERVICE"
    
    state["trace"].append(TraceEvent.node_end("check_handoff"))
    return state


def route_by_agent(state: SupportState) -> Literal["human_escalation", "finalize"]:
    """
    Feltételes él: routing az active_agent alapján.
    
    Ez demonstrálja az állapot-vezérelt routing-ot.
    """
    if state["active_agent"] == "HUMAN":
        return "human_escalation"
    else:
        return "finalize"


def human_escalation_agent(state: SupportState) -> SupportState:
    """
    Emberi eszkalációs ágens felkészíti az ügyet az emberi átadásra.
    """
    state["trace"].append(TraceEvent.node_start("human_escalation_agent"))
    
    message = state["messages"][-1]["content"]
    
    # Ügybriefing generálása
    context = {
        "category": state["ticket"].category if state.get("ticket") else "Ismeretlen",
        "priority": state["ticket"].priority if state.get("ticket") else "P2",
        "sentiment": state["ticket"].sentiment if state.get("ticket") else "neutral",
        "handoff_reason": "Szabály trigger észlelve",
        "sources": state.get("sources", []),
    }
    
    case_brief = generate_case_brief(message, context)
    
    # Agent assist generálása az emberi ügynök számára
    state["agent_assist"] = AgentAssistOutput(
        draft_reply=f"Ezt az ügyet emberi felülvizsgálatra eszkaláltuk...",
        case_summary=[
            f"Eszkalált {state['ticket'].category} ügy",
            f"Prioritás: {state['ticket'].priority}",
            "Emberi felülvizsgálat szükséges szabály trigger miatt",
        ],
        next_actions=[
            "Ügybriefing és ügyfélelőzmények áttekintése",
            "Ügyfélazonosság és fiók részletek ellenőrzése",
            "Helyzet értékelése szabályzati irányelvek szerint",
            "Személyre szabott megoldás nyújtása",
        ],
    )
    
    state["final_answer"] = f"""Ez az ügy emberi segítséget igényel.

**Ügybriefing:**
{case_brief}

Prioritás: {state['ticket'].priority if state.get('ticket') else 'P2'}"""
    
    state["trace"].append(TraceEvent.node_end("human_escalation_agent"))
    return state


def create_handoffs_graph() -> StateGraph:
    """
    Handoffs minta gráf létrehozása.
    
    Kulcs koncepciók:
    - Állapot-vezérelt agent váltás (active_agent mező)
    - Handoff események a trace-ben
    - Szabály-alapú eszkaláció
    - Esetbriefing generálás emberi ügynököknek
    """
    graph = StateGraph(SupportState)
    
    # Node-ok hozzáadása
    graph.add_node("self_service", self_service_agent)
    graph.add_node("check_handoff", check_handoff_needed)
    graph.add_node("human_escalation", human_escalation_agent)
    graph.add_node("finalize", finalize_response)
    
    # Belépési pont
    graph.set_entry_point("self_service")
    
    # Folyamat: self_service -> check_handoff
    graph.add_edge("self_service", "check_handoff")
    
    # Feltételes routing active_agent alapján
    graph.add_conditional_edges(
        "check_handoff",
        route_by_agent,
        {
            "human_escalation": "human_escalation",
            "finalize": "finalize",
        }
    )
    
    # Mindkét útvonal véget ér
    graph.add_edge("human_escalation", END)
    graph.add_edge("finalize", END)
    
    return graph
```

### Átadási Szabályok

```python
# backend/app/domain/policies.py

ESCALATION_KEYWORDS = {
    "refund_dispute": ["visszatérítés", "vita", "visszaterhelés"],
    "legal_threat": ["ügyvéd", "jogi lépések", "beperel"],
    "account_takeover": ["feltörték", "jogosulatlan hozzáférés"],
    "payment_fraud": ["csalás", "jogosulatlan díj"],
}

def check_handoff_policy(message: str, sentiment: Optional[str] = None) -> Optional[HandoffPolicy]:
    """
    Ellenőrzi, hogy az üzenet indít-e emberi átadást a szabályok alapján.
    """
    message_lower = message.lower()
    
    # Jogi fenyegetés ellenőrzése
    if any(kw in message_lower for kw in ESCALATION_KEYWORDS["legal_threat"]):
        return HandoffPolicy(
            trigger="legal_threat",
            reason="Jogi fenyegetés észlelve - azonnali eszkaláció szükséges",
            priority="P0"
        )
    
    # Magas negatív hangulat + sürgősség
    if sentiment == "negative":
        urgent_keywords = ["sürgős", "azonnal", "most", "vészhelyzet"]
        if any(kw in message_lower for kw in urgent_keywords):
            return HandoffPolicy(
                trigger="high_urgency_negative",
                reason="Magas sürgősségű negatív hangulat",
                priority="P1"
            )
    
    return None
```

### Mikor használjuk?
- ✅ Eszkalációs munkafolyamatok
- ✅ Többszintű támogatási rendszerek
- ✅ Szabály-alapú agent váltás szükséges

---

## 4. Skills Minta

### Koncepció

**On-demand kontextus betöltés, 1 agent vezérel**

Egyetlen vezérlő ágens "skill"-eket aktivál igény szerint. Minden skill egy kontextus-betöltő függvény (KB, ügyfél adat, stb.).

### Főbb jellemzők:
- ✅ **Kevesebb agent-hívás**: Hatékony erőforrás-felhasználás
- ✅ **"Context engineering" fókusz**: Csak a szükséges kontextust tölti be
- ✅ **Jó kompromisszum költségre**: Költséghatékony megközelítés

### Implementáció

```python
# backend/app/application/orchestration/patterns/skills.py

def assess_needs(state: SupportState) -> SupportState:
    """
    Felmér, mely skill-ek/kontextusok szükségesek.
    
    Ez a node elemzi a kérést és eldönti, mely skill-eket aktiválja.
    """
    state["trace"].append(TraceEvent.node_start("assess_needs"))
    
    message = state["messages"][-1]["content"]
    message_lower = message.lower()
    
    # Szükséges skill-ek meghatározása
    needs = {
        "kb_skill": False,
        "customer_skill": False,
        "ticketing_skill": False,
    }
    
    # KB skill mindig tudás-alapú kérdéseknél
    if any(kw in message_lower for kw in ["hogyan", "mi", "miért", "magyarázd", "szabályzat"]):
        needs["kb_skill"] = True
    
    # Ügyfél skill ha van customer ID vagy fiók-kapcsolatos
    if state.get("customer_id") or any(kw in message_lower for kw in ["fiók", "rendelés", "az én"]):
        needs["customer_skill"] = True
    
    # Ticketing skill problémák követéséhez
    if any(kw in message_lower for kw in ["probléma", "segítség", "támogatás"]):
        needs["ticketing_skill"] = True
    
    # Alapértelmezetten minden skill, ha bizonytalan
    if not any(needs.values()):
        needs = {"kb_skill": True, "customer_skill": True, "ticketing_skill": True}
    
    # Értékelés tárolása
    state["routing_decision"] = ",".join([k for k, v in needs.items() if v])
    
    state["trace"].append(TraceEvent.node_end("assess_needs", {
        "skills_needed": state["routing_decision"]
    }))
    
    return state


def kb_skill(state: SupportState) -> SupportState:
    """
    KB skill: Tudásbázis kontextus betöltése.
    
    Ez demonstrálja az on-demand kontextus betöltést - KB csak ha szükséges.
    """
    state["trace"].append(TraceEvent.node_start("kb_skill"))
    
    message = state["messages"][-1]["content"]
    
    # KB cikkek lekérése
    state["trace"].append(TraceEvent.tool_call("kb_tool"))
    articles, kb_event = retrieve_kb_articles(message, top_k=3)
    state["trace"].append(kb_event)
    state["sources"].extend(format_kb_sources(articles))
    
    # KB tartalom tárolása későbbi szintézishez
    kb_content = "\n".join([
        f"[{a['id']}] {a['title']}: {a['content']}"
        for a in articles
    ])
    
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["kb_skill"] = kb_content
    
    state["trace"].append(TraceEvent.tool_result("kb_tool", {
        "articles_count": len(articles)
    }))
    state["trace"].append(TraceEvent.node_end("kb_skill"))
    
    return state


def customer_skill(state: SupportState) -> SupportState:
    """
    Ügyfél skill: Ügyfél kontextus betöltése.
    
    Ez demonstrálja az on-demand kontextus betöltést - ügyfél adat csak ha szükséges.
    """
    state["trace"].append(TraceEvent.node_start("customer_skill"))
    
    # Ügyfél kontextus lekérése
    state["trace"].append(TraceEvent.tool_call("customer_tool"))
    customer, customer_event = get_customer_context(state.get("customer_id"))
    state["trace"].append(customer_event)
    
    # Ügyfél kontextus tárolása
    if customer:
        state["customer_tier"] = customer.get("sla_tier", "Standard")
        customer_info = format_customer_context(customer)
    else:
        customer_info = "Névtelen ügyfél (nincs fiók információ)"
    
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["customer_skill"] = customer_info
    
    state["trace"].append(TraceEvent.tool_result("customer_tool"))
    state["trace"].append(TraceEvent.node_end("customer_skill"))
    
    return state


def synthesize_with_skills(state: SupportState) -> SupportState:
    """
    Végső válasz szintézise a betöltött skill-ek/kontextus használatával.
    
    Ez a node demonstrálja, hogyan kombinálódnak a skill-ekből származó kontextusok.
    """
    state["trace"].append(TraceEvent.node_start("synthesize_with_skills"))
    
    llm = OpenAIProvider()
    message = state["messages"][-1]["content"]
    
    # Összes skill kimenet összegyűjtése
    skills_used = state.get("specialist_results", {})
    
    # Kontextus építése skill-ekből
    context_parts = []
    
    if "kb_skill" in skills_used:
        context_parts.append(f"Tudásbázis:\n{skills_used['kb_skill']}")
    
    if "customer_skill" in skills_used:
        context_parts.append(f"Ügyfél Kontextus:\n{skills_used['customer_skill']}")
    
    if "ticketing_skill" in skills_used:
        context_parts.append(f"Ticket Státusz:\n{skills_used['ticketing_skill']}")
    
    context = "\n\n".join(context_parts) if context_parts else "Nincs további kontextus"
    
    # Válasz generálása skill-ek használatával
    prompt = f"""Ügyfélszolgálati ágens vagy skill-alapú kontextussal.

Ügyfél kérdés: {message}

Elérhető Kontextus:
{context}

Adj hasznos, pontos választ a betöltött kontextus használatával."""
    
    answer = llm.chat_completion([{"role": "user", "content": prompt}])
    state["final_answer"] = answer
    
    state["trace"].append(TraceEvent.node_end("synthesize_with_skills", {
        "skills_used": list(skills_used.keys())
    }))
    
    return state


def create_skills_graph() -> StateGraph:
    """
    Skills minta gráf létrehozása.
    
    Kulcs koncepciók:
    - On-demand kontextus betöltés (skill-ek csak szükség esetén aktiválódnak)
    - Értékelő node dönti el, mely skill-ek szükségesek
    - Tool hívások minden skill-nél jól láthatók a trace-ben
    - Szintézis csak a betöltött kontextust használja
    """
    graph = StateGraph(SupportState)
    
    # Node-ok hozzáadása
    graph.add_node("assess_needs", assess_needs)
    graph.add_node("kb_skill", kb_skill)
    graph.add_node("customer_skill", customer_skill)
    graph.add_node("ticketing_skill", ticketing_skill)
    graph.add_node("synthesize", synthesize_with_skills)
    
    # Belépési pont
    graph.set_entry_point("assess_needs")
    
    # Egyszerű lineáris folyamat demo céljából
    # (Production környezetben ez feltételes lenne)
    graph.add_edge("assess_needs", "kb_skill")
    graph.add_edge("kb_skill", "customer_skill")
    graph.add_edge("customer_skill", "ticketing_skill")
    graph.add_edge("ticketing_skill", "synthesize")
    graph.add_edge("synthesize", END)
    
    return graph
```

### Mikor használjuk?
- ✅ Költségoptimalizálás fontos
- ✅ Változó kontextus-szükséglet
- ✅ Hatékony erőforrás-felhasználás szükséges

---

## 5. Custom Workflow Minta

### Koncepció

**Determinista + agentikus node-ok LangGraphban**

Rögzített folyamat determinisztikus lépésekkel (pl. tisztítás, entitás-kinyerés) és agentikus node-okkal (LLM-alapú döntések). Tartalmaz rekurzió-kontrollt.

### Főbb jellemzők:
- ✅ **Explicit kontroll és auditálhatóság**: Minden lépés követhető
- ✅ **Bármely mintát beágyazhatsz**: Rugalmas kombináció
- ✅ **Prod-ready struktúra**: Éles környezetre kész

### Implementáció

```python
# backend/app/application/orchestration/patterns/custom_workflow.py

def sanitize_input(state: SupportState) -> SupportState:
    """
    Bemenet tisztítása.
    
    Első determinisztikus lépés a pipeline-ban.
    """
    state["trace"].append(TraceEvent.node_start("sanitize_input"))
    
    message = state["messages"][-1]["content"]
    
    # Alap tisztítás (felesleges szóközök eltávolítása, stb.)
    sanitized = re.sub(r'\s+', ' ', message).strip()
    
    # Üzenet frissítése
    state["messages"][-1]["content"] = sanitized
    
    state["trace"].append(TraceEvent.node_end("sanitize_input", {
        "original_length": len(message),
        "sanitized_length": len(sanitized)
    }))
    
    return state


def extract_entities(state: SupportState) -> SupportState:
    """
    Entitások kinyerése az üzenetből.
    
    Második determinisztikus lépés - rendelés ID-k, email-ek, hibakódok kinyerése.
    """
    state["trace"].append(TraceEvent.node_start("extract_entities"))
    
    message = state["messages"][-1]["content"]
    
    entities = {}
    
    # Rendelés ID-k kinyerése (formátum: ORD-XXXX)
    order_ids = re.findall(r'ORD-\d+', message, re.IGNORECASE)
    if order_ids:
        entities["order_ids"] = order_ids
    
    # Email-ek kinyerése
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message)
    if emails:
        entities["emails"] = emails
    
    # Hibakódok kinyerése
    error_codes = re.findall(r'(?:ERR|ERROR|HIBA)[-\s]?\d+', message, re.IGNORECASE)
    if error_codes:
        entities["error_codes"] = error_codes
    
    # Entitások tárolása állapotban
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["entities"] = entities
    
    state["trace"].append(TraceEvent.node_end("extract_entities", {"entities": entities}))
    
    return state


def draft_reply(state: SupportState) -> SupportState:
    """
    Kezdeti válasz draft (agentikus node).
    
    Ötödik lépés - LLM generál draft választ.
    Ez demonstrálja a rekurziót: a draft revízióra szorulhat.
    """
    state["trace"].append(TraceEvent.node_start("draft_reply"))
    
    # Rekurzió mélység növelése
    state["recursion_depth"] = state.get("recursion_depth", 0) + 1
    
    llm = OpenAIProvider()
    message = state["messages"][-1]["content"]
    kb_content = state.get("specialist_results", {}).get("kb_content", "")
    category = state["ticket"].category if state.get("ticket") else "Általános"
    
    prompt = f"""Ügyfélszolgálati válasz draft készítése ehhez a {category} kéréshez.

Ügyfél üzenet: {message}

Tudásbázis:
{kb_content}

Írj hasznos, professzionális választ. Hivatkozz KB cikkekre, ha releváns."""
    
    draft = llm.chat_completion([{"role": "user", "content": prompt}])
    
    # Draft tárolása
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["draft"] = draft
    
    state["trace"].append(TraceEvent.node_end("draft_reply", {
        "draft_length": len(draft),
        "recursion_depth": state["recursion_depth"]
    }))
    
    return state


def policy_check(state: SupportState) -> SupportState:
    """
    Draft ellenőrzése szabályzatokkal szemben.
    
    Hatodik lépés - validálja a draft szabályzat-megfelelőségét.
    """
    state["trace"].append(TraceEvent.node_start("policy_check"))
    
    draft = state.get("specialist_results", {}).get("draft", "")
    message = state["messages"][-1]["content"]
    
    # Szabályzat sértések ellenőrzése a draft-ban
    violations = []
    
    # Ne ígérj visszatérítést jóváhagyás nélkül
    if "visszatérítés" in draft.lower() and "vezető" not in draft.lower():
        if any(kw in message.lower() for kw in ["visszatérítés", "pénz vissza"]):
            violations.append("refund_promise")
    
    # Ne ossz meg személyes adatokat
    if any(pattern in draft.lower() for pattern in ["jelszó:", "jelszavad", "ssn", "hitelkártya"]):
        violations.append("data_exposure")
    
    # Professzionális hangnem biztosítása
    if any(word in draft.lower() for word in ["hülye", "idióta", "ostoba"]):
        violations.append("unprofessional_tone")
    
    # Szabályzat ellenőrzés eredmény tárolása
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["policy_violations"] = violations
    state["specialist_results"]["policy_passed"] = len(violations) == 0
    
    state["trace"].append(TraceEvent.node_end("policy_check", {
        "violations": violations,
        "passed": len(violations) == 0
    }))
    
    return state


def route_after_policy(state: SupportState) -> Literal["revise_draft", "finalize_workflow"]:
    """
    Feltételes él: revízió ha szabálysértések vannak, különben véglegesítés.
    
    Ez demonstrálja a rekurzió-kontrollt a custom workflow-ban.
    """
    violations = state.get("specialist_results", {}).get("policy_violations", [])
    recursion_depth = state.get("recursion_depth", 0)
    
    # Rekurzió limit ellenőrzése (végtelen ciklusok megelőzése)
    if recursion_depth >= 3:
        # Rekurzió limit elérve - folytatás sértésekkel is
        state["trace"].append(TraceEvent.node_start("recursion_limit_check"))
        state["trace"].append(TraceEvent.node_end("recursion_limit_check", {
            "reason": "Maximális rekurzió mélység elérve",
            "depth": recursion_depth
        }))
        return "finalize_workflow"
    
    # Ha vannak sértések, revízió
    if violations:
        return "revise_draft"
    else:
        return "finalize_workflow"


def revise_draft(state: SupportState) -> SupportState:
    """
    Draft revíziója a szabálysértések javításához.
    
    Ez a node demonstrálja a rekurziót - visszafolyik a policy_check-be.
    """
    state["trace"].append(TraceEvent.node_start("revise_draft"))
    
    llm = OpenAIProvider()
    draft = state.get("specialist_results", {}).get("draft", "")
    violations = state.get("specialist_results", {}).get("policy_violations", [])
    
    prompt = f"""Javítsd ezt az ügyfélszolgálati draft-ot a szabálysértések kijavításához.

Eredeti draft:
{draft}

Talált szabálysértések:
{', '.join(violations)}

Irányelvek:
- Ne ígérj visszatérítést vezető jóváhagyása nélkül
- Soha ne ossz meg érzékeny ügyfél adatokat
- Tartsd fenn a professzionális hangnemet
- Légy empatikus és segítőkész

Javított draft:"""
    
    revised = llm.chat_completion([{"role": "user", "content": prompt}])
    
    # Draft frissítése
    state["specialist_results"]["draft"] = revised
    
    state["trace"].append(TraceEvent.node_end("revise_draft", {
        "violations_fixed": violations
    }))
    
    return state


def create_custom_workflow_graph() -> StateGraph:
    """
    Custom Workflow minta gráf létrehozása.
    
    Kulcs koncepciók:
    - Determinisztikus pipeline (sanitize → extract → triage → retrieve → draft → policy → finalize)
    - Agentikus node-ok (draft_reply LLM-et használ)
    - Rekurzió limit-tel (draft → policy → revise → policy, max 3 iteráció)
    - Reducerek (messages append, sources unique merge, trace append)
    - Rekurzió mélység követése állapotban
    """
    graph = StateGraph(SupportState)
    
    # Minden node hozzáadása
    graph.add_node("sanitize", sanitize_input)
    graph.add_node("extract_entities", extract_entities)
    graph.add_node("triage", triage_request)
    graph.add_node("retrieve_kb", retrieve_knowledge)
    graph.add_node("draft", draft_reply)
    graph.add_node("policy_check", policy_check)
    graph.add_node("revise", revise_draft)
    graph.add_node("finalize", finalize_workflow)
    
    # Belépési pont
    graph.set_entry_point("sanitize")
    
    # Determinisztikus pipeline
    graph.add_edge("sanitize", "extract_entities")
    graph.add_edge("extract_entities", "triage")
    graph.add_edge("triage", "retrieve_kb")
    graph.add_edge("retrieve_kb", "draft")
    graph.add_edge("draft", "policy_check")
    
    # Feltételes él: policy check → revise vagy finalize
    graph.add_conditional_edges(
        "policy_check",
        route_after_policy,
        {
            "revise_draft": "revise",
            "finalize_workflow": "finalize",
        }
    )
    
    # Rekurzió: revise → policy_check (ciklus létrehozása)
    graph.add_edge("revise", "policy_check")
    
    # Finalize a végponthoz
    graph.add_edge("finalize", END)
    
    return graph
```

### Rekurzió Limit Demonstráció

A Custom Workflow minta legfontosabb tulajdonsága a **rekurzió kontroll**:

1. **Rekurzió mélység követése**: `state["recursion_depth"]` számláló
2. **Maximum iterációk**: 3 revízió megengedett
3. **Végtelen ciklus védelem**: Limit után kilépés, még ha vannak sértések is
4. **Trace láthatóság**: Minden iterációnál rögzítve van a mélység

```python
# Rekurzió példa trace kimenet:
# 1. draft_reply (recursion_depth=1)
# 2. policy_check (violations=["refund_promise"])
# 3. revise_draft (fixing violations)
# 4. policy_check (recursion_depth=2, violations=[])
# 5. finalize_workflow
```

### Mikor használjuk?
- ✅ Auditálhatóság kritikus
- ✅ Rögzített folyamat lépések szükségesek
- ✅ Éles környezetre optimalizált struktúra kell

---

## Shared State és Reducerek

### Állapot Definíció

```python
# backend/app/domain/state.py

from typing import List, Optional, Annotated
from typing_extensions import TypedDict
from operator import add

class SupportState(TypedDict):
    """
    Megosztott állapot a support agent workflow-khoz.
    
    Ez az állapot minden node között megosztott a LangGraph workflow-ban.
    A reducerek definiálják, hogyan egyesülnek az állapot frissítések.
    """
    
    # Messages az 'add' reducer-t használja - új üzenetek hozzáfűződnek
    messages: Annotated[List[dict], add]
    
    # Végrehajtott minta
    selected_pattern: str
    
    # Aktív ágens (handoff minta használja)
    active_agent: Optional[str]
    
    # Ticket triage eredmény
    ticket: Optional[TicketTriage]
    
    # Agent assist kimenet
    agent_assist: Optional[AgentAssistOutput]
    
    # Tudásforrások - egyedi merge_sources reducer használja deduplikáláshoz
    sources: Annotated[List[str], merge_sources]
    
    # Trace események - időrendben hozzáfűzve
    trace: Annotated[List[TraceEvent], add]
    
    # Rekurzió mélység számláló (custom workflow)
    recursion_depth: int
    
    # Ügyfél kontextus (opcionális)
    customer_id: Optional[str]
    customer_tier: Optional[str]
    
    # Csatorna (chat, email, stb.)
    channel: str
    
    # Végső válasz
    final_answer: Optional[str]
```

### Egyedi Reducer

```python
def merge_sources(existing: List[str], new: List[str]) -> List[str]:
    """
    Reducer a forrásokhoz: egyesítés és deduplikálás.
    
    Ez demonstrál egy egyedi reducer-t, amely egyedi forrásokat tart fenn
    miközben megőrzi a megjelenési sorrendet.
    """
    seen = set(existing)
    result = existing.copy()
    
    for source in new:
        if source not in seen:
            result.append(source)
            seen.add(source)
    
    return result
```

### Reducer Magyarázat

**Build-in Reducerek:**
- `add` (operator): Listához hozzáfűz (append)
- Példa: `messages: Annotated[List[dict], add]`

**Egyedi Reducerek:**
- `merge_sources`: Deduplikálja a forrásokat
- Példa: `sources: Annotated[List[str], merge_sources]`

**Miért fontosak?**
- ✅ Több node frissítheti ugyanazt a mezőt
- ✅ LangGraph automatikusan egyesíti a frissítéseket
- ✅ Elkerüli az állapot felülírási konfliktusokat

---

## Mintakombinációk

### Ajánlott Kombinációk

A "Megjegyzés" szerint: **A minták keverhetők. A jó architektúra gyakran 2-3 mintát kombinál.**

#### Kombináció 1: Router + Skills
```
Router osztályozás → Skills betölti kontextust → Válasz
```
**Előny**: Specializált routing + hatékony kontextus betöltés

#### Kombináció 2: Handoffs + Custom Workflow
```
Custom workflow pipeline → Handoff policy check → Eszkaláció vagy befejezés
```
**Előny**: Strukturált folyamat + rugalmas eszkaláció

#### Kombináció 3: Router + Skills + Custom Workflow
```
Custom workflow előfeldolgozás → Router osztályozás → Skills kontextus → Szintézis
```
**Előny**: Teljes kontroll + specializáció + hatékonyság

---

## Graph Factory

### Minta Kiválasztás

```python
# backend/app/application/orchestration/graph_factory.py

class GraphFactory:
    """Factory LangGraph workflow-k létrehozásához minta kiválasztás alapján."""
    
    @staticmethod
    def create(pattern: PatternType) -> StateGraph:
        """
        Összeállított gráf létrehozása a megadott mintához.
        """
        if pattern == "router":
            graph = create_router_graph()
        elif pattern == "subagents":
            graph = create_subagents_graph()
        elif pattern == "handoffs":
            graph = create_handoffs_graph()
        elif pattern == "skills":
            graph = create_skills_graph()
        elif pattern == "custom_workflow":
            graph = create_custom_workflow_graph()
        else:
            raise ValueError(f"Ismeretlen minta: {pattern}")
        
        # Gráf összeállítása
        compiled = graph.compile()
        
        return compiled
```

---

## Összefoglalás

| Minta | Mikor használd | Főbb előny | LangGraph feature |
|-------|----------------|------------|-------------------|
| **Router** | Több domain, párhuzamos végrehajtás | Specializáció | Send (fan-out) |
| **Subagents** | Központi koordináció | Egyszerű UX | Tool calling |
| **Handoffs** | Eszkaláció, többszintű támogatás | Szabály-alapú váltás | State routing |
| **Skills** | Költségoptimalizálás | Hatékonyság | On-demand loading |
| **Custom Workflow** | Auditálhatóság, prod környezet | Explicit kontroll | Recursion limit |

### Következő lépések

1. **Próbáld ki a mintákat**: Indítsd el az alkalmazást és teszteld mindegyik mintát
2. **Vizsgáld meg a trace-t**: Figyeld meg, hogyan hajtódnak végre a node-ok
3. **Módosítsd a kódot**: Adj hozzá saját node-okat vagy tool-okat
4. **Kombináld a mintákat**: Hozz létre hibrid megközelítést

---

**Oktatási célra készült:** Robot Dreams - Multi-Agent Rendszerek kurzus
