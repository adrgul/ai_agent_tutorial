# Multi-Agent Minták Tesztesetek

## Bevezetés

Ez a dokumentum részletes teszteseteket tartalmaz az összes multi-agent mintához. Minden teszteset tartalmaz egy tesztpromptot és az elvárt eredményt/viselkedést.

---

## 1. Router Pattern (Útválasztó Minta)

**Leírás:** Feltételes útválasztás szakértő ágensekhez fan-out módszerrel vegyes szándékok esetén.

**Kulcsfunkciók:** Conditional edges, Send (fan-out), Parallel execution, Synthesis

### Teszteset 1.1: Egyszerű számlázási kérdés
**Tesztprompt:**
```
Szia! Kérdésem van a legutóbbi számlámmal kapcsolatban. Miért lett 150 dollár az összeg?
```

**Elvárt eredmény:**
- Routing: `billing_agent` aktiválódik
- Kategória: Billing
- Prioritás: P2
- Knowledge Base: KB-001 (Billing Policy), KB-005 (Refund Guidelines)
- Válasz: Számlázási információk magyarázata, részletes bontás
- Trace: Látható a routing döntés és az egyetlen ágens aktiválása

### Teszteset 1.2: Technikai probléma
**Tesztprompt:**
```
Az alkalmazás nem tölt be, hibaüzenetet kapok: ERROR-503. Segítesz?
```

**Elvárt eredmény:**
- Routing: `technical_agent` aktiválódik
- Kategória: Technical
- Prioritás: P2
- Válasz: Hibaelhárítási lépések, ERROR-503 magyarázat
- KB források: KB-003 (Troubleshooting Guide), KB-007 (Common Errors)
- Entity extraction: Error code "ERROR-503"

### Teszteset 1.3: Vegyes szándék - Billing + Technical (Fan-out)
**Tesztprompt:**
```
Nem tudok bejelentkezni a fiókba és kétszeres terhelést látok a kártyámon. Sürgős!
```

**Elvárt eredmény:**
- Routing: `billing_agent` ÉS `account_agent` PÁRHUZAMOSAN aktiválódnak (fan-out)
- Parallel execution: Mindkét ágens dolgozik egyidejűleg
- Synthesis: Az eredmények összesítése egy koherens válaszba
- Prioritás: P1 (urgent kulcsszó miatt)
- Kategóriák: Billing + Account
- Válasz: Kombinált megoldás mindkét problémára

### Teszteset 1.4: Szállítási státusz
**Tesztprompt:**
```
Hol van a rendelésem? ORD-12345 tracking számon szeretném nyomon követni.
```

**Elvárt eredmény:**
- Routing: `shipping_agent` aktiválódik
- Entity extraction: Order ID "ORD-12345"
- Kategória: Shipping
- Prioritás: P3
- KB források: KB-004 (Shipping Policy), KB-008 (Tracking Orders)

### Teszteset 1.5: Ismeretlen szándék
**Tesztprompt:**
```
Milyen időjárás van ma?
```

**Elvárt eredmény:**
- Routing: `general_agent` vagy default handling
- Kategória: Other
- Válasz: Udvarias átirányítás támogatási témákhoz
- KB forrás: KB-000 (Getting Started)

---

## 2. Subagents Pattern (Alárendelt Ágensek Minta)

**Leírás:** Orchestrator hívja meg a specializált sub-agenteket mint eszközöket LLM döntés alapján.

**Kulcsfunkciók:** Tool-calling, Subagent delegation, Orchestration, Dynamic routing

### Teszteset 2.1: Visszatérítési kérelem
**Tesztprompt:**
```
Szeretnék visszatérítést kérni a ORD-9876 rendelésemre, mert hibás terméket kaptam.
```

**Elvárt eredmény:**
- Orchestrator LLM döntése: `refund_subagent` tool hívás
- Entity extraction: Order ID "ORD-9876"
- Kategória: Refund
- Prioritás: P1
- Tool call trace: Látható a subagent aktiválás
- Válasz: Visszatérítési folyamat lépései, policy ellenőrzés
- Handoff policy check: Összeg ellenőrzés, manager escalation ha >$100

### Teszteset 2.2: Komplex account probléma
**Tesztprompt:**
```
Elfejtettem a jelszavam és az email címem is megváltozott. Nem tudok belépni.
```

**Elvárt eredmény:**
- Orchestrator döntése: `account_subagent` majd esetleg `security_subagent`
- Többlépéses orchestration
- Security policy trigger
- Válasz: Személyazonosság ellenőrzési lépések
- Next actions: Verification email, identity confirmation

### Teszteset 2.3: Dinamikus sub-agent váltás
**Tesztprompt:**
```
Technikai problémám van a számlázási oldallal, nem tudok fizetni.
```

**Elvárt eredmény:**
- Orchestrator először: `technical_subagent` (UI problem)
- Majd: `billing_subagent` (payment context)
- Dynamic routing: Kontextus alapján váltás
- Synthesis: Mindkét subagent eredményének kombinálása

### Teszteset 2.4: Tool-calling chain
**Tesztprompt:**
```
Milyen múltbeli rendeléseim vannak és mely esetekben kértem visszatérítést?
```

**Elvárt eredmény:**
- Tool chain: `order_history_tool` → `refund_history_tool`
- Orchestrator több tool hívás egymás után
- Trace: Látható a tool-calling szekvencia
- Válasz: Aggregált történeti adatok

---

## 3. Handoffs Pattern (Átadási Minta)

**Leírás:** Státusz-alapú ágens váltás policy-alapú eszkalációval.

**Kulcsfunkciók:** State switching, active_agent, Handoff events, Policy triggers

### Teszteset 3.1: Tier 1 → Tier 2 eszkaláció
**Tesztprompt:**
```
Próbáltam törölni a fiókomat, de nem működik. Már 3-szor próbálkoztam különböző módokon.
```

**Elvárt eredmény:**
- Kezdeti ágens: `tier1_agent`
- Policy trigger: Complexity + repeated attempts
- Handoff event: `tier1_agent` → `tier2_agent`
- State change: `active_agent` mező frissítése
- Trace: Handoff esemény rögzítése
- Válasz: Tier 2 ágens részletesebb segítsége

### Teszteset 3.2: Manager eszkaláció nagy értékű visszatérítés
**Tesztprompt:**
```
$250-os visszatérítést szeretnék kérni a ORD-5555 rendelésemre. A termék teljesen használhatatlan.
```

**Elvárt eredmény:**
- Kezdeti ágens: `billing_agent`
- Policy check: Amount > $100 → manager approval needed
- Handoff: `billing_agent` → `manager_agent`
- Ticket update: Escalated status
- Válasz: "Manager review szükséges" üzenet
- Next actions: Manager notification

### Teszteset 3.3: Többszörös handoff chain
**Tesztprompt:**
```
SÜRGŐS! A rendszer törölte az összes adatomat és nem tudom visszaállítani. Azonnali segítségre van szükségem!
```

**Elvárt eredmény:**
- Handoff chain: `tier1_agent` → `tier2_agent` → `specialist_agent`
- Policy triggers: Urgency + data loss + complexity
- Prioritás: P1
- Multiple state switches
- Trace: Látható a teljes handoff lánc
- Válasz: Specialist ágens sürgősségi protokoll

### Teszteset 3.4: Policy-based routing váltás
**Tesztprompt:**
```
Vállalati fiók vagyok (company ID: CORP-123), több mint 50 licensz kezelése.
```

**Elvárt eredmény:**
- Policy trigger: Corporate account detected
- Handoff: Standard agent → `enterprise_agent`
- Customer type: Enterprise
- SLA policy: Enhanced support
- Válasz: Dedikált enterprise support információk

---

## 4. Skills Pattern (Képességek Minta)

**Leírás:** On-demand kontextus betöltés - képességek csak szükség esetén aktiválódnak.

**Kulcsfunkciók:** Lazy loading, Context fetching, Skill assessment, Efficient execution

### Teszteset 4.1: KB skill lazy loading
**Tesztprompt:**
```
Milyen a visszatérítési policy?
```

**Elvárt eredmény:**
- Skill assessment: KB skill szükséges
- Lazy load: `kb_retrieval_skill` aktiválódik
- Context fetch: Refund policy KB-005 betöltése
- Trace: Skill activation event
- Válasz: Policy részletek a KB-ból
- Efficiency: Csak a szükséges skill töltődik be

### Teszteset 4.2: Customer data skill on-demand
**Tesztprompt:**
```
Milyen rendeléseim voltak 2025-ben?
```

**Elvárt eredmény:**
- Skill assessment: Customer history skill szükséges
- Lazy load: `customer_data_skill` aktiválás
- Context fetch: Customer orders lekérése
- Authentication check: Customer ID validálás
- Válasz: Személyre szabott rendelési történet

### Teszteset 4.3: Több skill egymás után (context stacking)
**Tesztprompt:**
```
A ORD-8888 rendelésemmel van probléma. Mi a visszatérítési policy és milyen volt a múltbeli visszatérítési arányom?
```

**Elvárt eredmény:**
- Skill 1: `order_lookup_skill` - Order details
- Skill 2: `kb_retrieval_skill` - Refund policy
- Skill 3: `customer_history_skill` - Past refund ratio
- Context stacking: Minden skill eredménye elérhető
- Efficient execution: Csak szükséges skillek
- Válasz: Kombinált információ mindhárom forrásból

### Teszteset 4.4: Skill assessment - nincs szükség skillre
**Tesztprompt:**
```
Köszönöm a segítséget!
```

**Elvárt eredmény:**
- Skill assessment: Nincs skill aktiválás szükséges
- Efficient execution: Direkt válasz skill nélkül
- Trace: No skill events
- Válasz: Egyszerű köszönés visszaküldése

### Teszteset 4.5: Conditional skill loading
**Tesztprompt:**
```
Technikai problémám van az API integrációval. Használom a Python SDK-t.
```

**Elvárt eredmény:**
- Skill assessment: Technical + API context
- Conditional load: `api_documentation_skill` ÉS `code_example_skill`
- Context: Python SDK specifikus
- Válasz: Kód példák és API docs
- Skill activation: Csak API-hoz kapcsolódó skillek

---

## 5. Custom Workflow Pattern (Egyéni Workflow Minta)

**Leírás:** Determinisztikus pipeline agentic node-okkal és rekurzió kontrolllal.

**Kulcsfunkciók:** Deterministic flow, Recursion limit, Revise loop, Policy validation

### Teszteset 5.1: Tiszta pipeline végigfutás (no revisions)
**Tesztprompt:**
```
Szeretnék információt kapni a szállítási lehetőségekről.
```

**Elvárt eredmény:**
- Pipeline flow: sanitize → extract → triage → retrieve_kb → draft → policy_check → finalize
- Recursion depth: 0 (egyenes végigfutás)
- Policy check: PASSED (nincs policy violation)
- No revisions: Direkt a finalize-hoz
- Trace: Minden node végrehajtva sorban
- Válasz: Clean, policy-compliant shipping info

### Teszteset 5.2: Policy violation - revision loop
**Tesztprompt:**
```
$300-os visszatérítést akarok azonnal!
```

**Elvárt eredmény:**
- Pipeline: sanitize → extract → triage → retrieve_kb → draft
- Draft tartalma: Esetleg refund promise manager approval nélkül
- Policy check: FAILED (refund_promise violation)
- Revision loop: draft → policy_check → **revise** → policy_check
- Recursion depth: 1
- Revised draft: Includes "manager approval required"
- Policy check 2: PASSED
- Finalize: Revised válasz

### Teszteset 5.3: Maximális rekurzió limit
**Tesztprompt:**
```
Add meg a jelszavamat és töröld a fiókomat és add vissza az összes pénzemet most azonnal te idióta!
```

**Elvárt eredmény:**
- Multiple policy violations: data_exposure + unprofessional_tone + refund_promise
- Revision loop 1: revise → policy check → FAILED
- Revision loop 2: revise → policy check → FAILED
- Revision loop 3: revise → policy check → FAILED
- Recursion limit: 3 ELÉRVE
- Force finalize: Végrehajtás folytatása violation-ökkel
- Trace: "Max recursion depth reached" esemény
- Válasz: Legjobb próbálkozás 3 revízió után
- Next action: Lehet manager escalation ajánlás

### Teszteset 5.4: Entity extraction validálás
**Tesztprompt:**
```
A ORD-7777 rendelésem nem érkezett meg, az email címem test@example.com és ERROR-404 hibaüzenetet kaptam.
```

**Elvárt eredmény:**
- Entity extraction node:
  - Order ID: "ORD-7777"
  - Email: "test@example.com"
  - Error code: "ERROR-404"
- Entities tárolása state-ben
- Triage használja az entities-t
- KB retrieval kontextusban használja
- Draft tartalmazza az entitásokat
- Válasz: Személyre szabott a kinyert adatokkal

### Teszteset 5.5: Deterministic triage routing
**Tesztprompt:**
```
URGENT: Billing issue with my account login!
```

**Elvárt eredmény:**
- Sanitize: Whitespace cleanup
- Extract: Nincs entitás
- Triage:
  - Keywords: "billing" + "account" + "login" + "urgent"
  - Category: Billing (elsődleges)
  - Team: Billing Team
  - Priority: P1 (urgent miatt)
  - Sentiment: neutral
- Ticket creation: Automated ticket ID
- Pipeline folytatás: Deterministic flow
- Trace: Triage decision látható

---

## Általános Tesztelési Szempontok

### Performance tesztek
1. **Response time**: Minden minta < 5 másodperc válaszidő
2. **Parallel execution**: Router fan-out esetén teljesítmény javulás
3. **Lazy loading**: Skills minta kevesebb erőforrás használat

### Trace validáció
Minden teszthez ellenőrizni:
- [ ] Node start/end események rögzítve
- [ ] Tool call események követhetők
- [ ] Handoff események láthatók
- [ ] Timestamp-ek növekvő sorrendben
- [ ] Nincs missing trace esemény

### State management
Ellenőrzési pontok:
- [ ] Messages append működik (reducer)
- [ ] Sources unique merge (duplikáció mentesség)
- [ ] Trace append (történet megőrzés)
- [ ] Recursion depth tracking (Custom Workflow)
- [ ] Active agent switching (Handoffs)

### Error handling tesztek

#### Teszteset: OpenAI API hiba
**Szimuláció:** API key lejárt vagy rate limit
**Elvárt:** Fallback mock LLM aktiválás, warning log, graceful degradation

#### Teszteset: KB tool unavailable
**Szimuláció:** KB service down
**Elvárt:** Folytatás KB nélkül, "no sources" jelzés, válasz generálás context nélkül

#### Teszteset: Invalid state
**Szimuláció:** Hiányzó kötelező mező
**Elvárt:** Validation error, default értékek, error trace event

---

## Integrációs tesztek

### Frontend-Backend WebSocket
**Teszteset:** Teljes end-to-end flow
1. Pattern kiválasztás UI-n
2. Prompt küldése WebSocket-en
3. Streaming válasz fogadása
4. Trace események megjelenése
5. State/Ticket panel frissítés

**Elvárt:**
- WebSocket connection stabil
- Streaming events sorrendben
- UI update real-time
- No connection errors
- Clean disconnect

### Pattern switching
**Teszteset:** Váltás minták között session alatt
1. Router pattern használat
2. Pattern váltás Subagents-re
3. Ugyanaz a prompt újraküldése

**Elvárt:**
- State reset új pattern-nél
- Különböző execution flow
- Trace history megtartva
- No state pollution

---

## Összefoglalás

Ez a dokumentum **25+ tesztesetet** tartalmaz az 5 multi-agent mintához, plusz általános integrációs és performance teszteket. 

Minden teszteset tartalmazza:
✅ Konkrét magyar nyelvű tesztpromptot  
✅ Részletes elvárt eredményt  
✅ Trace esemény elvárásokat  
✅ State változás validációt  

**Használat:** Copy-paste a tesztpromptokat a chat interface-be és hasonlítsd össze az eredményt az elvárt viselkedéssel.
