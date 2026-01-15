# Docker Architecture Documentation

**AI Agent Complex System - Container Architecture**

Last Updated: January 15, 2026

---

## 🏗️ System Overview

The AI Agent Complex application is deployed as a multi-container Docker architecture consisting of 4 primary services:

1. **Backend** - FastAPI application (Python)
2. **Frontend** - React/TypeScript UI
3. **Prometheus** - Metrics collection and storage
4. **Grafana** - Metrics visualization and dashboards

All services are orchestrated using Docker Compose and communicate through a shared Docker network.

---

## 📦 Service Components

### 1. Backend Service

**Purpose**: Core AI agent API server with LangGraph workflow engine

```yaml
Service Name: backend
Container Name: ai-agent-backend
Image: Custom build (./backend/Dockerfile)
Internal Port: 8000
External Port: 8001
```

**Key Features**:
- FastAPI REST API for agent interaction
- LangGraph-based AI agent with multi-tool support
- Session management and conversation history
- Prometheus metrics endpoint (`/metrics`)
- Health check endpoint (`/`)

**Environment Variables**:
- `OPENAI_API_KEY` - Required for LLM operations
- `ALPHAVANTAGE_API_KEY` - For stock/financial data tools
- `ENABLE_METRICS=true` - Activates Prometheus metrics export
- `ENVIRONMENT=dev` - Deployment environment

**Volumes**:
- `./backend/data:/app/data` - Persistent storage for:
  - Session history (`/app/data/sessions/`)
  - User profiles (`/app/data/users/`)
  - Generated files (`/app/data/files/`)

**Health Check**:
- Command: `curl -f http://localhost:8000/`
- Interval: 30s
- Timeout: 10s
- Retries: 3
- Start period: 40s

**Dependencies**: None (base service)

---

### 2. Frontend Service

**Purpose**: User interface for chat interaction with the AI agent

```yaml
Service Name: frontend
Container Name: ai-agent-frontend
Image: Custom build (./frontend/Dockerfile)
Internal Port: 3000
External Port: 3000
```

**Key Features**:
- React-based chat interface
- Real-time message streaming
- Session management UI
- Profile editing capabilities

**Dependencies**:
- `depends_on: backend` - Waits for backend to start

**Health Check**:
- Command: `wget --quiet --tries=1 --spider http://localhost:3000`
- Interval: 30s
- Timeout: 10s
- Retries: 3
- Start period: 40s

**API Communication**:
- Connects to backend at: `http://backend:8000` (internal) or `http://localhost:8001` (external)

---

### 3. Prometheus Service

**Purpose**: Metrics collection, storage, and time-series database

```yaml
Service Name: prometheus
Container Name: ai-agent-prometheus
Image: prom/prometheus:latest
Internal Port: 9090
External Port: 9090
```

**Key Features**:
- Scrapes metrics from backend `/metrics` endpoint
- Time-series database for metric storage
- Query engine for metric analysis
- Retention: 15 days or 10GB

**Configuration**:
- Config file: `./observability/prometheus.yml`
- Scrape interval: Defined in prometheus.yml (typically 15s)
- Storage path: `/prometheus` (persistent volume)

**Volumes**:
- `./observability/prometheus.yml:/etc/prometheus/prometheus.yml:ro` - Configuration (read-only)
- `prometheus-data:/prometheus` - Persistent metric storage

**Command Arguments**:
```bash
--config.file=/etc/prometheus/prometheus.yml
--storage.tsdb.path=/prometheus
--storage.tsdb.retention.time=15d
--storage.tsdb.retention.size=10GB
--web.console.libraries=/usr/share/prometheus/console_libraries
--web.console.templates=/usr/share/prometheus/consoles
```

**Dependencies**: None (can run independently)

---

### 4. Grafana Service

**Purpose**: Metrics visualization and dashboard platform

```yaml
Service Name: grafana
Container Name: ai-agent-grafana
Image: grafana/grafana:latest
Platform: linux/amd64
Internal Port: 3000
External Port: 3001
```

**Key Features**:
- Pre-configured dashboards for AI agent metrics
- Automatic provisioning of data sources and dashboards
- User authentication and access control

**Environment Variables**:
- `GF_SECURITY_ADMIN_USER=admin` - Admin username
- `GF_SECURITY_ADMIN_PASSWORD=admin` - Admin password
- `GF_USERS_ALLOW_SIGN_UP=false` - Disable public registration

**Volumes**:
- `grafana-data:/var/lib/grafana` - Persistent storage for settings and data
- `./observability/grafana/provisioning:/etc/grafana/provisioning` - Auto-provisioning configs
- `./observability/grafana/dashboards:/var/lib/grafana/dashboards` - Dashboard JSON files

**Pre-configured Dashboards**:
1. **LLM Dashboard** - Inference metrics, tokens, latency, costs
2. **Agent Workflow Dashboard** - Tool calls, node execution, workflow metrics
3. **RAG Dashboard** - Retrieval, embedding, vector DB metrics
4. **Cost Dashboard** - Model costs, burn rate, cost per workflow

**Dependencies**:
- `depends_on: prometheus` - Requires Prometheus as data source

**Access**:
- URL: http://localhost:3001
- Credentials: admin/admin

---

## 🔗 Component Relationships

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                         User Browser                         │
└────────────┬─────────────────────────────────┬───────────────┘
             │                                 │
             │ Port 3000                       │ Port 3001
             │ (Chat UI)                       │ (Dashboards)
             ▼                                 ▼
┌─────────────────────────┐         ┌──────────────────────────┐
│   Frontend Container    │         │   Grafana Container      │
│   (React/TypeScript)    │         │   (Visualization)        │
│   Port 3000             │         │   Port 3001              │
└────────────┬────────────┘         └──────────┬───────────────┘
             │                                 │
             │ HTTP API                        │ PromQL Queries
             │ (Port 8000)                     │ (Port 9090)
             ▼                                 ▼
┌─────────────────────────┐         ┌──────────────────────────┐
│   Backend Container     │◄────────│  Prometheus Container    │
│   (FastAPI/LangGraph)   │ Scrape  │  (Metrics Storage)       │
│   Port 8001             │ Metrics │  Port 9090               │
│   /metrics endpoint     │         │                          │
└─────────────────────────┘         └──────────────────────────┘
             │
             │ Persistent Storage
             ▼
┌─────────────────────────┐
│   Docker Volume         │
│   ./backend/data        │
│   - sessions/           │
│   - users/              │
│   - files/              │
└─────────────────────────┘
```

### Data Flow

#### 1. User Chat Flow
```
User → Frontend (Port 3000) 
     → Backend API (Port 8001, /v1/agent/chat) 
     → LangGraph Agent 
     → LLM (OpenAI) 
     → Tools (weather, crypto, etc.) 
     → Response → Frontend → User
```

#### 2. Metrics Flow
```
Backend Agent Execution 
     → Metrics Recording (Prometheus Python client) 
     → /metrics endpoint 
     → Prometheus Scraper (every 15s) 
     → Time-series DB 
     → Grafana Queries 
     → Dashboard Visualization
```

#### 3. Persistence Flow
```
Agent Creates File/Session 
     → Backend writes to /app/data 
     → Docker volume mount 
     → Host filesystem ./backend/data 
     → Persistent across container restarts
```

---

## 🌐 Network Architecture

### Docker Network
All services run on the default Docker Compose network, enabling:
- Service discovery by container name
- Internal DNS resolution
- Isolated network namespace

### Internal Communication
- **Frontend → Backend**: `http://backend:8000`
- **Prometheus → Backend**: `http://backend:8000/metrics`
- **Grafana → Prometheus**: `http://prometheus:9090`

### External Access
| Service    | Internal Port | External Port | URL                        |
|------------|---------------|---------------|----------------------------|
| Frontend   | 3000          | 3000          | http://localhost:3000      |
| Backend    | 8000          | 8001          | http://localhost:8001      |
| Prometheus | 9090          | 9090          | http://localhost:9090      |
| Grafana    | 3000          | 3001          | http://localhost:3001      |

---

## 💾 Persistent Storage

### Named Volumes

```yaml
volumes:
  backend_data:      # User data, sessions, files
  prometheus-data:   # Metrics time-series database
  grafana-data:      # Dashboard configs, user settings
```

### Volume Lifecycle
- Created on first `docker-compose up`
- Persist across container restarts
- Must be manually removed with `docker-compose down -v`

### Bind Mounts
- `./backend/data` → Backend user data (sessions, profiles, files)
- `./observability/prometheus.yml` → Prometheus configuration
- `./observability/grafana/provisioning` → Grafana auto-provisioning
- `./observability/grafana/dashboards` → Dashboard JSON definitions

---

## 🚀 Deployment Commands

### Start All Services
```bash
docker-compose up -d
```

### Start Specific Service
```bash
docker-compose up -d backend
docker-compose up -d frontend
```

### Rebuild and Start
```bash
docker-compose up -d --build
```

### View Logs
```bash
docker-compose logs -f backend
docker-compose logs -f --tail=100 prometheus
```

### Stop All Services
```bash
docker-compose down
```

### Stop and Remove Volumes (⚠️ Deletes Data)
```bash
docker-compose down -v
```

### Check Service Status
```bash
docker-compose ps
```

### Execute Commands in Container
```bash
docker exec -it ai-agent-backend bash
docker exec ai-agent-backend cat /app/main.py
```

---

## 🔍 Health Monitoring

### Service Health Checks

All services define health checks in docker-compose.yml:

**Backend**:
```bash
curl -f http://localhost:8000/
```

**Frontend**:
```bash
wget --quiet --tries=1 --spider http://localhost:3000
```

### Verify All Services Running
```bash
docker-compose ps
# All services should show "Up" status
```

### Check Backend Metrics Endpoint
```bash
curl http://localhost:8001/metrics
# Should return Prometheus-formatted metrics
```

### Prometheus Targets
Navigate to: http://localhost:9090/targets
- Backend target should be "UP"

### Grafana Health
Navigate to: http://localhost:3001
- Login with admin/admin
- Check "AI Agent" folder for dashboards

---

## 📊 Metrics Architecture

### Metrics Export (Backend)
- Library: `prometheus_client` (Python)
- Endpoint: `http://localhost:8001/metrics`
- Format: Prometheus exposition format
- Instrumentation: 
  - LLM calls (tokens, latency, cost)
  - Tool invocations
  - Agent execution time
  - RAG operations

### Metrics Collection (Prometheus)
- Scrape interval: 15s
- Scrape timeout: 10s
- Retention: 15 days or 10GB
- Storage: TSDB (Time-Series Database)

### Metrics Visualization (Grafana)
- Data source: Prometheus
- Query language: PromQL
- Refresh intervals: 5s to 1m
- Dashboard provisioning: Automatic on startup

---

## 🔒 Security Considerations

### Current Configuration (Development)
⚠️ **Not production-ready** - Current setup is for development/testing

**Known Security Issues**:
1. Grafana default credentials (admin/admin)
2. No TLS/SSL encryption
3. Services exposed directly on host ports
4. No authentication on Prometheus
5. API keys in environment variables (should use secrets management)

### Production Recommendations
- [ ] Change Grafana admin password
- [ ] Use Docker secrets for API keys
- [ ] Add reverse proxy (Nginx) with TLS
- [ ] Implement API authentication/authorization
- [ ] Restrict Prometheus/Grafana access
- [ ] Use separate networks for services
- [ ] Enable CORS restrictions on backend
- [ ] Set up log aggregation and audit trails

---

## 🛠️ Troubleshooting

### Backend Won't Start
```bash
# Check if OPENAI_API_KEY is set
docker-compose logs backend | grep OPENAI_API_KEY

# Verify port not in use
lsof -i :8001

# Check data volume permissions
ls -la ./backend/data
```

### Frontend Can't Connect to Backend
```bash
# Check if backend is running
docker-compose ps backend

# Test backend endpoint
curl http://localhost:8001/

# Check frontend environment/config
docker exec ai-agent-frontend cat /app/.env
```

### Prometheus Not Scraping
```bash
# Check Prometheus config
docker exec ai-agent-prometheus cat /etc/prometheus/prometheus.yml

# Verify backend metrics endpoint
curl http://localhost:8001/metrics

# Check Prometheus targets UI
open http://localhost:9090/targets
```

### Grafana Dashboards Missing
```bash
# Check provisioning config
docker exec ai-agent-grafana ls /etc/grafana/provisioning/dashboards

# Verify dashboard files
docker exec ai-agent-grafana ls /var/lib/grafana/dashboards

# Restart Grafana
docker-compose restart grafana
```

---

## 📋 Service Dependencies Startup Order

Docker Compose ensures proper startup order:

```
1. Backend (no dependencies)
   ↓
2. Frontend (depends_on: backend)
   ↓
3. Prometheus (no dependencies, but scrapes backend)
   ↓
4. Grafana (depends_on: prometheus)
```

**Note**: `depends_on` only waits for container start, not full service readiness. Health checks ensure services are actually ready.

---

## 🔄 Restart Policies

All services use `restart: unless-stopped`:
- Automatically restart on failure
- Restart on Docker daemon restart
- Don't restart if manually stopped

---

## 📁 Directory Structure

```
ai_agent_complex/
├── docker-compose.yml          # Multi-container orchestration
├── backend/
│   ├── Dockerfile              # Backend container definition
│   ├── requirements.txt        # Python dependencies
│   ├── main.py                 # FastAPI application entry
│   ├── data/                   # Persistent data (volume mount)
│   │   ├── sessions/           # Conversation histories
│   │   ├── users/              # User profiles
│   │   └── files/              # Generated files
│   └── ...
├── frontend/
│   ├── Dockerfile              # Frontend container definition
│   ├── package.json            # Node.js dependencies
│   └── ...
└── observability/
    ├── prometheus.yml          # Prometheus config (volume mount)
    └── grafana/
        ├── provisioning/       # Auto-provision configs (volume mount)
        └── dashboards/         # Dashboard JSON files (volume mount)
```

---

## ✅ Quick Start Checklist

- [ ] Set `OPENAI_API_KEY` environment variable
- [ ] (Optional) Set `ALPHAVANTAGE_API_KEY` for stock tools
- [ ] Run `docker-compose up -d`
- [ ] Wait 30-60 seconds for all health checks to pass
- [ ] Verify services: `docker-compose ps`
- [ ] Access frontend: http://localhost:3000
- [ ] Access Grafana: http://localhost:3001 (admin/admin)
- [ ] Send test prompt to generate metrics
- [ ] Check Grafana dashboards for data

---

## 📚 Related Documentation

- [MONITORING_TEST_PROMPTS.md](MONITORING_TEST_PROMPTS.md) - Test prompts for metrics
- [docs/09_MONITORING_PROMPT.md](docs/09_MONITORING_PROMPT.md) - Monitoring implementation guide
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Application architecture details
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide

---

**End of Document**
