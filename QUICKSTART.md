# 🚀 AI Agent with RAG - Quick Start Guide

## Prerequisites

- Python 3.9+ installed
- Node.js 16+ and npm installed
- OpenAI API key

## 1. Set up Environment

```bash
# Copy and edit .env file
cp backend/.env.example backend/.env

# Edit backend/.env and add your OpenAI API key:
# OPENAI_API_KEY=sk-your-actual-key-here
```

## 2. Start the Application

```bash
# Make scripts executable (first time only)
chmod +x start_app.sh stop_app.sh

# Start everything
./start_app.sh
```

The script will:
- ✅ Create necessary directories
- ✅ Install backend dependencies (Python packages)
- ✅ Install frontend dependencies (npm packages)
- ✅ Start backend server on http://localhost:8000
- ✅ Start frontend server on http://localhost:5173

## 3. Test RAG Functionality

### Upload a Test Document

1. Open http://localhost:5173 in your browser
2. Find the "📄 Document Upload" panel in the left sidebar
3. Click "Choose File" and select `test_document.txt` (provided in project root)
4. Click "Upload"
5. Verify: "✓ Uploaded: test_document.txt (X chunks)" appears
6. Check header shows: "📄 Docs: 1 | Chunks: X"

### Ask Questions

Try these queries to test RAG:

```
What embedding model does the RAG system use?
```
**Expected**: Response mentions "text-embedding-3-small" with citation [RAG-1]

```
How many nodes are in the RAG pipeline?
```
**Expected**: Response mentions "5 nodes" or "five nodes" with citations

```
What is the retrieval-before-tools principle?
```
**Expected**: Response explains the architecture with citations

### Verify RAG Features

1. **Citations**: Look for [RAG-1], [RAG-2] in responses
2. **Debug Panel**: Click "🔧 Debug Panel" to see:
   - 🔍 RAG Context (rewritten query, citations, chunk count)
   - Retrieved chunk previews (first 200 chars)
   - 📊 RAG Metrics (latencies, similarity scores)
3. **Document Management**: Click 🗑️ to delete documents

## 4. Stop the Application

```bash
./stop_app.sh
```

## 5. View Logs

```bash
# Backend logs
tail -f backend.log

# Frontend logs
tail -f frontend.log
```

## Troubleshooting

### "OPENAI_API_KEY not set"
- Edit `backend/.env` and add your actual OpenAI API key

### "Backend failed to start"
- Check `backend.log` for errors
- Ensure port 8000 is not in use: `lsof -i :8000`
- Try: `cd backend && source venv/bin/activate && python -m pip install -r requirements.txt`

### "RAG services not available"
- Check backend logs for ChromaDB errors
- Ensure `backend/data/rag/chroma/` directory exists
- Verify OpenAI API key is valid

### Frontend errors
- Check `frontend.log`
- Ensure port 5173 is not in use: `lsof -i :5173`
- Try: `cd frontend && npm install`

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/

## Architecture Overview

```
User Query
    ↓
RAG Subgraph (5 nodes)
    ↓
Agent (with RAG context)
    ↓
Tools (if needed)
    ↓
Response with Citations
```

**RAG Pipeline:**
1. QueryRewrite → 2. Retrieve → 3. ContextBuilder → 4. Guardrail → 5. Feedback

## Project Structure

```
ai_agent_complex/
├── backend/
│   ├── rag/              # RAG implementation
│   ├── services/         # Agent and chat services
│   ├── domain/           # Models and interfaces
│   ├── infrastructure/   # Repositories
│   └── data/             # Storage (created on start)
├── frontend/
│   └── src/
│       ├── components/   # React components
│       ├── api.ts        # API client
│       └── types.ts      # TypeScript types
├── start_app.sh          # Start script
├── stop_app.sh           # Stop script
└── test_document.txt     # Sample document
```

## Success Criteria ✅

- [ ] Application starts without errors
- [ ] Can upload .txt or .md files
- [ ] Queries return responses with [RAG-1] citations
- [ ] Debug panel shows RAG context and metrics
- [ ] Can delete documents
- [ ] Header shows document/chunk counts

## Next Steps

- Upload your own documents (.txt, .md)
- Explore the Debug Panel for performance metrics
- Try the "reset context" command
- Check out the Swagger docs at http://localhost:8000/docs

Enjoy your AI Agent with RAG! 🎉
