# Project Specification: Python AI Agent System

**Role:** You are a Senior Python Backend Engineer and AI Solutions Architect.
**Current Project Status:** The project is already scaffolded and running.
**Architecture Reference:** This file defines the strict architectural standards (Clean Architecture, DI, TypedDict State) that must be followed for all new code.

## 1. Technology Stack

- **Language:** Python 3.11+
- **LLM Provider:** Groq (via `langchain-groq`)
- **Orchestration:** LangGraph (StateGraph, Nodes, Edges)
- **Configuration:** `python-dotenv` and `pydantic-settings`
- **Dependency Management:** use `uv`
- **Typing:** Strict type hinting with `mypy` standards.

## 2. Architectural Guidelines (Clean Architecture)

You must enforce separation of concerns. The application is divided into four distinct layers with strict dependency rules.

### A. Domain Layer (`src/domain`)

- **Role:** Definitions of Data, State, and Interfaces. **No external dependencies.**
- **`state.py`:** Define the `AgentState` (TypedDict or Pydantic) here. This is the data contract for the graph.
- **`interfaces.py`:** Define abstract protocols for Services and Infrastructure (e.g., `WeatherProviderProtocol`).
- **`entities.py`:** Define pure data models used by the business logic.

### B. Application Layer (`src/application`)

- **Role:** AI Orchestration & Agent Workflow (Probabilistic).
- **`graph.py`:** Defines the LangGraph `StateGraph`, nodes, and compilation logic.
- **`nodes.py`:** The functions called by the graph. These nodes interact with the LLM and the Services.
- **Rule:** This layer imports `Domain` and `Services`. It does _not_ contain raw business logic.

### C. Services Layer (`src/services`)

- **Role:** Deterministic Business Logic (The "Tools").
- **Content:** Classes (e.g., `WeatherForecaster`) that implement specific capabilities.
- **Rule:** Code here must be **deterministic**. It performs calculations or aggregates API calls. It generally implements interfaces defined in `Domain`.
- **Rule:** NO LLM calls allowed in this layer.

### D. Infrastructure Layer (`src/infrastructure`)

- **Role:** Low-level I/O & Concrete Implementations.
- **Content:** The raw `ChatGroq` client setup, database connectors, and concrete API clients (e.g., `OpenWeatherMapClient`).
- **Config:** Loads environment variables via `config.py`.

## 3. Dependency Injection Strategy

- **Pattern:** Manual Constructor Injection via a Composition Root.
- **Constraint:** No class in `application` or `services` may instantiate a concrete class from `infrastructure` directly.
- **Wiring:** All components must be initialized and wired together in `src/container.py` (The Composition Root).

## 4. Desired Folder Structure

Generate the files based on this tree:

```text
.
├── .env.example
├── pyproject.toml       # Must include [tool.ruff] and [tool.mypy] sections
├── README.md
├── main.py              # Entry point (calls container.py)
└── src
    ├── __init__.py
    ├── container.py     # Composition Root (DI wiring)
    ├── domain
    │   ├── __init__.py
    │   ├── state.py     # AgentState definition
    │   ├── entities.py  # Data models
    │   └── interfaces.py# Protocols
    ├── application
    │   ├── __init__.py
    │   ├── graph.py     # LangGraph builder
    │   └── nodes.py     # Node logic
    ├── services
    │   ├── __init__.py
    │   └── weather.py   # Example business logic service
    └── infrastructure
        ├── __init__.py
        ├── config.py    # Pydantic settings (Single file)
        ├── llm.py       # ChatGroq factory
        └── external.py  # Concrete API clients
```

## 5. Coding Standards & Implementation Details

- **Config**: Create src/infrastructure/config.py using pydantic-settings to validate GROQ_API_KEY exists on startup.

- **Service-to-Tool:** In src/application, create a wrapper or use @tool decorators to expose methods from the Services layer as tools usable by LangGraph/LangChain.

- **Error Handling:** Ensure the Services layer catches external API errors and returns structured error entities, so the Agent doesn't crash on HTTP 500s.

- **Typing:** Every function argument and return value must have type hints.

## 6. Quality Assurance & Formatting

Configure `pyproject.toml` with the following requirements:

- **Linter/Formatter:** Use `ruff`.
  - ** Line length:** 88 characters.

  - ** Quote style:** Double quotes.

  - **Import sorting:** Enabled (isort compatible).

- ** Type Checking:** Use mypy.
  - `strict = true`

  - `disallow_untyped_defs = true`

- **Docstrings:** All public modules, classes, and methods must have Google-style docstrings.

## 7. Execution Instructions

When generating the code, please provide:

1. The full content for the file structure above, including the configured `pyproject.toml`.

2. A sample main.py that uses src/container.py to build the agent and run a simple query ("What is the weather in New York?").
