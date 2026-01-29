# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Setup Environment
```bash
# Copy environment template
cp .env.example .env

# (Optional) Add your OpenAI API key to .env
# If you skip this, the app will use mock responses
```

### Step 2: Start Application
```bash
# Build and start all services
docker compose up --build

# Wait for services to start...
# Backend will be on http://localhost:8000
# Frontend will be on http://localhost:5173
```

### Step 3: Test the Patterns

Open http://localhost:5173 in your browser.

#### Try Router Pattern (Fan-out)
1. Select "Router Pattern" from the dropdown
2. Enter: **"I have a billing problem and a technical error"**
3. Watch the Trace Panel for `send_fanout` event
4. See both specialists respond in parallel

#### Try Handoffs Pattern (Escalation)
1. Select "Handoffs Pattern"
2. Enter: **"I want to sue you for this fraudulent charge"**
3. Watch for `handoff` event in Trace Panel
4. See case escalated to human with P0 priority

#### Try Custom Workflow (Recursion)
1. Select "Custom Workflow Pattern"
2. Enter: **"Give me a refund immediately"**
3. Watch recursion_depth in State Panel
4. See draft → policy check → revise loop

#### Try Skills Pattern (Lazy Loading)
1. Select "Skills Pattern"
2. Enter: **"What is your shipping policy?"**
3. Watch which skills are activated
4. See only necessary context loaded

#### Try Subagents Pattern
1. Select "Subagents Pattern"
2. Enter: **"Help me track my order ORD-9871"**
3. Watch LLM decide which subagents to call
4. See tool call events in Trace Panel

## 📊 What to Watch

### Trace Panel
Real-time execution events:
- 🔹 **node_start/end**: Graph node execution
- 🔧 **tool_call/result**: KB retrieval, customer lookup
- ⚡ **send_fanout**: Parallel execution trigger
- 🔄 **handoff**: Agent switching
- 💾 **cache_hit/miss**: Caching behavior

### State Panel
- Pattern name
- Active agent (in handoffs)
- Recursion depth (in custom workflow)
- Sources collected
- Message count

### Ticket Panel
- Category classification
- Priority (P0-P3)
- Sentiment
- Routing team
- Tags

### Agent Assist Panel
- Draft reply for human agent
- Case summary bullets
- Next action checklist

## 🛠️ Troubleshooting

**WebSocket won't connect?**
```bash
# Check backend is running
curl http://localhost:8000/api/health

# Restart services
docker compose down
docker compose up
```

**Want to see real LLM responses?**
```bash
# Add to .env:
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o-mini

# Restart
docker compose restart backend
```

**Check logs:**
```bash
# Backend logs
docker compose logs -f backend

# Frontend logs
docker compose logs -f frontend
```

## 🎓 Learning Path

1. **Start simple**: Try each pattern with basic queries
2. **Read the trace**: Understand node execution order
3. **Explore the code**: 
   - Patterns: `backend/app/application/orchestration/patterns/`
   - State: `backend/app/domain/state.py`
4. **Modify patterns**: Add your own nodes or tools
5. **Create new pattern**: Follow the template in existing patterns

## 📚 Key Files to Read

- `backend/app/domain/state.py` - Shared state with reducers
- `backend/app/application/orchestration/patterns/router.py` - Router with Send
- `backend/app/application/orchestration/patterns/custom_workflow.py` - Recursion example
- `backend/app/domain/policies.py` - Handoff policy logic

## 🎯 Example Queries

**Billing:**
- "Why was I charged twice?"
- "I need a refund for order ORD-9871"

**Technical:**
- "Getting error 500 when I try to login"
- "The app keeps crashing"

**Account:**
- "Can't log in to my account"
- "How do I reset my password?"

**Mixed (triggers fan-out):**
- "I have a billing issue and the app is broken"
- "My payment failed and I'm getting an error"

**Escalation (triggers handoff):**
- "I'm going to sue you"
- "This is fraud and I want my money back now"

---

**Happy exploring! 🚀**
