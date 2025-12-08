
AI Meeting Assistant (Jegyző + Feladatkiosztó + Összegző Agent)

Koncepció:
Egy AI agent, ami meeting jegyzetből automatikusan:
  - összefoglalót készít,
  - akciópontokat (to-do-kat) gyűjt ki,
  - és elmenti azokat egy JSON-ba vagy Jira API-ba.

Előnyök:
  - Egyszerű indulás: sima TXT / transcript feldolgozása
  - LangGraph példák: document input → LLM summarization → JSON output
  - Üzleti relevancia: rengeteg startup / cég épít ilyet
  - Látványos: a hallgató végén bemutathatja, ahogy a jegyzetből AI-s „meeting summary” lesz
  - Könnyen ellenőrizhető: egységes sample input → expected output összevetés
  - Bővíthető: memóriával, feladatrögzítéssel, Slack-integrációval

Végeredmény:
„MeetingAI” néven futó agent, ami automatikusan készít:
  - meeting summary-t,
  - task listát,
  - és elmenti a feladatokat JSON formátumban.

-----------------------------------------------------------------------------------------------------------------------------

AI Support Triage & Answer Drafting Agent
(„Ügyfélszolgálati triage és válaszoló agent tudásbázissal”)

Előnyei:
- Valós üzleti igény: minden szervezetnek van support-csatornája (email, chat, ticket).
- Egységes, szintetikus adatcsomaggal tanítható és automatizáltan pontozható (nincs API-kulcs mizéria).
- Tiszta RAG-feladat: FAQ/KB cikkekből idéz (citáció), és készít struktúrált JSON választ.
- Kettős output → jól mérhető:
- Kötelező: triage (kategória, prioritás, SLA) → klasszifikációs pontozás
- Opcionális: válasz-tervezet (citációkkal) → minőség/formatum/séma ellenőrzés
- LangGraph-barát: szép pipeline (intent → retrieve → re-rank → generate → policy check).
- Könnyű demo: „Bejött egy panasz e-mail → a rendszer kategorizál, prioritást ad, és válasz-tervezetet küld hivatkozásokkal.”



Mit csinál az agent?
-Bejövő üzenet (ticket/email/chat) → szándék és kategória meghatározás
-Prioritás + SLA javaslat (pl. P1/P2, 4h/24h)
-RAG: releváns tudásbázis cikkek visszakeresése (top-k + re-rank)
-Válasz-tervezet generálása citációkkal (doc_id, chunk_id, score)




-----------------------------------------------------------------------------------------------------------------------------


AI Internal Knowledge Router & Workflow Automation Agent**

(„Vállalati belső tudásirányító + workflow-automata agent”)

Röviden:

Egy agent, amely képes:
- megnézni, hogy a felhasználó kérése milyen típusú (FAQ, HR, IT, pénzügy, jog, marketing)
- kiválasztani a megfelelő tudásbázist
- kikeresni a releváns információt RAG-gal
- végrehajtani egy workflow-lépést(pl. Jira ticket, Slack üzenet, meeting generálás, dokumentum előkeresése, approval)
- szépített, strukturált választ adni citációkkal





1. Minden cég szenved attól, hogy:
- 10 féle tudásbázis van (Confluence, PDF-ek, HR fájlok, GitHub wiki, Google Docs)
- 20 féle workflow van (IT ticket, HR request, szabadság, eszközigénylés, szerződésfeltöltés)
- az emberek nem tudják „mi hol van”
- → Ez az agent pont ezt oldja meg: felhasználó kérdez → agent tudja, „hova kell nyúlni”.

2. Technikailag:
- multi-vector store támogatás
- routing (intent → domain)
- RAG több domainre
- workflow node-ok LangGraph-ban
- JSON struktúrált output
- citációk (AI Act compliance-ready)

3. Minden fontos AI skill benne van
- RAG (multi-dataset)
- LangGraph (multi-branch workflow)
- Memory (context tracking)
- Tool calling (API-k)
- Reasoning (routing logic)
- JSON output
- Policy check & guardrails
- Prompt engineering

Demó
„Szeretnék szabadságot igényelni október 3–4-re.”
→ Agent felismeri, hogy HR domain → HR vector store → policy kihúzása → JSON reply
→ Workflow: „Generated HR request: hr_request_2025-03.json”

„Hol van a legfrissebb marketing brand guideline?”
→ Agent felismeri: marketing domain → marketing KB → idéz → linket ad

„Nem működik a VPN”
→ Agent: IT → KB → citációk → draft ticket JSON


-----------------------------------------------------------------------------------------------------------------------------
