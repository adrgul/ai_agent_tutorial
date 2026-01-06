# 🐳 AI Agent with RAG - Docker Quick Start

This is a **Docker-based application**. Use Docker Compose to run everything with a single command!

## Prerequisites

- Docker installed
- Docker Compose installed
- OpenAI API key

## 🚀 Quick Start (3 steps)

### 1. Set your OpenAI API Key

```bash
# Create .env file in project root
echo "OPENAI_API_KEY=sk-your-actual-key-here" > .env
```

Or export it in your terminal:
```bash
export OPENAI_API_KEY=sk-your-actual-key-here
```

### 2. Start the Application

```bash
docker-compose up --build
```

That's it! Docker will:
- ✅ Build backend and frontend images
- ✅ Install all dependencies
- ✅ Create necessary directories
- ✅ Start both services
- ✅ Set up networking

**Services will be available at:**
- 🌐 **Frontend**: http://localhost:3000
- 📡 **Backend API**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs

### 3. Test RAG Functionality

1. Open http://localhost:3000 in your browser
2. Upload the test document:
   - Use the "📄 Document Upload" panel in the sidebar
   - Select `test_document.txt` from the project root
   - Click "Upload"
3. Ask questions:
   ```
   What embedding model does the RAG system use?
   How many nodes are in the RAG pipeline?
   ```
4. Verify citations like [RAG-1], [RAG-2] appear in responses
5. Check the Debug Panel (🔧) for RAG metrics

## 📝 Commands

### Start (build and run)
```bash
docker-compose up --build
```

### Start in background
```bash
docker-compose up -d
```

### View logs
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

### Stop
```bash
docker-compose down
```

### Stop and remove volumes (clean slate)
```bash
docker-compose down -v
```

### Restart a service
```bash
# Restart backend
docker-compose restart backend

# Restart frontend
docker-compose restart frontend
```

## 🐛 Troubleshooting

### Port already in use
If ports 3000 or 8000 are already in use:

```bash
# Find process using port 3000
lsof -i :3000

# Find process using port 8000
lsof -i :8000

# Kill the process or change ports in docker-compose.yml
```

### Backend health check failing
```bash
# Check backend logs
docker-compose logs backend

# Common issues:
# - OPENAI_API_KEY not set
# - ChromaDB initialization error
# - Missing dependencies
```

### "OPENAI_API_KEY not set"
Make sure you either:
- Created `.env` file in project root with `OPENAI_API_KEY=sk-...`
- Or exported: `export OPENAI_API_KEY=sk-...`

### Rebuild after code changes
```bash
docker-compose up --build
```

### Access container shell
```bash
# Backend
docker exec -it ai-agent-backend bash

# Frontend
docker exec -it ai-agent-frontend sh
```

## 📂 Data Persistence

Docker volume `./backend/data` is mounted to persist:
- ChromaDB vector database: `data/rag/chroma/`
- Uploaded documents: `data/rag/uploads/`
- User profiles: `data/users/`
- Conversation history: `data/sessions/`

Even if you stop containers, your data remains!

## 🔧 Docker Compose Configuration

The `docker-compose.yml` includes:
- **Backend**: Python 3.11, FastAPI, ChromaDB, RAG system
- **Frontend**: Node.js, React, Vite
- **Networking**: Automatic service discovery
- **Health checks**: Automatic restart if unhealthy
- **Volume mounts**: Data persistence

## 📊 Resource Usage

Typical resource usage:
- **Backend**: ~500MB RAM, 1 CPU
- **Frontend**: ~200MB RAM, 0.5 CPU
- **ChromaDB**: Grows with document count

## 🎯 Testing the RAG System

### Upload Test Document
```bash
# The test_document.txt is in the project root
# Upload it via the UI at http://localhost:3000
```

### Example Queries
```
What is the architecture of the RAG system?
Which embedding model is used?
Explain the 5 RAG pipeline nodes
What are the API endpoints?
```

### Verify Features
- ✅ Citations appear as [RAG-1], [RAG-2]
- ✅ Debug Panel shows RAG Context and Metrics
- ✅ Header displays document/chunk counts
- ✅ Can delete documents via 🗑️ button

## 🚀 Production Deployment

For production, consider:

1. **Environment variables**: Use proper secrets management
2. **HTTPS**: Add reverse proxy (nginx, traefik)
3. **Database**: Consider external vector DB for scale
4. **Monitoring**: Add logging aggregation
5. **Backups**: Backup `./backend/data` regularly

Example nginx config:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
    }

    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

## 📖 Next Steps

- Read [QUICKSTART.md](QUICKSTART.md) for detailed testing steps
- Check [backend/README.md](backend/README.md) for architecture details
- Explore API docs at http://localhost:8000/docs
- Upload your own documents and start querying!

## ✨ What's Been Implemented

✅ **Complete RAG Integration**
- 5-node LangGraph pipeline (QueryRewrite → Retrieve → ContextBuilder → Guardrail → Feedback)
- ChromaDB vector database with multi-tenancy
- OpenAI text-embedding-3-small (1536 dimensions)
- Paragraph-aware chunking (500-700 tokens, 10-15% overlap)
- Citation enforcement in agent responses

✅ **Full-Stack Features**
- Document upload (.txt, .md files)
- Document management (list, delete)
- RAG stats in header
- Debug panel with chunk previews
- Performance metrics tracking

✅ **Production-Ready**
- Docker containerization
- Health checks
- Data persistence
- Error handling
- Clean architecture (SOLID principles)

Enjoy your AI Agent with RAG! 🎉
