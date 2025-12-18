import os
import uuid
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from domain.models import ChatRequest, ChatResponse
from infrastructure.repositories import InMemConversationRepository
from infrastructure.tool_clients import GeminiClient, QdrantVectorDB
from services.agent import TriageAgent
from services.chat_service import ChatService

# Load Env
load_dotenv()

app = FastAPI(title="Medical Support AI Agent")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DI Container (Simple Singleton for Demo)
class Container:
    def __init__(self):
        self.repo = InMemConversationRepository()
        self.llm_client = GeminiClient()
        self.vector_db = QdrantVectorDB() # Will create local DB
        self.agent = TriageAgent(self.llm_client, self.vector_db)
        self.chat_service = ChatService(self.agent, self.repo)

container = Container()

def get_chat_service():
    return container.chat_service

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Medical Support AI Agent API",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, service: ChatService = Depends(get_chat_service)):
    conv_id = request.conversation_id or str(uuid.uuid4())
    return await service.process_message(conv_id, request.message)

@app.get("/history/{conversation_id}")
async def get_history(conversation_id: str, service: ChatService = Depends(get_chat_service)):
    return await service.get_history(conversation_id)

@app.post("/reset/{conversation_id}")
async def reset_context(conversation_id: str, service: ChatService = Depends(get_chat_service)):
    await service.clear_history(conversation_id)
    return {"status": "cleared"}

@app.post("/seed_kb")
async def seed_kb():
    """Seed the vector DB with some sample medical policies for RAG demo."""
    db = container.vector_db
    policies = [
        {"text": "For password reset, users must verify identity via SMS code.", "source": "KB-Security-01"},
        {"text": "If the Submit button is missing on Call Report, check if the report status is 'Planned' or 'Saved'.", "source": "KB-UI-Issues"},
        {"text": "Tier 1 handles basic login and how-to questions.", "source": "SLA-Definitions"},
        {"text": "Tier 2 handles data integration and specific application errors.", "source": "SLA-Definitions"},
        {"text": "Critical system outages are Tier 3.", "source": "SLA-Definitions"},
    ]
    for p in policies:
        await db.upsert(p["text"], {"source": p["source"]})
    return {"status": "seeded", "count": len(policies)}

# Instructions for developer (as requested)
"""
Usage Instructions:
1. Copy .env.example to .env and set GOOGLE_API_KEY.
2. Build Docker: docker build -t medical-ai-agent .
3. Run Docker: docker run -p 8000:8000 --env-file .env medical-ai-agent
"""
