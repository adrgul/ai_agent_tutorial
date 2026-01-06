#!/bin/bash
# Startup script for AI Agent with RAG

set -e

echo "🚀 Starting AI Agent with RAG Integration"
echo "========================================="

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Check for .env file
if [ ! -f "backend/.env" ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        echo "✅ Created backend/.env - PLEASE ADD YOUR OPENAI_API_KEY!"
        echo ""
        echo "Edit backend/.env and add your OpenAI API key, then run this script again."
        exit 1
    else
        echo "❌ Error: No .env.example found"
        exit 1
    fi
fi

# Check for OPENAI_API_KEY
source backend/.env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo "❌ Error: OPENAI_API_KEY not set in backend/.env"
    echo "Please edit backend/.env and add your OpenAI API key"
    exit 1
fi

echo "✅ Environment configured"

# Create necessary directories
echo ""
echo "📁 Creating data directories..."
mkdir -p backend/data/rag/chroma
mkdir -p backend/data/rag/uploads
mkdir -p backend/data/users
mkdir -p backend/data/sessions
mkdir -p backend/data/files
echo "✅ Data directories created"

# Check Python version
echo ""
echo "🐍 Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "✅ Found $PYTHON_VERSION"

# Install backend dependencies
echo ""
echo "📦 Installing backend dependencies..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Backend dependencies installed"

# Check Node.js
echo ""
echo "📦 Checking Node.js..."
cd ../frontend
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm not found. Please install Node.js"
    exit 1
fi
NODE_VERSION=$(node --version)
echo "✅ Found Node.js $NODE_VERSION"

# Install frontend dependencies
echo ""
echo "📦 Installing frontend dependencies..."
if [ ! -d "node_modules" ]; then
    npm install
else
    echo "✅ Dependencies already installed"
fi

# Start backend
echo ""
echo "========================================="
echo "🚀 Starting Backend Server..."
echo "========================================="
cd ../backend
source venv/bin/activate

# Start backend in background
uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID) - Logs: backend.log"
echo "   📡 API: http://localhost:8000"
echo "   📚 Docs: http://localhost:8000/docs"

# Wait for backend to be ready
echo ""
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start. Check backend.log"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
    echo -n "."
done

# Start frontend
echo ""
echo "========================================="
echo "🚀 Starting Frontend Server..."
echo "========================================="
cd ../frontend

npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID) - Logs: frontend.log"
echo "   🌐 App: http://localhost:5173"

# Save PIDs
cd ..
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid

echo ""
echo "========================================="
echo "✅ APPLICATION RUNNING!"
echo "========================================="
echo ""
echo "🌐 Open your browser to: http://localhost:5173"
echo ""
echo "📋 Quick Test:"
echo "   1. Upload a .txt or .md file in the sidebar"
echo "   2. Ask a question about the content"
echo "   3. See citations like [RAG-1] in the response"
echo "   4. Check Debug Panel for RAG metrics"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "🛑 To stop: ./stop_app.sh"
echo ""
echo "Press Ctrl+C to stop monitoring..."
echo ""

# Monitor logs
trap 'echo ""; echo "Stopping..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; rm -f .backend.pid .frontend.pid; exit' INT

tail -f backend.log frontend.log
