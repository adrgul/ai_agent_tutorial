# AI Chat Console - OpenAI Chat Interface

**Házi Feladat #1 - Alapozó gyakorlat**

Ez a projekt a **3. AI Internal Knowledge Router & Workflow Automation Agent** feladat előkészítése. 

Ebben az első lépésben egy egyszerű chat interfészt implementálunk, amely később kibővíthető:
- Multi-domain routing (HR, IT, Finance, Legal, Marketing)
- Vector adatbázis (RAG)
- LangChain + LangGraph workflow
- Automatizált workflow végrehajtás

---

Egyszerű konzol alapú chat alkalmazás OpenAI modellel.

## Leírás

Ez a projekt egy alapvető chat interfészt biztosít, amely közvetlenül az OpenAI API-t használja. A felhasználó kérdéseket tehet fel a konzolban, és azonnal megkapja a válaszokat.

## Követelmények

- Docker és Docker Compose
- OpenAI API kulcs

## Gyors Indítás

### 1. Környezeti változók beállítása

```bash
cd mini_projects/istvan.hadhazi/hf1
cp env.example .env
```

Szerkeszd a `.env` fájlt és add meg az OpenAI API kulcsodat:

```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

### 2. Indítás Docker-rel

**Helyes módszer (interaktív mód):**

```bash
docker-compose run --rm chat
```

**FONTOS:** Ne használd a `docker-compose up` parancsot, mert az nem biztosít interaktív terminált!

**Alternatív módszer:**

```bash
# Build
docker-compose build

# Futtatás interaktív móddal
docker run -it --rm --env-file .env ai-chat-console python chat.py
```

### 3. Egyszerű futtatás Makefile-lal

```bash
# Első indítás
make run

# Vagy build külön, aztán futtatás
make build
make run
```

### 4. Indítás lokálisan (Python)

```bash
# Virtuális környezet létrehozása
python -m venv venv
source venv/bin/activate  # Linux/Mac
# vagy
venv\Scripts\activate  # Windows

# Függőségek telepítése
pip install -r requirements.txt

# Alkalmazás indítása
python chat.py
```

## Használat

Az alkalmazás elindítása után egy interaktív chat konzol jelenik meg:

```
===========================================
   AI Chat Console - OpenAI GPT-4
===========================================

Parancsok:
  - Írj be bármilyen kérdést
  - 'exit' vagy 'quit' - Kilépés
  - 'clear' - Beszélgetés törlése
  - 'history' - Korábbi üzenetek megjelenítése

-------------------------------------------

You: Mi az AI?
Assistant: Az AI (Artificial Intelligence) vagy mesterséges intelligencia...

You: exit
Viszlát!
```

## Funkciók

- ✅ OpenAI GPT-4 integráció
- ✅ Chat history (beszélgetési előzmények)
- ✅ Interaktív konzol interfész
- ✅ Környezeti változók kezelése
- ✅ Docker támogatás
- ✅ Színes konzol kimenet
- ✅ Hibakezelés és retry logic

## Konfiguráció

Az alkalmazás a `.env` fájlban konfigurálható:

```env
# OpenAI beállítások
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4o-mini  # Elérhető: gpt-4o-mini, gpt-3.5-turbo, gpt-4
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=1000
```

**Elérhető modellek:**
- `gpt-4o-mini` - Legújabb, gyors, ingyenes/olcsó (alapértelmezett)
- `gpt-3.5-turbo` - Gyors, olcsó
- `gpt-4` - Legerősebb, de fizetős (külön előfizetés kell)

## Projekt Struktúra

```
istvan.hadhazi/
├── chat.py              # Fő alkalmazás
├── requirements.txt     # Python függőségek
├── Dockerfile          # Docker konfiguráció
├── docker-compose.yml  # Docker Compose setup
├── .env.example        # Környezeti változók sablon
├── .gitignore          # Git ignore fájl
└── README.md           # Ez a fájl
```

## Fejlesztési Terv

Ez az egyszerű implementáció az alapot képezi a következő funkciókhoz:

- [ ] LangChain integráció
- [ ] LangGraph workflow
- [ ] Vector adatbázis (Qdrant/Pinecone)
- [ ] Multi-domain routing (HR, IT, Finance, Legal, Marketing)
- [ ] Workflow automation
- [ ] RAG (Retrieval-Augmented Generation)

## Licenc

MIT License

