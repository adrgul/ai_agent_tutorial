You are an expert Python backend engineer and software architect.
Generate a minimal but clean example project that demonstrates embeddings + vector database + nearest-neighbor retrieval, running in Docker and used from the terminal.

The code MUST follow SOLID principles (Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion) in a pragmatic, lightweight way. Use small, focused classes and clear abstractions.

Goal
-----
Create a small Python CLI app that:
1. Reads an OpenAI API key from a `.env` file.
2. Lets the user type free-text prompts in a terminal loop.
3. For each prompt:
   - Creates an embedding using the OpenAI Embeddings API.
   - Stores the text + embedding in a local vector database.
   - Immediately queries the same vector DB for the k nearest neighbors to the current embedding.
   - Prints the nearest stored texts and their similarity scores back to the terminal.

Project structure
------------------
Create the following files:

- `Dockerfile`
- `requirements.txt`
- `app/main.py`
- `app/config.py`
- `app/embeddings.py`
- `app/vector_store.py`
- `app/cli.py`
- `.env.example`  (template for the real `.env`)

SOLID & architecture guidelines
-------------------------------
Design the code according to SOLID principles:

1. Single Responsibility Principle
   - Each class/module should have one clear responsibility:
     - `Config` for configuration loading.
     - `OpenAIEmbeddingService` for embedding generation.
     - `ChromaVectorStore` for vector DB operations.
     - `EmbeddingApp` (or similar) to orchestrate the workflow.
     - `CLI` layer for user interaction.

2. Open/Closed Principle
   - Define small interfaces / abstract base classes where it makes sense:
     - e.g. an `EmbeddingService` interface / ABC.
     - a `VectorStore` interface / ABC.
   - The core app (`EmbeddingApp`) should depend on these abstractions, so we can swap implementations (e.g., different embedding provider or vector DB) without changing the app logic.

3. Liskov Substitution Principle
   - Concrete implementations (e.g. `OpenAIEmbeddingService`) must be drop-in replacements for the corresponding interface / ABC without breaking behavior.

4. Interface Segregation Principle
   - Keep interfaces small and focused:
     - `EmbeddingService` should expose only what is needed (e.g. `get_embedding(text: str) -> List[float]`).
     - `VectorStore` should expose only what is needed (e.g. `add`, `similarity_search`).

5. Dependency Inversion Principle
   - High-level logic (the application / CLI) should depend on abstractions, not concrete classes:
     - Pass `EmbeddingService` and `VectorStore` instances into `EmbeddingApp` via constructor injection.
   - Configuration (e.g. choosing OpenAI model, DB path) should be outside the core logic, in `config.py` or `main.py`.

Python & dependencies
----------------------
- Use Python 3.11 (or 3.10+) in the Docker image (official slim image is fine).
- Use `openai` for calling the Embeddings API.
- Use a simple local vector database library, e.g. `chromadb`, and persist data on disk in a `./chroma_db` folder inside the container.
- Use `python-dotenv` to load environment variables from `.env`.

`requirements.txt` should include at least:
- `openai`
- `chromadb`
- `python-dotenv`

Environment variables
----------------------
- The real API key must NOT be hard-coded.
- In `config.py`, load variables from `.env` using `python-dotenv`.
- Expect `OPENAI_API_KEY` in the `.env`.
- `.env.example` should contain:
    OPENAI_API_KEY=your_openai_api_key_here

Embeddings logic
-----------------
- Use one of the current OpenAI embedding models, for example `text-embedding-3-small`.
- Implement an `EmbeddingService` abstraction (e.g. via an abstract base class or protocol) with:
    - `get_embedding(text: str) -> List[float]`
- Implement `OpenAIEmbeddingService(EmbeddingService)` that:
    - uses the OpenAI Embeddings API,
    - returns the embedding vector,
    - handles basic errors (print/log an error and continue if the API fails).

Vector DB logic
----------------
- Implement a `VectorStore` abstraction with methods like:
    - `add(id: str, text: str, embedding: List[float]) -> None`
    - `similarity_search(embedding: List[float], k: int) -> List[Tuple[str, float, str]]`
      (id, score, text or similar)
- Implement `ChromaVectorStore(VectorStore)` using ChromaDB:
    - On startup, create or load a persistent collection, e.g.:
        - path: `./chroma_db`
        - collection name: `prompts`
    - For each user prompt:
        - generate an ID (e.g. UUID string),
        - add the text + embedding to the collection.
    - After inserting, run a similarity search on the same collection to find the k nearest neighbors (e.g. k=3) to the current embedding.
    - Return the matched texts and similarity scores/distances.

CLI behavior and application orchestration
-------------------------------------------
- Implement a high-level `EmbeddingApp` class that:
    - Receives an `EmbeddingService` and `VectorStore` via constructor injection.
    - Has a method like `process_query(text: str, k: int = 3)` that:
        1) gets the embedding of the input text,
        2) stores it in the vector DB,
        3) performs a similarity search,
        4) returns the results in a structured form.

- Implement `CLI` logic in `app/cli.py` or within `main.py` using the `EmbeddingApp`:
    - When the app starts, print a short intro explaining what it does.
    - Enter an infinite loop:
        - Prompt the user: `Enter a prompt (or 'exit' to quit): `
        - If the user types `exit`, gracefully terminate.
        - Otherwise:
            - Call `EmbeddingApp.process_query(...)`.
            - Print a nicely formatted result, for example:

              ```
              Stored prompt and retrieved nearest neighbors:
              1. (distance=0.000) "the current text itself..."
              2. (distance=0.123) "previous similar text..."
              3. (distance=0.456) "another somewhat related text..."
              ```

Dockerfile
-----------
- Based on an official Python image (e.g. `python:3.11-slim`).
- Copy the project files into the container.
- Install dependencies from `requirements.txt`.
- Use a working directory like `/app`.
- Ensure the `./chroma_db` directory is created and writable.
- Set `ENTRYPOINT` or `CMD` so that running the container starts the CLI, e.g.:
    `CMD ["python", "-m", "app.main"]`

Developer instructions
-----------------------
Add short usage instructions as comments (or docstring) in `app/main.py`:

- How to copy `.env.example` to `.env` and fill in `OPENAI_API_KEY`.
- How to build the Docker image, e.g.:
    - `docker build -t embedding-demo .`
- How to run the container with the env file:
    - `docker run -it --env-file .env embedding-demo`

Code style
-----------
- Use clear function boundaries and small classes that follow SOLID.
- Add type hints and minimal docstrings for public methods.
- Keep the code as simple and educational as possible: this is for teaching embeddings + vector DB basics and SOLID design in a Python/Docker setting.

Now generate all the mentioned files with full, working code.
