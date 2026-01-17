# Vector Embeddings Demo

A minimal but clean demonstration of embeddings + vector database + nearest-neighbor retrieval, designed to teach core concepts while following SOLID principles.

## Features

- 🔑 **OpenAI Embeddings**: Generate vector embeddings for text using OpenAI's API
- 🗄️ **Vector Database**: Store and retrieve embeddings using ChromaDB
- 🔍 **Similarity Search**: Find nearest neighbors to any query
- 🐳 **Dockerized**: Fully containerized for easy deployment
- 🎯 **SOLID Design**: Clean architecture with clear abstractions

## Architecture

This project demonstrates SOLID principles in a practical Python application:

### Single Responsibility Principle
Each module has one clear purpose:
- `config.py` - Configuration loading and validation
- `embeddings.py` - Embedding generation
- `vector_store.py` - Vector database operations
- `application.py` - Business logic orchestration
- `cli.py` - User interface and interaction

### Open/Closed Principle
The application is open for extension via interfaces:
- Swap embedding providers (OpenAI → Cohere, Hugging Face, etc.)
- Swap vector stores (ChromaDB → Pinecone, Weaviate, etc.)

### Liskov Substitution Principle
Concrete implementations can be substituted without breaking contracts:
- `OpenAIEmbeddingService` implements `EmbeddingService`
- `ChromaVectorStore` implements `VectorStore`

### Interface Segregation Principle
Small, focused interfaces:
- `EmbeddingService` - Only `get_embedding()`
- `VectorStore` - Only `add()` and `similarity_search()`

### Dependency Inversion Principle
High-level logic depends on abstractions:
- `EmbeddingApp` depends on interfaces, not concrete classes
- Dependencies injected via constructors

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py           # Entry point with usage instructions
│   ├── config.py         # Configuration management
│   ├── interfaces.py     # Abstract base classes
│   ├── embeddings.py     # OpenAI embedding service
│   ├── vector_store.py   # ChromaDB vector store
│   ├── application.py    # Business logic orchestrator
│   └── cli.py            # Command-line interface
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Quick Start

### 1. Prerequisites

- Docker installed on your system
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### 2. Configuration

Copy the environment template and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and replace `your_openai_api_key_here` with your actual OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-api-key
```

### 3. Build the Docker Image

```bash
docker build -t embedding-demo .
```

### 4. Run the Application

```bash
docker run -it --env-file .env embedding-demo
```

## Usage

Once the application starts, you'll see a welcome message. Simply type prompts and press Enter:

```
Enter a prompt (or 'exit' to quit): I love learning about artificial intelligence

Processing...

✓ Stored with ID: 123e4567-e89b-12d3-a456-426614174000

Nearest neighbors:
  1. (distance=0.0000) "I love learning about artificial intelligence"
```

As you add more prompts, the similarity search will find related entries:

```
Enter a prompt (or 'exit' to quit): Machine learning is fascinating

Processing...

✓ Stored with ID: 987fcdeb-51a2-43f1-9c7d-8a1b2c3d4e5f

Nearest neighbors:
  1. (distance=0.0000) "Machine learning is fascinating"
  2. (distance=0.1234) "I love learning about artificial intelligence"
```

Type `exit` to quit the application.

## How It Works

1. **User Input**: You type a text prompt
2. **Embedding Generation**: The text is sent to OpenAI's API to generate a vector embedding
3. **Storage**: The text and embedding are stored in ChromaDB (persisted to disk)
4. **Similarity Search**: ChromaDB finds the k-nearest neighbors using cosine similarity
5. **Display**: Results are shown with similarity scores

## Development

### Running Without Docker

If you prefer to run locally without Docker:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m app.main
```

### Extending the Application

Thanks to SOLID design, you can easily extend this application:

**Add a new embedding provider:**
1. Create a class implementing `EmbeddingService`
2. Inject it in `main.py` instead of `OpenAIEmbeddingService`

**Add a new vector store:**
1. Create a class implementing `VectorStore`
2. Inject it in `main.py` instead of `ChromaVectorStore`

**Change the embedding model:**
Set `EMBEDDING_MODEL` in `.env`:
```
EMBEDDING_MODEL=text-embedding-3-large
```

## Technologies Used

- **Python 3.11** - Modern Python runtime
- **OpenAI API** - Text embedding generation
- **ChromaDB** - Vector database for similarity search
- **Docker** - Containerization
- **python-dotenv** - Environment variable management

## License

This is a demo project for educational purposes.

## Learn More

- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
