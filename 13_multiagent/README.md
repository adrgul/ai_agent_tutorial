# AI Customer Support Agent - Multi-Agent Patterns Demo

A production-style, full-stack demo application showcasing **5 multi-agent design patterns** built with **LangGraph**, demonstrating agentic RAG, ticket triage, agent-assist, and human handoff capabilities.

## 🎯 Overview

This application demonstrates enterprise-grade customer support automation using advanced multi-agent architectures. It showcases how different LangGraph patterns can be applied to solve real-world support scenarios.

### Key Features

- **Agentic RAG**: Knowledge-grounded answers with citations from a mock knowledge base
- **Ticket Triage**: Automatic classification, priority assignment, and routing
- **Agent Assist**: Draft replies, case summaries, and next-best-actions for human agents
- **Human Handoff**: Policy-based escalation with guardrails
- **Real-time Streaming**: Word-by-word response streaming via WebSocket
- **Demo-Friendly UI**: Visual trace panel showing node execution, tool calls, and state changes

## 🏗️ Architecture

### Multi-Agent Patterns (5 Implementations)

#### 1. **Router Pattern**
Conditional routing to specialist agents with fan-out capability for mixed intents.

**LangGraph Concepts:**
- Conditional edges for routing decisions
- `Send` for parallel execution (fan-out)
- Multiple specialist nodes (billing, technical, account)
- Result synthesis from parallel outputs

**Use Case:** Customer asks about both billing and technical issues → routes to both specialists in parallel

#### 2. **Subagents Pattern**
Orchestrator calls specialized subagents as tools based on LLM decision.

**LangGraph Concepts:**
- Single orchestrator node
- Subagents invoked as functions/tools
- LLM decides which subagents to call
- Tool call/result events in trace

**Use Case:** LLM analyzes request and calls Triage, Knowledge, and AgentAssist subagents as needed

#### 3. **Handoffs Pattern**
State-driven agent switching with policy-based escalation.

**LangGraph Concepts:**
- `active_agent` field in shared state
- Conditional routing based on state
- Handoff events with reason tracking
- Case brief generation for human agents

**Use Case:** Self-service agent handles simple queries; escalates to human for refund disputes or legal threats

#### 4. **Skills Pattern**
On-demand context loading - skills activated only when needed.

**LangGraph Concepts:**
- Assessment node determines required skills
- Skills = on-demand context fetchers (KB, customer data, ticketing)
- Tool calls only when necessary
- Efficient resource usage

**Use Case:** Only fetches customer data and KB articles when actually needed for the query

#### 5. **Custom Workflow Pattern**
Deterministic pipeline with agentic nodes and recursion control.

**LangGraph Concepts:**
- Fixed pipeline: sanitize → extract → triage → retrieve → draft → policy → finalize
- **Recursion with limit** (draft → policy → revise → policy, max 3 iterations)
- `recursion_depth` tracking in state
- Revise loop demonstrates controlled iteration

**Use Case:** Structured pipeline that drafts replies, checks policies, and revises until compliant or recursion limit reached

### LangGraph Concepts Demonstrated

| Concept | Where to See It | Pattern(s) |
|---------|----------------|------------|
| **Shared State** | `SupportState` in `domain/state.py` | All patterns |
| **Reducers** | `merge_sources` (unique merge), `add` (append) | All patterns |
| **Send (fan-out)** | `fanout_specialists()` in router | Router |
| **Conditional Edges** | `route_to_specialist()`, `route_by_agent()` | Router, Handoffs, Custom |
| **Recursion Limit** | `route_after_policy()` with depth check | Custom Workflow |
| **Handoff Events** | `TraceEvent.handoff()` | Handoffs |
| **Tool Calls** | KB/Customer/Ticketing tools | All patterns |

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- (Optional) OpenAI API key for real LLM responses

### Setup

1. **Clone and navigate:**
   ```bash
   cd /Users/adriangulyas/Development/robotdreams/14_multiagent
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY (or leave empty for mock mode)
   ```

3. **Start the application:**
   ```bash
   docker compose up --build
   ```

4. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Mock Mode (No API Key Required)

The application works without an OpenAI API key! It uses deterministic mock responses for demo purposes. Just leave `OPENAI_API_KEY` empty in `.env`.

## 📱 User Interface

The UI is divided into two main sections:

### Left Panel: Chat
- **Input Box**: Type customer support queries
- **Message Stream**: Real-time word-by-word streaming responses
- **Connection Status**: WebSocket connection indicator

### Right Panels:

#### 1. **Pattern Selector**
Choose which multi-agent pattern to execute:
- Router
- Subagents
- Handoffs
- Skills
- Custom Workflow

Each pattern shows its key concepts as badges.

#### 2. **Trace / Events Panel**
Chronological execution trace showing:
- 🔹 **Node Start/End**: Which graph nodes executed
- 🔧 **Tool Calls**: KB retrieval, customer lookup, ticketing operations
- ⚡ **Fan-out**: When parallel execution occurs (Send)
- 🔄 **Handoffs**: Agent switching with reasons
- 💾 **Cache Hits/Misses**: Caching efficiency

#### 3. **State Snapshot Panel**
Real-time shared state view:
- Selected pattern
- Active agent (for handoffs)
- Recursion depth (for custom workflow)
- Sources count
- Messages count

#### 4. **Ticket Triage Panel**
Automatic classification results:
- **Category**: Billing, Technical, Account, Shipping, Refund, Other
- **Priority**: P0 (critical) → P3 (low)
- **Sentiment**: Positive, Neutral, Negative
- **Routing Team**: Assigned team
- **Tags**: Auto-generated labels
- **Confidence**: Classification confidence score

#### 5. **Agent Assist Panel**
AI-generated assistance for human agents:
- **Suggested Reply Draft**: Pre-written response for review
- **Case Summary**: 2-3 bullet point summary
- **Next Best Actions**: Checklist of recommended steps

## 🧪 Try These Examples

### Example 1: Router Pattern (Fan-out)
**Query:** "I have a billing issue and a technical error"

**Watch for:**
- Classification detects mixed intent
- `send_fanout` event
- Parallel execution of billing + technical specialists
- Synthesis of both responses

### Example 2: Handoffs Pattern (Escalation)
**Query:** "I want to sue you for this fraudulent charge"

**Watch for:**
- Policy trigger detection
- `handoff` event from self_service → human
- Case brief generation
- Priority set to P0

### Example 3: Custom Workflow (Recursion)
**Query:** "I need a refund for my order immediately"

**Watch for:**
- Entity extraction (order ID if provided)
- Draft generation
- Policy check
- Revise loop (if policy violations)
- Recursion depth incrementing

### Example 4: Skills Pattern (Lazy Loading)
**Query:** "What is your shipping policy?"

**Watch for:**
- Assessment determines only KB skill needed
- Customer skill skipped (not needed)
- Tool calls only for necessary skills

## 🏛️ Architecture & Code Structure

### Backend (`backend/`)

```
backend/
├── app/
│   ├── core/                    # Configuration & logging
│   │   ├── config.py           # Environment config
│   │   └── logging.py          # Logging setup
│   ├── domain/                  # Core domain models
│   │   ├── state.py            # Shared state + reducers ⭐
│   │   ├── events.py           # Trace events
│   │   ├── ticket.py           # Triage models
│   │   └── policies.py         # Handoff policies
│   ├── infrastructure/          # External integrations
│   │   ├── llm/
│   │   │   ├── base.py         # LLM interface
│   │   │   └── openai_provider.py  # OpenAI + mock
│   │   ├── tools/
│   │   │   ├── kb_tool.py      # RAG retrieval
│   │   │   ├── customer_tool.py # Customer context
│   │   │   └── ticketing_tool.py # Ticket management
│   │   └── cache/
│   │       └── memory_cache.py  # Simple TTL cache
│   ├── application/             # Use cases & orchestration
│   │   ├── orchestration/
│   │   │   ├── graph_factory.py     # Pattern builder ⭐
│   │   │   └── patterns/
│   │   │       ├── router.py        # Router pattern ⭐
│   │   │       ├── subagents.py     # Subagents pattern ⭐
│   │   │       ├── handoffs.py      # Handoffs pattern ⭐
│   │   │       ├── skills.py        # Skills pattern ⭐
│   │   │       └── custom_workflow.py # Custom workflow ⭐
│   │   └── usecases/
│   │       └── chat_stream.py   # Streaming orchestration
│   ├── presentation/            # API layer
│   │   └── api/
│   │       ├── ws_chat.py       # WebSocket endpoint
│   │       └── http_routes.py   # REST endpoints
│   └── main.py                  # FastAPI app
├── Dockerfile
└── pyproject.toml
```

**⭐ = Key files for understanding LangGraph patterns**

### Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── app/
│   │   └── App.tsx              # Main app component
│   ├── components/
│   │   ├── Chat.tsx             # Chat interface
│   │   ├── PatternSelector.tsx  # Pattern selection
│   │   ├── TracePanel.tsx       # Execution trace
│   │   ├── StatePanel.tsx       # State snapshot
│   │   ├── TicketPanel.tsx      # Triage results
│   │   └── AgentAssistPanel.tsx # Agent assist
│   ├── lib/
│   │   ├── types.ts             # TypeScript types
│   │   └── ws.ts                # WebSocket client
│   ├── main.tsx
│   └── index.css
├── Dockerfile
├── package.json
└── vite.config.ts
```

## 🔬 Technical Details

### Shared State & Reducers

The `SupportState` in `backend/app/domain/state.py` demonstrates LangGraph's state management:

```python
class SupportState(TypedDict):
    messages: Annotated[List[dict], add]              # Append reducer
    sources: Annotated[List[str], merge_sources]      # Custom unique merge
    trace: Annotated[List[TraceEvent], add]           # Append reducer
    # ... other fields
```

**Reducers:**
- `add`: Appends new items to list
- `merge_sources`: Custom reducer that deduplicates sources

### Caching Strategy

Three cache instances with different purposes:
- **Routing Cache**: Caches classification decisions (message → route)
- **KB Cache**: Caches knowledge base retrieval (query → articles)
- **Synthesis Cache**: Caches final answers for idempotent queries

All caches use TTL (default 300s) and track hit/miss statistics.

### Streaming Protocol

WebSocket messages follow this protocol:

**Client → Server:**
```json
{
  "pattern": "router|subagents|handoffs|skills|custom_workflow",
  "message": "user question",
  "customer_id": "CUST-001",
  "channel": "chat"
}
```

**Server → Client:**
```json
// Trace events
{"type": "trace", "event": {...}}

// Word-by-word streaming
{"type": "word", "content": "Hello"}
{"type": "word", "content": " "}
{"type": "word", "content": "there"}

// Final result
{
  "type": "done",
  "final": {
    "text": "...",
    "ticket": {...},
    "agent_assist": {...},
    "stats": {...}
  }
}
```

## 🧩 Adding New Patterns

To add a new multi-agent pattern:

1. Create `backend/app/application/orchestration/patterns/your_pattern.py`
2. Implement nodes and create graph using `StateGraph`
3. Add factory method in `graph_factory.py`
4. Update pattern list in `get_available_patterns()`

## 🐛 Troubleshooting

### Container Issues
```bash
# Rebuild containers
docker compose down
docker compose up --build

# View logs
docker compose logs -f backend
docker compose logs -f frontend
```

### WebSocket Connection Issues
- Check that backend is running on port 8000
- Verify CORS settings in `backend/app/main.py`
- Check browser console for connection errors

### Mock LLM Not Working
- Verify no `OPENAI_API_KEY` is set in `.env`
- Check logs: "Using mock LLM for demo" should appear
- Mock responses are deterministic and keyword-based

## 📚 Learning Resources

This codebase is designed to be **teachable**. Key learning points:

1. **Shared State**: See `backend/app/domain/state.py`
2. **Reducers**: `merge_sources` custom reducer
3. **Conditional Edges**: `route_to_specialist()` in router pattern
4. **Send (Fan-out)**: `fanout_specialists()` in router pattern
5. **Recursion Control**: `route_after_policy()` in custom workflow
6. **Handoff Events**: `check_handoff_needed()` in handoffs pattern

Each pattern file has detailed comments explaining **why** certain design decisions were made.

## 📄 License

MIT License - Feel free to use this for learning and teaching purposes.

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Multi-agent orchestration
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React](https://react.dev/) - Frontend framework
- [Tailwind CSS](https://tailwindcss.com/) - Styling

---

**Happy Learning! 🚀**

For questions or issues, please check the code comments or trace panel output.
