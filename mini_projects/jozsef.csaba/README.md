# Customer Service Triage and Response Agent

A production-ready AI agent that automatically triages customer service tickets, retrieves relevant knowledge base articles, and generates professional response drafts with citations.

## Features

- **Intent Detection**: Automatically detects problem type (billing, technical, account, feature request) and customer sentiment
- **Smart Triage**: Classifies tickets by category, subcategory, priority (P1-P4), and assigns SLA timeframes
- **RAG Retrieval**: Uses FAISS vector search with query expansion and LLM-based re-ranking
- **Draft Generation**: Creates professional, empathetic responses with embedded KB citations
- **Policy Validation**: Checks drafts for compliance with company policies
- **RESTful API**: FastAPI-based API with automatic documentation

## Architecture

### Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **LLM**: OpenAI GPT-4 (via LangChain)
- **Vector DB**: FAISS (local)
- **Embeddings**: OpenAI text-embedding-3-large (1536 dimensions)
- **Workflow**: LangGraph for orchestration
- **Validation**: Pydantic for data modeling

### Workflow Pipeline

```
┌─────────────────┐
│  Ticket Input   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Intent Detection│  → Problem type + Sentiment
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Triage Node     │  → Priority + SLA + Team
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query Expansion │  → Generate search queries
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Vector Search   │  → Retrieve top-k KB articles
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Re-ranking    │  → LLM-based relevance scoring
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Draft Generator │  → Professional response with citations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Policy Check   │  → Compliance validation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  JSON Output    │  → Structured response
└─────────────────┘
```

## Installation

### Prerequisites

- Python 3.11 or higher
- OpenAI API key
- pip or uv for dependency management

### Setup

1. **Clone the repository**

```bash
cd ai_support
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

Modern approach (recommended):

```bash
pip install -e ".[dev,test]"
```

Or using the traditional requirements file:

```bash
pip install -r requirements.txt
```

4. **Configure environment**

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=your-actual-openai-api-key-here
```

5. **Initialize knowledge base**

The knowledge base will be automatically initialized on first run with dummy data from `data/kb_articles.json`.

### Quick Start with Makefile

For convenience, you can use the provided Makefile:

```bash
# Install all dependencies and initialize KB
make all

# Or step by step:
make install-dev  # Install with dev dependencies
make init-kb      # Initialize knowledge base
make run          # Run the API server
```

See all available commands:
```bash
make help
```

## Usage

### Running the API

**Using Makefile (recommended):**

```bash
make run    # Production mode
make dev    # Development mode with auto-reload
```

**Or directly with Python:**

```bash
# Development mode (with auto-reload)
python -m uvicorn app.main:app --reload

# Production mode
python app/main.py
```

**Using Docker:**

```bash
# Using docker-compose (recommended)
docker-compose up

# Or build and run manually
docker build -t triage-agent .
docker run -p 8000:8000 --env-file .env triage-agent
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

#### POST /api/v1/triage

Process a customer ticket through the complete triage workflow.

**Request:**

```bash
curl -X POST "http://localhost:8000/api/v1/triage" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "customer_email": "john.doe@example.com",
    "subject": "Duplicate charge on my invoice",
    "message": "I noticed I was charged twice for the same transaction on December 5th. The amount is $49.99. Can you please help me get a refund?"
  }'
```

**Response:**

```json
{
  "ticket_id": "TKT-2025-01-10-a3f2",
  "timestamp": "2025-01-10T14:32:00Z",
  "triage": {
    "category": "Billing - Invoice Issue",
    "subcategory": "Duplicate Charge",
    "priority": "P2",
    "sla_hours": 24,
    "suggested_team": "Finance Team",
    "sentiment": "frustrated",
    "confidence": 0.92
  },
  "answer_draft": {
    "greeting": "Dear John,",
    "body": "Thank you for reaching out regarding the duplicate charge...",
    "closing": "Best regards,\nSupport Team",
    "tone": "empathetic_professional"
  },
  "citations": [
    {
      "doc_id": "KB-1234",
      "chunk_id": "c-45",
      "title": "How to Handle Duplicate Charges",
      "score": 0.89,
      "url": "https://kb.company.com/billing/duplicate-charges"
    }
  ],
  "policy_check": {
    "refund_promise": false,
    "sla_mentioned": true,
    "escalation_needed": false,
    "compliance": "passed",
    "warnings": []
  }
}
```

#### GET /api/v1/health

Health check endpoint.

```bash
curl http://localhost:8000/api/v1/health
```

#### GET /api/v1/kb/stats

Get knowledge base statistics.

```bash
curl http://localhost:8000/api/v1/kb/stats
```

### Example Requests

**Billing Issue:**

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/triage",
    json={
        "customer_name": "Jane Smith",
        "customer_email": "jane@example.com",
        "subject": "Refund request",
        "message": "I want to cancel my subscription and get a refund."
    }
)

print(response.json())
```

**Technical Issue:**

```python
response = requests.post(
    "http://localhost:8000/api/v1/triage",
    json={
        "customer_name": "Bob Johnson",
        "customer_email": "bob@example.com",
        "subject": "API timeout errors",
        "message": "I'm getting TIMEOUT-500 errors when calling your API."
    }
)

print(response.json())
```

## Testing

### Run Tests

**Using Makefile:**

```bash
make test          # Run all tests
make test-cov      # Run with coverage report
make test-verbose  # Run with verbose output
```

**Or directly with pytest:**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v
```

### Test Structure

- `tests/test_api.py` - API endpoint tests
- `tests/test_models.py` - Pydantic model validation tests
- `tests/test_vector_store.py` - FAISS vector store tests

**Note**: Some integration tests require an OpenAI API key and are skipped by default.

## Project Structure

```
ai_support/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py              # API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings and configuration
│   │   └── dependencies.py        # Dependency injection
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── embeddings.py          # Embedding service
│   │   ├── intent_detection.py   # Intent detection service
│   │   ├── triage.py              # Triage classification
│   │   ├── retrieval.py           # RAG retrieval (query expansion, search, re-rank)
│   │   ├── draft_generator.py    # Response draft generator
│   │   └── policy_checker.py     # Policy compliance checker
│   ├── utils/
│   │   ├── __init__.py
│   │   └── vector_store.py        # FAISS vector store wrapper
│   └── workflows/
│       ├── __init__.py
│       └── langgraph_workflow.py  # LangGraph workflow orchestration
├── data/
│   ├── kb_articles.json           # Dummy knowledge base articles
│   └── faiss_index/               # FAISS index storage (created on init)
├── scripts/
│   ├── __init__.py
│   └── init_kb.py                 # KB initialization script
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest configuration
│   ├── test_api.py                # API tests
│   ├── test_models.py             # Model tests
│   └── test_vector_store.py       # Vector store tests
├── pyproject.toml                 # Project metadata and dependencies
├── requirements.txt               # Python dependencies (legacy)
├── Makefile                       # Development commands
├── Dockerfile                     # Docker container definition
├── docker-compose.yml             # Docker compose configuration
├── .dockerignore                  # Docker ignore file
├── .gitignore                     # Git ignore file
├── .env.example                   # Environment variables template
├── pytest.ini                     # Pytest configuration
├── demo.py                        # Interactive demo script
├── README.md                      # This file
└── QUICKSTART.md                  # Quick start guide
```

## SOLID Principles Implementation

This project follows SOLID principles throughout:

### Single Responsibility Principle (SRP)
- Each service class handles one specific concern
- `IntentDetectionService` - Only intent detection
- `TriageService` - Only triage classification
- `RetrievalService` - Only document retrieval
- `DraftGeneratorService` - Only draft generation
- `PolicyCheckerService` - Only policy validation

### Open/Closed Principle (OCP)
- Services can be extended without modification
- New workflow nodes can be added to LangGraph without changing existing ones
- Vector store can be swapped (FAISS → Pinecone/Weaviate)

### Liskov Substitution Principle (LSP)
- All services implement consistent interfaces
- Pydantic models ensure type safety

### Interface Segregation Principle (ISP)
- Models are focused and minimal
- No model is forced to depend on unused fields

### Dependency Inversion Principle (DIP)
- High-level modules (API, workflows) depend on abstractions (services)
- Dependency injection via FastAPI's `Depends()`
- Settings managed via Pydantic Settings

## Configuration

All configuration is managed via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | OpenAI API key |
| `LLM_MODEL` | `gpt-4-turbo-preview` | OpenAI model for LLM operations |
| `EMBEDDING_MODEL` | `text-embedding-3-large` | OpenAI embedding model |
| `TEMPERATURE` | `0.3` | LLM temperature (0.0-1.0) |
| `MAX_TOKENS` | `2000` | Max tokens for LLM responses |
| `FAISS_INDEX_PATH` | `./data/faiss_index` | Path for FAISS index storage |
| `TOP_K_RETRIEVAL` | `10` | Number of documents to retrieve |
| `TOP_K_RERANK` | `3` | Number of documents after re-ranking |
| `API_HOST` | `0.0.0.0` | API host |
| `API_PORT` | `8000` | API port |

## Dummy Data

The project includes 10 sample KB articles covering:

- Billing (duplicate charges, refunds, cancellations)
- Account management (password reset, locked accounts)
- Technical support (API errors, integrations, data export)
- Feature requests

Articles are in `data/kb_articles.json` and are automatically indexed on startup.

## Performance Metrics

Based on the specification goals:

| Metric | Target | Implementation |
|--------|--------|----------------|
| Triage Accuracy | 90%+ | LLM-based classification with confidence scores |
| Draft Acceptance | 70%+ | Template-based with KB citations |
| Response Time | < 10 min | Real-time processing (~5-15 seconds) |
| SLA Compliance | 95%+ | Automated priority and SLA assignment |
| Citation Precision | 95%+ | Re-ranking with LLM ensures relevance |

## Troubleshooting

### Knowledge base not initialized

```bash
# Check if FAISS index exists
ls -la data/faiss_index/

# If missing, the app will create it on startup
# Check logs for initialization status
```

### OpenAI API errors

```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Check API key validity
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Import errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Development

### Code Quality

**Using Makefile:**

```bash
make format      # Format code with black
make lint        # Check code with ruff
make lint-fix    # Auto-fix linting issues
```

**Or directly:**

```bash
# Format code
black app/ tests/

# Lint code
ruff check app/ tests/

# Fix linting issues
ruff check --fix app/ tests/
```

### Adding New KB Articles

Edit `data/kb_articles.json` and restart the application:

```json
{
  "doc_id": "KB-NEW",
  "title": "New Article Title",
  "category": "Category",
  "url": "https://kb.company.com/new-article",
  "content": "Article content here..."
}
```

Then rebuild the FAISS index:

**Using Makefile:**
```bash
make rebuild-kb
```

**Or manually:**
```bash
rm -rf data/faiss_index/
python app/main.py
```

## Production Deployment

### Recommendations

1. **Use production-grade vector DB**: Replace FAISS with Pinecone, Weaviate, or Qdrant
2. **Add authentication**: Implement API key or JWT authentication
3. **Rate limiting**: Add rate limiting middleware
4. **Monitoring**: Add logging, metrics (Prometheus), and tracing (OpenTelemetry)
5. **Caching**: Add Redis for caching LLM responses
6. **Async processing**: Use Celery for background task processing
7. **Database**: Add PostgreSQL for ticket history and analytics

### Docker Deployment

The project includes a production-ready Dockerfile and docker-compose configuration.

**Using Docker Compose (recommended):**

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Building manually:**

```bash
# Build image
docker build -t customer-service-triage-agent .

# Run container
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name triage-agent \
  customer-service-triage-agent

# View logs
docker logs -f triage-agent
```

**Using Makefile:**

```bash
make docker-build  # Build Docker image
make docker-run    # Run Docker container
```

The Docker image includes:
- Multi-stage build for smaller size
- Health checks
- Proper volume mounts for data persistence
- Environment variable configuration

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: [Create an issue]
- Documentation: `/docs` endpoint when running

---

**Built with**: Python, FastAPI, LangChain, LangGraph, OpenAI, FAISS

**POC/MVP Version** - Ready for demo and testing
