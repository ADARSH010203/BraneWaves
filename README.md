<div align="center">
  <img src="https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/sparkles.svg" width="80" height="80" alt="BrainWeave Logo" />
  <h1 align="center">BrainWeave ARC Platform</h1>
  <p align="center">
    <strong>Agentic Research & Work Copilot</strong>
  </p>
  <p align="center">
    A multi-agent AI research platform powered by Groq GPT-OSS models, FastAPI, and Next.js 15. Formulate complex queries and let a pipeline of specialized agents plan, research, analyze, code, critique, repair, and report.
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.11-blue.svg?logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-0.104+-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Next.js-15-black.svg?logo=next.js&logoColor=white" alt="Next.js" />
    <img src="https://img.shields.io/badge/MongoDB-Motor_Async-47A248.svg?logo=mongodb&logoColor=white" alt="MongoDB" />
    <img src="https://img.shields.io/badge/Redis-Caching_&_PubSub-DC382D.svg?logo=redis&logoColor=white" alt="Redis" />
    <img src="https://img.shields.io/badge/LLM-Groq_LPU-orange.svg" alt="Groq" />
  </p>
</div>

---

## 🚀 Features

- **7-Agent Pipeline:** Planner, Research, Data, Code, Critic, Repair, and Report agents orchestrated via a DAG (Directed Acyclic Graph) executor.
- **Real-Time Telemetry:** Live WebSocket streaming directly to the frontend, visualised through a beautiful physics-based Framer Motion timeline.
- **Persistent Knowledge Base (RAG):** Upload PDF, Markdown, CSV, TXT, JSON, and DOCX context documents. Embeddings are stored in MongoDB and searched with an in-process FAISS index. Large deployments should use a persistent vector service.
- **Cost Analytics Dashboard:** Aggregate lifetime task costs, token usage, per-agent spend, daily trends, and recent task costs.
- **Robust Authentication:** Traditional Email/Password + OAuth2 (Google & GitHub) backed by secure JWT sessions.
- **Export & Delivery:** Automatically generate polished outputs downloadable as rich Markdown, PDF, or DOCX formats.

---

## 🏗 System Architecture

The BrainWeave ARC platform is organized into two main application directories:

1. **/backend** (FastAPI / Python)
   - Serves the robust REST API and WebSocket events.
   - Manages connections to MongoDB (via Motor) and Redis.
   - Executes the core DAG agent orchestrator.
   - Enforces rate limiting, JWT validation, tool permissions, and forwards code execution only to a separately isolated sandbox service.

2. **/frontend** (Next.js 15 / React / TailwindCSS)
   - Delivers a premium, dark-mode biased, glassmorphic UI.
   - Manages global state, animated agent timelines, data visualizations via Recharts, and dynamic knowledge base dropzones.

---

## ⚙️ Prerequisites

Ensure you have the following installed on your system before proceeding:

- **Node.js** (v18+ recommended)
- **Python** (v3.11+ strictly recommended)
- **MongoDB** (Running locally on default port `27017` or via Docker)
- **Redis** (Running locally on default port `6379` or via Docker)

> **Pro-tip:** You can easily spin up MongoDB and Redis using Docker:
> ```bash
> docker run -d -p 27017:27017 --name arc-mongo mongo:latest
> docker run -d -p 6379:6379 --name arc-redis redis:latest
> ```

---

## 🛠️ Step 1: Backend Setup

Navigate to the `backend` directory and set up your Python environment:

```bash
cd backend

# Create and activate a Virtual Environment
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
# (Also ensure you have installed authlib and httpx from recent upgrades: pip install authlib httpx)
```

### Environment Variables (.env)
Copy the repository-root `.env.example` to `.env` and fill in the required values:

```ini
# Application
APP_NAME="ARC — Agentic Research & Work Copilot"
ENVIRONMENT="development"
DEBUG=True

# Database & Caching
MONGO_URI="mongodb://localhost:27017"
REDIS_URL="redis://localhost:6379/0"

# Authentication
# Required in every environment; generate a random secret of at least 32 characters
JWT_SECRET_KEY="your-secure-32-byte-secret-key-here" 

# AI APIs
GROQ_API_KEY="your-groq-api-key"

# OAuth2 (Optional but required for Social Login)
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
GITHUB_CLIENT_ID="your-github-client-id"
GITHUB_CLIENT_SECRET="your-github-client-secret"
```

### Run the Backend Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The FastAPI backend will now be running at `http://localhost:8000`. 
*You can view the interactive API documentation at `http://localhost:8000/docs`.*

---

## 🖥️ Step 2: Frontend Setup

Open a new terminal window, navigate to the `frontend` directory, and install the required modules:

```bash
cd frontend

# Install dependencies
npm install
```

### Environment Variables (.env.local)
Create a `.env.local` file in the `frontend/` directory.

```ini
NEXT_PUBLIC_API_URL="http://localhost:8000"
```

### Run the Frontend Development Server
```bash
npm run dev
```
The Next.js frontend will now be running at `http://localhost:3000`.

---

## 🐋 Run with Docker

`docker-compose.yml` is the **development stack**. It includes the API, worker, frontend, MongoDB, and Redis. MongoDB and Redis are not published to host ports.

Make sure [Docker Desktop](https://www.docker.com/products/docker-desktop/) is installed and running. Create your root `.env` file as described in Step 1, then simply run:

```bash
# Development stack
docker compose up --build -d

# Production-oriented stack (set NEXT_PUBLIC_API_URL / NEXT_PUBLIC_WS_URL first)
docker compose -f docker-compose.prod.yml up --build -d
```

- Frontend accessible at: `http://localhost:3000`
- Backend accessible at: `http://localhost:8000`

To stop the cluster:
```bash
docker-compose down
```

---

## 🎯 Usage Walkthrough

1. **Authentication:** Open `http://localhost:3000` in your browser. Create an account via Email/Password or use the configured Google/GitHub OAuth links.
2. **Knowledge Base:** Navigate to the "Knowledge Base" in the sidebar. Drag and drop any relevant `.pdf`, `.txt`, `.csv`, or `.md` reference files. The backend will automatically map vector embeddings to your workspace.
3. **Launch a Task:** Go to the "New Task" screen. You can select an industry-standard template (e.g., Code Review, Market Analysis) or write your own research objective.
4. **Watch it Execute:** Sit back and watch the DAG visualizer. The system will dynamically display the Planner spinning up, parallel streams from the Code/Research/Data agents executing, and the final Critic/Repair checks looping over any errors.
5. **Analyze Costs:** Visit the "Cost Dashboard" to review charts displaying your exact Groq Token consumption, cache hit savings, and budget distribution.

---

## 🛡 Security & Safety Guardrails
- **Prompt Injection Telemetry:** Heuristic detection flags suspicious instructions; it is not treated as a security boundary.
- **Tool Authorization:** Agents can execute only explicitly allowed tools, with permission-scope checks.
- **Budget Enforcement:** Per-task budgets and account usage quotas are enforced from recorded LLM usage.
- **Python Isolation:** The API never runs untrusted Python locally. Configure `PYTHON_SANDBOX_URL` to a separately isolated service with CPU, memory, filesystem, network, and process limits.
- **Refresh Sessions:** Refresh tokens are stored as hashes in MongoDB and sent to browsers only in HttpOnly cookies.

---

## 📝 License
This project was developed as a Final Year Academic Platform upgraded for industry-grade operations. All rights reserved.
