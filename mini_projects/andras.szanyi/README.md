# Python AI Agent System

A production-grade Python project that uses **LangGraph** for agent orchestration and **Groq** for LLM inference. The project follows **Clean Architecture** principles to separate probabilistic AI logic from deterministic business logic.

## Architectural Guidelines (Clean Architecture)

The application enforces separation of concerns and is divided into four distinct layers with strict dependency rules:

### A. Domain Layer (`src/domain`)

- **Role:** Definitions of Data, State, and Interfaces. **No external dependencies.**
- **Content:** `state.py` (AgentState definition), `interfaces.py` (abstract protocols), `entities.py` (pure data models).

### B. Application Layer (`src/application`)

- **Role:** AI Orchestration & Agent Workflow (Probabilistic).
- **Content:** `graph.py` (LangGraph builder), `nodes.py` (Node logic).
- **Rule:** This layer imports `Domain` and `Services`. It does _not_ contain raw business logic.

### C. Services Layer (`src/services`)

- **Role:** Deterministic Business Logic (The "Tools").
- **Content:** Classes (e.g., `WeatherForecaster`) that implement specific capabilities.
- **Rule:** Code here must be **deterministic**. It performs calculations or aggregates API calls. It generally implements interfaces defined in `Domain`. NO LLM calls allowed.

### D. Infrastructure Layer (`src/infrastructure`)

- **Role:** Low-level I/O & Concrete Implementations.
- **Content:** `config.py` (Pydantic settings), `llm.py` (ChatGroq client), `external.py` (Concrete API clients).

### Dependency Injection Strategy

- **Pattern:** Manual Constructor Injection via a Composition Root.
- **Constraint:** No class in `application` or `services` may instantiate a concrete class from `infrastructure` directly.
- **Wiring:** All components must be initialized and wired together in `src/container.py` (The Composition Root).

## Desired Folder Structure

```text
.
├── .env.example
├── pyproject.toml
├── README.md
├── main.py
└── src
    ├── __init__.py
    ├── container.py
    ├── domain
    │   ├── __init__.py
    │   ├── state.py
    │   ├── entities.py
    │   └── interfaces.py
    ├── application
    │   ├── __init__.py
    │   ├── graph.py
    │   └── nodes.py
    ├── services
    │   ├── __init__.py
    │   └── weather.py
    └── infrastructure
        ├── __init__.py
        ├── config.py
        ├── llm.py
        └── external.py
```

## Setup & Usage

### Prerequisites

- **uv**: This project uses `uv` for dependency management. You must have it installed on your system.
  [Installation Guide](https://github.com/astral-sh/uv)

The project includes a `Makefile` to simplify common tasks.

### 1. Configuration

Create a `.env` file in the root directory based on `.env.example`:

```bash
cp .env.example .env
```

Edit the `.env` file and add your API keys:

- `GROQ_API_KEY`: Your Groq API key.
- `OPENWEATHER_API_KEY`: Your OpenWeatherMap API key (used for Geolocation).

### 2. Installation

Install project dependencies using `uv`:

```bash
make install
```

(This executes `uv sync`)

### 3. Running the Agent

To run the main application:

```bash
make run
```

(This executes `uv run src/main.py`)

### 4. Testing

To run the test suite:

```bash
make test
```

(This executes `uv run pytest`)

### 5. Building

To build the project:

```bash
make build
```

(This executes `uv build`)

# TODOs

- linting/formatting is not checked yet.
- incomplete graph, it does not have a last state which summarize the result of the tool call.
- dockerization
- logging
- http

