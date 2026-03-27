# 🚀 ARC Platform — Complete Instructions

> **Agentic Research & Work Copilot** — AI SaaS platform that orchestrates multiple agents to plan, research, analyse, code, validate, and deliver research reports.

---

## 📁 Project Structure

```
BrainWeave/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py             # FastAPI app + lifespan
│   │   ├── config.py           # Pydantic-settings (env vars)
│   │   ├── database.py         # MongoDB (Motor) + Redis connections
│   │   ├── middleware.py       # Trace ID + request size limit
│   │   ├── deps.py             # FastAPI dependency injection
│   │   ├── models/             # 8 Pydantic MongoDB document models
│   │   ├── security/           # JWT, passwords, rate limit, prompt filter,
│   │   │                         loop detector, audit logs, prompt versioning
│   │   ├── agents/             # 7 AI agents + orchestrator
│   │   ├── tools/              # 6 tools + registry
│   │   ├── rag/                # Ingestion, chunking, embeddings, retriever
│   │   ├── services/           # Auth, task, file business logic
│   │   ├── routes/             # REST + WebSocket API routes
│   │   ├── workers/            # Redis background task worker
│   │   └── observability/      # Structured logging + metrics
│   ├── tests/                  # pytest test suite
│   ├── requirements.txt
│   ├── Dockerfile
│   └── Dockerfile.worker
├── frontend/                   # Next.js 15 + TypeScript + TailwindCSS
│   ├── src/
│   │   ├── app/                # Pages (landing, login, dashboard, etc.)
│   │   ├── hooks/              # useAuth, useTask, useWebSocket
│   │   ├── lib/                # API client, WebSocket client, utilities
│   │   └── types/              # TypeScript type definitions
│   ├── Dockerfile
│   ├── package.json
│   └── tailwind.config.ts
├── docker-compose.yml          # 5 services: Mongo, Redis, backend, worker, frontend
├── .env.example                # All environment variables
└── INSTRUCTIONS.md             # ← You are here
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.11+, Node.js 20+, MongoDB, Redis
- OR: Docker & Docker Compose

### Option 1: Local Development (Recommended for Windows / Fast Setup)
This is the recommended way to run the project for college presentations, as it avoids a massive 2GB+ PyTorch download inside Docker.

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Set your Groq API key in .env
# GROQ_API_KEY=gsk_your_key_here

# 3. Backend API (Terminal 1)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. Background Worker (Terminal 2)
cd backend
python -m app.workers.task_worker

# 5. Frontend UI (Terminal 3)
cd frontend
npm install
npm run dev
```
> **Access at:** http://localhost:3000

### Option 2: Docker Setup (Requires Fast Internet)
*Note: Docker will download heavy ML libraries (PyTorch ~1GB). If your internet is slow, this build may timeout (`pip install timeout`).*
```bash
# 1. Start everything 
docker-compose up --build -d

# 2. Access
#    Frontend → http://localhost:3000
#    Backend API → http://localhost:8000
```

---

## 🔑 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | **Yes** | — | Your Groq API key (get from [console.groq.com](https://console.groq.com)) |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | LLM model for agents |
| `MONGO_URI` | No | `mongodb://localhost:27017` | MongoDB connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string |
| `JWT_SECRET_KEY` | **Yes** (prod) | dev default | Secret for JWT signing (32+ chars) |
| `MAX_TASK_BUDGET_USD` | No | `5.00` | Max spend per task |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Local embedding model (no API key needed) |

---

## 🤖 Agent System

The platform uses **7 specialized agents** orchestrated in a dependency graph:

| Agent | Role | Tools Used |
|-------|------|------------|
| **Planner** | Breaks user goal into subtasks | — |
| **Research** | Finds sources & extracts claims | Web Search, Paper Search |
| **Data** | Analyses datasets, runs EDA | Dataset Search, Python Sandbox |
| **Code** | Writes & runs analysis code | Python Sandbox |
| **Critic** | Validates outputs for accuracy | Citation Verify, Vector Search |
| **Report** | Generates final research report | — |
| **Repair** | Fixes failed steps automatically | (inherits from failed agent) |

### How It Works
1. User submits a research task
2. **Planner** decomposes it into steps with dependencies
3. **Orchestrator** executes steps (parallel when possible)
4. Each agent calls tools, tracks cost, logs to MongoDB
5. **Critic** validates, triggers **Repair** on failures
6. **Report** assembles final output with citations
7. Results streamed via WebSocket in real time

---

## 🔧 Tool System

| Tool | API Used | Auth Required | Description |
|------|----------|---------------|-------------|
| Web Search | DuckDuckGo Instant Answer | No | General web search |
| Paper Search | Semantic Scholar | No | Academic paper discovery |
| Dataset Search | HuggingFace Hub | No | Dataset discovery |
| Python Sandbox | Local subprocess | No | Sandboxed code execution |
| Vector Search | MongoDB (local) | No | RAG document retrieval |
| Citation Verify | HTTP HEAD requests | No | URL accessibility check |

---

## 📚 RAG Memory System

| Stage | Implementation | Notes |
|-------|---------------|-------|
| **Ingestion** | `rag/ingestion.py` | Supports txt, md, csv, json, pdf |
| **Chunking** | `rag/chunker.py` | Recursive splitter, 512 chars, 64 overlap |
| **Embeddings** | `rag/embeddings.py` | `all-MiniLM-L6-v2` (local, free, 384-dim) |
| **Retrieval** | `rag/retriever.py` | Cosine similarity, per-user namespace |

> **Note:** Embeddings run locally using sentence-transformers. No API key needed. First run downloads the model (~80MB).

---

## 🔒 Security Features

| Feature | File | Description |
|---------|------|-------------|
| JWT Auth | `security/jwt_handler.py` | Access + refresh tokens |
| Password Hashing | `security/password.py` | bcrypt |
| Rate Limiting | `security/rate_limiter.py` | Sliding window per user |
| Prompt Injection Filter | `security/prompt_filter.py` | Blocks common injection patterns |
| Loop Detection | `security/loop_detector.py` | Catches infinite agent loops |
| Audit Logs | `security/audit.py` | All security events → MongoDB |
| Prompt Versioning | `security/prompt_versioning.py` | Version control for agent prompts |
| Sandbox Code Execution | `tools/python_sandbox.py` | Forbidden pattern blocking |

---

## 💰 Cost Control

- **Per-task budget** — configurable max USD per task (default $5)
- **Per-agent budget** — each agent has its own spending limit
- **Step limits** — max 50 steps per task
- **Auto-abort** — exceeding budget raises `BudgetExceededError`
- **Real-time tracking** — every LLM call logged with token counts + cost
- **Groq pricing** — much cheaper than OpenAI (~$0.59/M input tokens for 70B model)

---

## 🎨 Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Landing | `/` | Hero, features, pricing |
| Login | `/login` | Email + password sign in |
| Register | `/register` | Create account |
| Dashboard | `/dashboard` | Stats + task list |
| New Task | `/dashboard/new` | 3-step wizard |
| Task Detail | `/dashboard/tasks/[id]` | Live agent timeline + WebSocket |
| Cost Dashboard | `/dashboard/costs` | Spending breakdown |
| Settings | `/dashboard/settings` | Profile + preferences |

---

## 🧪 Running Tests

```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Sign in, get tokens |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/tasks` | Create research task |
| GET | `/tasks/{id}` | Get task details |
| GET | `/tasks/{id}/steps` | Get task steps |
| GET | `/tasks/{id}/result` | Get final result |
| POST | `/files/upload` | Upload file for RAG |
| WS | `/tasks/{id}/stream` | Live execution stream |

---

## ⚠️ Production Checklist

- [ ] Set strong `JWT_SECRET_KEY` (32+ random characters)
- [ ] Set `GROQ_API_KEY` with your Groq key
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `ALLOWED_ORIGINS` for your frontend domain
- [ ] Set up MongoDB authentication
- [ ] Set up Redis password
- [ ] Configure backup strategy for MongoDB
- [ ] Set up monitoring (Prometheus/Grafana recommended)
- [ ] Review rate limits for your expected traffic
- [ ] Set appropriate `MAX_TASK_BUDGET_USD` for your tier

---

## 🔄 LLM Provider: Groq

This platform uses **Groq** instead of OpenAI for LLM inference.

**Why Groq?**
- ⚡ **10x faster inference** — Groq's LPU chips deliver blazing speed
- 💰 **Much cheaper** — ~$0.59/M tokens vs OpenAI's $2.50+/M
- 🦙 **Open models** — Llama 3.3, Mixtral, Gemma (no vendor lock-in)
- 🔗 **OpenAI-compatible API** — drop-in replacement

**Available Models:**
| Model | Context | Use Case |
|-------|---------|----------|
| `llama-3.3-70b-versatile` | 128K | Default, best quality |
| `llama-3.1-8b-instant` | 128K | Fast, cheap tasks |
| `mixtral-8x7b-32768` | 32K | Good balance |
| `gemma2-9b-it` | 8K | Lightweight tasks |

To change the model, set `GROQ_MODEL` in your `.env` file.
