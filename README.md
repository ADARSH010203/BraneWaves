# BrainWeave (ARC Platform)
**Agentic Research & Work Copilot**

BrainWeave is an advanced, fully autonomous **Agentic AI platform** designed to handle complex, multi-step research and analysis tasks. Built on a modern tech stack (FastAPI, Next.js 15, MongoDB, Redis), it orchestrates multiple specialized AI agents to plan, research, write code, analyze data, and verify citations—all in real-time.

---

## 🌟 Core Architecture & Technology Stack

**Backend:**
- **Framework:** FastAPI (Python)
- **Database:** MongoDB (Motor Async) for documents, tasks, and users
- **Cache & Pub/Sub:** Redis for rate limiting, background queues, and real-time WebSocket streaming
- **AI/LLM:** Groq API (`llama-3.3-70b-versatile`)
- **Embedding/RAG:** Local Sentence-Transformers (`all-MiniLM-L6-v2`) with ultra-fast FAISS vector similarity search

**Frontend:**
- **Framework:** Next.js 15 (App Router, React 19)
- **Styling:** TailwindCSS, Framer Motion for sophisticated animations
- **Components:** Glassmorphism UI, real-time WebSockets, Recharts for data visualization

---

## 🤖 The 7-Agent Orchestration System

At the heart of BrainWeave is the **Task Orchestrator**, a Directed Acyclic Graph (DAG) manager that dispatches work to 7 specialized agents:

1. **Planner Agent:** Breaks down complex user requests into a graph of dependent steps.
2. **Research Agent:** Uses web scraping and search tools to gather external knowledge.
3. **Data Agent:** Queries the RAG FAISS index to find relevant context from uploaded user documents.
4. **Code Agent:** Writes Python code for data analysis, math, or scraping.
5. **Critic Agent:** Reviews the outputs of other agents to ensure accuracy and logical consistency.
6. **Report Agent:** Synthesizes all gathered data into a final, beautifully formatted Markdown report.
7. **Repair Agent:** Automatically attempts to fix failed steps or code errors based on Critic feedback.

---

## 🛠️ Security & Advanced Features

- **Sandboxed Python Execution:** The Code agent runs user-generated Python scripts inside an isolated subprocess with strict regex pattern filtering to prevent malicious code execution (e.g., blocks `import os`, `eval()`).
- **Real-Time Streaming:** The frontend connects via JWT-authenticated WebSockets to stream the exact thoughts, actions, and status of every agent live.
- **Budget Control:** Granular cost tracking. Every LLM token is counted. Tasks are automatically aborted if they exceed their predefined budget (e.g., $1.50 limit).
- **Prompt Injection Defense:** Regex filters drop prompts containing "ignore previous instructions" or manipulating the system boundary.
- **Infinite Loop Detection:** The orchestrator tracks identical outputs and identical tool calls to prevent agents from getting stuck in cyclical loops.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB instance (running on port 27017)
- Redis instance (running on port 6379)
- Groq API Key

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env   # Add your GROQ_API_KEY
uvicorn app.main:app --reload --port 8000
```

### Worker Setup (Run in a new terminal)
```bash
cd backend
source venv/bin/activate
python -m app.workers.task_worker
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` to start using the platform!
