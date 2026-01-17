# Architecture Diagram - User Guide

## Overview

This document explains the comprehensive architecture diagram that visualizes the AI Agent Complex system with emphasis on **MCP (Model Context Protocol) integration**, **LangGraph workflows**, and **parallel execution patterns**.

**Diagram File**: [`ARCHITECTURE_DIAGRAM_MCP_LANGGRAPH.drawio`](./ARCHITECTURE_DIAGRAM_MCP_LANGGRAPH.drawio)

---

## How to View the Diagram

### Option 1: Draw.io Desktop App (Recommended)
1. Download [Draw.io Desktop](https://github.com/jgraph/drawio-desktop/releases)
2. Open `ARCHITECTURE_DIAGRAM_MCP_LANGGRAPH.drawio`
3. Navigate with zoom (Ctrl/Cmd + Mouse Wheel)

### Option 2: Draw.io Web App
1. Go to [https://app.diagrams.net/](https://app.diagrams.net/)
2. Click "Open Existing Diagram"
3. Select `ARCHITECTURE_DIAGRAM_MCP_LANGGRAPH.drawio`

### Option 3: VS Code Extension
1. Install the [Draw.io Integration extension](https://marketplace.visualstudio.com/items?itemName=hediet.vscode-drawio)
2. Open the `.drawio` file directly in VS Code

---

## Diagram Structure

The diagram is organized into **5 main sections**:

### 1. **Main Agent Workflow** (Left Column)
**Location**: Left side, vertical flow
**Color**: Light Blue (#CCE5FF)

**Flow**:
```
START
  ↓
RAG Pipeline (Subgraph)
  ↓
Fetch AlphaVantage Tools (🔶 MCP CALL)
  ↓
Fetch DeepWiki Tools (🔶 MCP CALL)
  ↓
Agent Decide (Diamond)
  ├→ MCP Tool Execution (🔶 MCP CALL) → Loop back
  ├→ Parallel Tool Execution (🔶 PARALLEL MCP) → Loop back
  ├→ Built-in Tools (local) → Loop back
  └→ Agent Finalize
      ↓
    END
```

**Key Features**:
- **MCP Calling Points**: Nodes with thick orange borders
- **Tool Loop**: Blue curved arrows showing multi-step reasoning
- **Conditional Routing**: Dashed arrows from Agent Decide diamond

**Each Node Includes**:
- Node name
- File path (e.g., `backend/services/agent.py`)
- Method name (e.g., `_fetch_alphavantage_tools_node()`)
- Line numbers (e.g., `[199-255]`)
- Purpose description

---

### 2. **RAG Subgraph Pipeline** (Top Right Inset)
**Location**: Top right, horizontal flow
**Color**: Light Yellow (#FFFFCC)

**Flow**:
```
query_rewrite → retrieve → context_builder → guardrail → feedback
```

**Purpose**: Document-based question answering with vector search

**Each Node Details**:
- `query_rewrite`: Optimizes query for retrieval
- `retrieve`: ChromaDB vector search (Top-K: 4, Threshold: 0.7)
- `context_builder`: Builds citations & context (Max tokens: 2000)
- `guardrail`: Validation & formatting
- `feedback`: Metrics aggregation

---

### 3. **Advanced Agent Workflow** (Center-Right Column)
**Location**: Right side, vertical flow
**Color**: Light Green (#CCFFCC)

**Flow**:
```
START
  ↓
Router (Dynamic Routing) - Diamond
  ├→ Planner → Executor (loop) → Aggregator → END
  ├→ Fan-Out → [Parallel Zone] → Fan-In → Aggregator → END
  └→ Direct Response → END
```

**Key Patterns Demonstrated**:
1. **Plan-and-Execute**:
   - Planner generates ExecutionPlan with `can_run_parallel` flags
   - Executor iterates through steps with dependency checking
   - Loop-back for multi-step plans

2. **Parallel Execution (Fan-Out/Fan-In)**:
   - Fan-Out validates task independence
   - Parallel Execution Zone shows 3 concurrent branches
   - Fan-In aggregates results using `parallel_results_reducer()`
   - **Performance**: 2-6x speedup (3 tasks @ 2s each = 2s total)

3. **Dynamic Routing**:
   - LLM-based router decides execution path
   - Returns `RoutingDecision` with confidence score
   - Routes to planner, fan-out, direct response, or end

---

### 4. **MCP Integration Details** (Bottom Inset)
**Location**: Bottom center, horizontal layout
**Color**: Light Orange (#FFF8E1)

**Three Panels**:

#### Panel 1: MCPClient Class
- **File**: `backend/infrastructure/tool_clients.py` [L272-496]
- **Methods**:
  - `connect(server_url)` [L285-373]: JSON-RPC 2.0 initialize
  - `list_tools()` [L375-437]: Fetch available tools
  - `call_tool(name, arguments)` [L439-486]: Execute tool (30s timeout)
  - `disconnect()` [L488-495]: Close connection

#### Panel 2: MCP Servers
1. **AlphaVantage MCP**
   - URL: `https://mcp.alphavantage.co/mcp?apikey=...`
   - Tools: 118 financial tools
   - Categories: Stocks, Forex, Crypto, Economic Indicators

2. **DeepWiki MCP**
   - URL: `https://mcp.deepwiki.com/mcp`
   - Tools: 3 knowledge tools (ask_question, read_wiki_structure, get_wiki_content)
   - Status: Currently returns 404

#### Panel 3: Protocol Flow
1. Initialize Connection (JSON-RPC 2.0, Protocol: 2025-03-26)
2. Send 'initialized' notification
3. List Available Tools (Header: `Mcp-Session-Id`)
4. Call Tool (30s timeout)
5. Disconnect (optional)

---

### 5. **State Management & Reducers** (Far Right Inset)
**Location**: Far right, vertical panel
**Color**: Light Blue (#E8F5FF)

**Purpose**: Explains how LangGraph handles concurrent state updates from parallel nodes

**Key State Fields with Reducers**:

1. **`parallel_results`**
   - Type: `Annotated[List[Dict], parallel_results_reducer]`
   - Reducer: [L72-99]
   - Purpose: Deduplicates by task_id
   - Why: Multiple parallel branches emit results; reducer ensures each task appears once

2. **`aggregated_data`**
   - Type: `Annotated[Dict, dict_merge_reducer]`
   - Reducer: [L53-69]
   - Purpose: Merges dicts from parallel branches
   - Why: Different tools produce different keys; reducer combines without data loss

3. **`messages`**
   - Type: `Annotated[Sequence[BaseMessage], list_reducer]`
   - Reducer: [L36-50]
   - Purpose: Appends new messages
   - Why: Conversation history from all branches

**How Reducers Work**:
```python
# When 3 parallel nodes emit updates:
Node A: parallel_results += [{task_A}]
Node B: parallel_results += [{task_B}]
Node C: parallel_results += [{task_C}]

# LangGraph calls reducer 3 times:
result = reducer([], [{task_A}])
result = reducer(result, [{task_B}])
result = reducer(result, [{task_C}])

# Final state: [{task_A}, {task_B}, {task_C}] ✅

# Without reducers: Only last update survives
# Result would be: [{task_C}] ❌
```

---

## Visual Design Guide

### Colors and Meanings

| Color | Hex Code | Meaning |
|-------|----------|---------|
| 🔵 Light Blue | #CCE5FF | Main Agent nodes |
| 🟢 Light Green | #CCFFCC | Advanced Agent nodes |
| 🟡 Light Yellow | #FFFFCC | RAG Pipeline nodes |
| 🟠 Light Orange | #FFDDAA | MCP-related nodes |
| 🟣 Light Purple | #E6CCFF | Parallel execution |
| ⬜ White/Gray | #FFFFFF/#F0F0F0 | Decision diamonds & insets |

### Border Highlights

| Border Style | Meaning |
|--------------|---------|
| 🔶 **Thick Orange** (4px) | **MCP calling point** - External MCP server communication |
| 🟣 **Thick Purple** (4px) | **Parallel execution zone** - Concurrent task execution |
| 🔷 **Thick Blue** (4px) | **Decision/routing node** - LLM-based routing |
| Regular (2px) | Standard node |

### Arrow Types

| Arrow Style | Meaning |
|-------------|---------|
| **→ Solid Arrow** | Sequential flow (guaranteed execution) |
| **⇢ Dashed Arrow** | Conditional flow (depends on decision) |
| **↻ Curved Blue Arrow** | Loop back (multi-step reasoning) |
| **⇉ Thick Purple** | Parallel spawn/merge |

---

## Key Insights from the Diagram

### 1. MCP Integration Points (🔶 Orange Highlights)

The diagram shows **4 MCP calling points**:

1. **Fetch AlphaVantage Tools** (agent.py:199-255)
   - Connects to AlphaVantage MCP server
   - Fetches 118 financial tools
   - Stores in `state["alphavantage_tools"]`

2. **Fetch DeepWiki Tools** (agent.py:257-312)
   - Connects to DeepWiki MCP server
   - Fetches 3 knowledge tools
   - Stores in `state["deepwiki_tools"]`

3. **MCP Tool Execution** (agent.py:699-756)
   - Executes single MCP tool
   - 30-second timeout
   - Returns SystemMessage with result

4. **Parallel Tool Execution** (agent.py:758-806)
   - Executes multiple MCP tools concurrently
   - Uses `asyncio.gather()` (parallel_execution.py:93)
   - 2-6x speedup

### 2. Parallel Execution Flow (🟣 Purple Highlights)

**Complete Flow**:
```
Router (LLM Decision)
  ↓
  [decides: is_parallel=true, next_nodes=[tool_A, tool_B, tool_C]]
  ↓
Fan-Out (Validate Independence)
  ↓
  [spawns 3 parallel branches]
  ↓
PARALLEL EXECUTION ZONE
  ├─ Tool Weather (Branch 1) ─┐
  ├─ Tool FX Rates (Branch 2) ─┼─ asyncio.gather()
  └─ Tool Crypto (Branch 3) ───┘
  ↓
  [LangGraph applies reducers to merge state]
  ↓
Fan-In (Aggregate Results)
  ↓
Aggregator (Synthesize Response)
```

**Key Mechanism**: `parallel_results_reducer()` ensures concurrent updates are safely merged.

### 3. Loop Mechanisms

**Two Types of Loops**:

1. **Main Agent Loop** (Blue curved arrows)
   - From tool nodes back to Agent Decide
   - Enables multi-step reasoning
   - Max iterations: 20 (tracked in `state["iteration_count"]`)

2. **Executor Loop** (Blue curved arrow)
   - From Executor back to itself
   - Iterates through plan steps
   - Continues until `plan_completed=true`

### 4. State Transformations

**Critical State Changes**:

| Node | State Transformation |
|------|---------------------|
| Fetch AlphaVantage | `state["alphavantage_tools"]` = 118 tools |
| Fetch DeepWiki | `state["deepwiki_tools"]` = 3 tools |
| Agent Decide | `state["tool_decision"]` = {action, tool_name, reasoning} |
| Parallel Execution | `state["parallel_results"]` = merged results (via reducer) |
| Fan-In | `state["aggregation_result"]` = {total, successful, failed, data} |

---

## How to Navigate the Diagram

### Finding Specific Information

1. **To understand MCP integration**:
   - Look for nodes with thick orange borders (🔶)
   - Check bottom inset "MCP Integration Details"
   - Trace arrows from "Fetch AlphaVantage/DeepWiki" nodes

2. **To understand parallel execution**:
   - Look for nodes with thick purple borders (🟣)
   - Find "PARALLEL EXECUTION ZONE" box
   - Check right inset "State Management & Reducers"
   - Trace flow: Fan-Out → Parallel Zone → Fan-In

3. **To understand LangGraph workflow**:
   - Start at START node (left or right column)
   - Follow solid arrows for sequential flow
   - Follow dashed arrows for conditional routing
   - Note loop-back arrows (blue curved)

4. **To find code implementation**:
   - Every node includes file path + method name + line numbers
   - Example: `backend/services/agent.py::_fetch_alphavantage_tools_node() [L199-255]`
   - Use your IDE's "Go to File" feature with these paths

---

## Educational Use Cases

### For Learning LangGraph:
- **State Management**: See how TypedDict with reducers handles concurrent updates
- **Conditional Edges**: Agent Decide node shows multiple routing options
- **Loops**: Tool nodes loop back for multi-step reasoning
- **Subgraphs**: RAG Pipeline as composable subgraph

### For Learning MCP:
- **Protocol Flow**: Bottom inset shows JSON-RPC 2.0 sequence
- **Client Implementation**: MCPClient methods with line numbers
- **Server Integration**: Two different MCP servers (AlphaVantage, DeepWiki)
- **Tool Discovery**: Automatic tool listing and registration

### For Learning Parallel Patterns:
- **Fan-Out/Fan-In**: Complete pattern with task independence validation
- **Reducers**: How to safely merge concurrent state updates
- **Performance**: Visual comparison of sequential vs parallel execution
- **Error Handling**: Partial failure support in Fan-In node

---

## Diagram Metadata

- **Created**: 2026-01-13
- **Tool**: Draw.io (app.diagrams.net)
- **Format**: XML (.drawio)
- **Size**: A3 Landscape (2400x2200px)
- **Nodes**: 50+ nodes with full code references
- **File Size**: ~40KB
- **Version**: 1.0

---

## Related Documentation

For deeper understanding, see:

1. **MCP Integration**:
   - [MCP_SZERVER_HASZNALAT.md](./MCP_SZERVER_HASZNALAT.md) - Complete MCP guide (1235 lines)
   - [MCP_TEST_PROMPTS.md](../MCP_TEST_PROMPTS.md) - Test queries for MCP tools

2. **Advanced Agents**:
   - [ADVANCED_AGENTS.md](./ADVANCED_AGENTS.md) - Plan-Execute, Parallel, Routing patterns
   - [PARALLEL_EXECUTION_COMPLETE.md](../PARALLEL_EXECUTION_COMPLETE.md) - Detailed parallel execution guide

3. **System Architecture**:
   - [SPECIFICATION.md](./SPECIFICATION.md) - Complete technical specification
   - [AI_AGENT_4_RETEG_ARCHITEKTURA.md](./AI_AGENT_4_RETEG_ARCHITEKTURA.md) - 4-layer architecture

4. **Code Implementation**:
   - `backend/services/agent.py` - Main agent graph
   - `backend/advanced_agents/` - Advanced patterns
   - `backend/infrastructure/tool_clients.py` - MCP client

---

## Troubleshooting

### Diagram Won't Open
- **Issue**: File format not recognized
- **Solution**: Ensure you're using Draw.io Desktop, Web, or VS Code extension (not a text editor)

### Text is Too Small
- **Issue**: Diagram is large, text appears tiny
- **Solution**: Use zoom controls (Ctrl/Cmd + Mouse Wheel) or View → Zoom In

### Can't Find Specific Node
- **Issue**: Diagram is complex with many nodes
- **Solution**: Use Find feature (Ctrl/Cmd + F) to search for node names or file paths

### Want to Edit Diagram
- **Issue**: Need to add custom notes or modifications
- **Solution**:
  1. Make a copy of the diagram file
  2. Open in Draw.io
  3. Edit freely (nodes are unlocked)
  4. Save with a new name

---

## Feedback and Contributions

If you find errors or want to suggest improvements:

1. **Code Issues**: Check if code references (file paths, line numbers) are still accurate
2. **Visual Clarity**: Suggest better color schemes or layouts
3. **Missing Information**: Identify important flows or patterns not covered

This diagram is a living document that evolves with the codebase.

---

## License

This diagram is part of the AI Agent Complex project. See the main project LICENSE file for details.
