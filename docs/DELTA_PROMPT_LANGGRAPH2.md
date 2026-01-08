## ➕ Parallel Nodes & Reducer Demonstration (LangGraph Extension)

Extend the **Teaching Memory Lab** to explicitly demonstrate **parallel node execution in LangGraph** and how **reducers reconcile parallel outputs** into a deterministic state.

---

### 🎯 Educational Objective

Students must be able to clearly see:

- That **multiple nodes can run in parallel**
- That **parallel execution does NOT mean shared mutable state**
- That **reducers are the only legal place where parallel results are merged**
- How **deterministic reducers prevent race conditions**

This section is **mandatory** for the teaching lab.

---

## 🧵 Parallel Node Design

Introduce a **parallel execution stage** in the LangGraph workflow:

crmsh
Copy code
      ┌──────────────┐
      │  Router Node │
      └──────┬───────┘
             │
  ┌──────────┼──────────┐
  ▼          ▼          ▼
Summarizer FactsExtractor MetricsCollector
Node Node Node
└──────────┼──────────┘
▼
Reducer Merge
▼
Answer Node

yaml
Copy code

---

## ⚙ Parallel Nodes to Implement

Create the following nodes under:

backend/teaching_memory_lab/nodes/

yaml
Copy code

### 1️⃣ `summarizer_node`
- Produces:
  - `summary_update`
- Does NOT mutate shared state
- Returns partial state only

---

### 2️⃣ `facts_extractor_node`
- Produces:
  - `facts_delta[]`
- Extracts structured facts
- Must be idempotent

---

### 3️⃣ `metrics_collector_node`
- Produces:
  - `trace_event`
- Collects latency, token usage, and flags
- Teaching focus: *side-effect-free observability*

---

All three nodes must:

- Run **in parallel**
- Return **partial state updates**
- Never modify global state directly

---

## 🔀 Reducer Demonstration (Critical)

Create reducers in:

backend/teaching_memory_lab/reducers.py

yaml
Copy code

### Required Reducers

#### `merge_summaries(old, new)`
- Replace strategy
- Version-aware
- Deterministic

#### `merge_facts(existing, incoming)`
- Merge by `key`
- Newer timestamp wins
- No duplicates

#### `merge_trace(existing, incoming)`
- Append
- Enforce max length (sliding window)

---

### Teaching Notes (Code Comments Must Explain)

- Why reducers are required in parallel graphs
- Why merge order must not matter
- Why reducers must be **pure functions**
- Why side effects inside nodes are forbidden

---

## 🧪 Mandatory Reducer Tests

Add tests proving:

- Parallel outputs merged in different orders produce identical state
- Duplicate facts are not re-inserted
- Summary replacement is deterministic
- Trace window is bounded

---

## 🧠 LangGraph Graph Definition

In `graph.py`:

- Use LangGraph’s **parallel edge syntax**
- Explicitly document:
  - fan-out
  - fan-in
  - merge point

Example (illustrative):

```python
graph.add_edge("router", ["summarizer", "facts", "metrics"])
graph.add_edge(["summarizer", "facts", "metrics"], "answer")
Explain in comments:

How LangGraph schedules parallel nodes

When reducers are applied

How state consistency is preserved

📦 API Response Extension
Extend memory_snapshot with:

json
Copy code
{
  "parallel_nodes_executed": [
    "summarizer",
    "facts_extractor",
    "metrics_collector"
  ],
  "reducers_applied": [
    "merge_summaries",
    "merge_facts",
    "merge_trace"
  ]
}
This must be visible when debug=true.

✅ Acceptance Criteria (Parallelism)
Parallel nodes are clearly visible in code

Reducers are the only merge mechanism

Reducers are deterministic and tested

Students can reason about:

race conditions

merge safety

state isolation

🧠 Teaching Principle to Emphasize
Parallel execution increases throughput,
reducers preserve correctness.

Implement this extension fully and document it clearly.