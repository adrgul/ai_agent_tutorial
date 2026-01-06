#!/bin/bash
# Stop script for AI Agent with RAG

echo "🛑 Stopping AI Agent..."

# Stop backend
if [ -f ".backend.pid" ]; then
    BACKEND_PID=$(cat .backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        sleep 1
        # Force kill if still running
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            kill -9 $BACKEND_PID 2>/dev/null || true
        fi
        echo "✅ Backend stopped"
    fi
    rm -f .backend.pid
fi

# Stop frontend
if [ -f ".frontend.pid" ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        sleep 1
        # Force kill if still running
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            kill -9 $FRONTEND_PID 2>/dev/null || true
        fi
        echo "✅ Frontend stopped"
    fi
    rm -f .frontend.pid
fi

# Clean up any remaining processes
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

echo "✅ Application stopped"
