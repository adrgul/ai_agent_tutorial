# MedicalSupportAI (Pharma CRM Triage Agent)

A specialized AI agent for medical/pharmaceutical support triage, capable of categorizing tickets (Tier 1-3) and drafting policy-compliant responses using Google's AI stack.

## Architecture

- **Backend**: Python (FastAPI), LangGraph, Google Gemini, Qdrant.
- **Frontend**: React (Vite), TailwindCSS.
- **Protocol**: REST API.

## Prerequisites

- Docker & Docker Compose (optional)
- Node.js 18+
- Python 3.11+
- Google Cloud API Key (AI Studio or Vertex AI)

## Setup & Running

### 1. Backend Setup

1. Navegate to `backend`:
   ```bash
   cd backend
   ```
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure Environment:
   Copy `.env.example` to `.env` and add your key:
   ```bash
   cp .env.example .env
   # Edit .env and set GOOGLE_API_KEY
   ```
5. Run Server:
   ```bash
   uvicorn main:app --reload
   ```
   Server runs at `http://localhost:8000`.

### 2. Frontend Setup

1. Navigate to `frontend`:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run Development Server:
   ```bash
   npm run dev
   ```
   App runs at `http://localhost:5173`.

### 3. Usage

1. Open the frontend URL.
2. Click the "Database" icon in the header to **Seed the Knowledge Base** (loads sample policies into Vector DB).
3. Type a medical support query (e.g., "I cannot login to the CLM app" or "Submit button missing on Call Report").
4. Observe the agent's response and the "Debug Panel" showing the Triage Decision and Logic.

### Docker Usage (Backend Only)

Build and run the backend container:
```bash
cd backend
docker build -t medical-ai-agent .
docker run -p 8000:8000 --env-file .env medical-ai-agent
```
