# Quick Start Guide

Get the Customer Service Triage Agent running in 5 minutes!

## Prerequisites

- Python 3.11+
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

## Installation

### 1. Set up virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

**Modern approach (recommended):**

```bash
pip install -e ".[dev,test]"
```

**Or using requirements.txt:**

```bash
pip install -r requirements.txt
```

### 3. Configure OpenAI API key

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

## Running the Demo

### Interactive Demo

Run the demo script to see the complete workflow in action:

```bash
python demo.py
```

This will process 3 sample tickets and show:
- Intent detection
- Triage classification
- RAG retrieval
- Draft generation
- Policy check

### API Server

Start the FastAPI server:

```bash
python app/main.py
```

Visit the interactive API docs at: http://localhost:8000/docs

### Test a Ticket

**Using curl:**

```bash
curl -X POST "http://localhost:8000/api/v1/triage" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "subject": "Duplicate charge",
    "message": "I was charged twice for the same transaction. Can I get a refund?"
  }'
```

**Using Python:**

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/triage",
    json={
        "customer_name": "John Doe",
        "customer_email": "john@example.com",
        "subject": "Duplicate charge",
        "message": "I was charged twice. Can I get a refund?"
    }
)

print(response.json())
```

**Using the interactive docs:**

1. Go to http://localhost:8000/docs
2. Click on `POST /api/v1/triage`
3. Click "Try it out"
4. Edit the request body
5. Click "Execute"

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test
pytest tests/test_models.py -v
```

## Troubleshooting

### "OpenAI API key not found"

Make sure your `.env` file exists and contains:
```env
OPENAI_API_KEY=sk-...
```

### "Knowledge base not initialized"

The KB is automatically initialized on startup. Check logs:
```bash
python app/main.py
```

You should see:
```
Initializing knowledge base...
Creating embeddings for X chunks...
Knowledge base initialized with X documents
```

### "Module not found"

Reinstall dependencies:
```bash
pip install -e ".[dev,test]"  # Modern approach
# Or
pip install -r requirements.txt --force-reinstall
```

## Available Commands (Makefile)

For convenience, use the Makefile:

```bash
make help         # Show all available commands
make install-dev  # Install with dev dependencies
make run          # Run the API server
make dev          # Run with auto-reload
make demo         # Run interactive demo
make test         # Run tests
make test-cov     # Run tests with coverage
make lint         # Check code quality
make format       # Format code
make clean        # Clean up generated files
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Add your own KB articles to [data/kb_articles.json](data/kb_articles.json)
- Explore the API at http://localhost:8000/docs
- Run the test suite with `pytest`
- Check out the code structure in the README

## Project Structure (Simplified)

```
ai_support/
├── app/
│   ├── main.py              # Start here - FastAPI app
│   ├── api/routes.py        # API endpoints
│   ├── models/schemas.py    # Data models
│   ├── services/            # Business logic (intent, triage, RAG, etc.)
│   └── workflows/           # LangGraph orchestration
├── data/
│   └── kb_articles.json     # Knowledge base articles
├── tests/                   # Test suite
├── demo.py                  # Interactive demo
└── .env                     # Your config (create this!)
```

## Key Features Demonstrated

1. **Intent Detection** - Automatically classifies problem type & sentiment
2. **Smart Triage** - Assigns priority (P1-P4) and SLA times
3. **RAG Retrieval** - Finds relevant KB articles using vector search
4. **Draft Generation** - Creates professional responses with citations
5. **Policy Validation** - Ensures compliance with company policies

## Sample Output

When you process a ticket, you'll get:

```json
{
  "ticket_id": "TKT-2025-01-10-a3f2",
  "triage": {
    "category": "Billing - Invoice Issue",
    "priority": "P2",
    "sla_hours": 24,
    "sentiment": "frustrated"
  },
  "answer_draft": {
    "greeting": "Dear John,",
    "body": "Thank you for reaching out... [KB-1234]",
    "closing": "Best regards,\nSupport Team"
  },
  "citations": [...],
  "policy_check": {
    "compliance": "passed"
  }
}
```

---

**Ready to go?** Run `python demo.py` or `python app/main.py`!
