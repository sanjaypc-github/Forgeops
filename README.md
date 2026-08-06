# EOPS (Engineering Operations Platform) MVP v1.0

EOPS is an AI-driven Engineering Operations Platform designed to automate incident triage, troubleshoot system failures, and perform root-cause analysis (RCA). Think of EOPS not just as an incident investigation assistant, but as an **AI Operating System for Engineering Teams**—modular, extensible, and built to orchestrate specialized agents running in parallel to solve complex operational issues.

---

## 🏗️ System Architecture

```
                          USER
                            │
                            ▼
               React Dashboard (Frontend)
                            │
                            ▼
                    FastAPI Backend (API)
                            │
                            ▼
              LangGraph Supervisor / Planner Agent
                            │
      ┌─────────────────────┼─────────────────────┐
      │                     │                     │
      ▼                     ▼                     ▼
 GitHub Agent          Logs Agent         Knowledge Agent
      │                     │                     │
      ▼                     ▼                     ▼
 GitHub Tool         Log Parser Tool      Knowledge Tool
      │                     │                     │
 GitHub API          Local Log Files      ChromaDB
                                                ▲
                                                │
                                     Embedding Model
                                                ▲
                                                │
                                      Chunking Pipeline
                                                ▲
                                                │
                                    Obsidian Vault (.md)

═══════════════════════════════════════════════════════════════
              Shared Investigation State (LangGraph)
═══════════════════════════════════════════════════════════════
                            │
                            ▼
                  Root Cause Analysis Agent
                            │
                            ▼
                  Human Approval Interface
                            │
                            ▼
               Investigation Report Generator
                            │
                            ▼
                    Dashboard + Markdown Report
```

---

## 📂 Repository Structure

The codebase is organized as follows:

```text
eops-mvp/
├── backend/                  # FastAPI Application Server
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI Entry Point (Endpoints: /investigate, /status, etc.)
│   │   ├── config.py         # System configuration & environment loading
│   │   └── routes.py         # Route handlers
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # React UI Dashboard (Vite-based)
│   ├── src/                  # Components, Hooks, and Pages
│   ├── package.json
│   └── vite.config.js
│
├── agents/                   # LangGraph AI Agents
│   ├── __init__.py
│   ├── supervisor/           # Coordinator Agent (Decides & routes sub-agents)
│   ├── github/               # Source code change analyst
│   ├── logs/                 # Log file parser and anomaly finder
│   ├── knowledge/            # RAG Agent for runbooks and documentation
│   └── rootcause/            # Synthesizer Agent (RCA & remediation steps)
│
├── tools/                    # Reusable Agent Tools (API Integrations & local tools)
│   ├── __init__.py
│   ├── github/               # Github REST API connector
│   ├── logs/                 # Local log parsing utilities
│   └── rag/                  # ChromaDB vector store querying tool
│
├── memory/                   # LangGraph State Definitions
│   ├── __init__.py
│   └── state.py              # Shared Investigation State schema
│
├── langgraph/                # Workflow Engine
│   ├── __init__.py
│   └── graph.py              # Graph definition, compilation, and supervisor logic
│
├── knowledge/                # Ingestion Pipeline & Raw Docs
│   ├── obsidian_vault/       # Source Markdown documents (Services, Runbooks, etc.)
│   └── ingestion/            # Offline indexing, chunking, and embedding pipelines
│
├── vector_db/                # Local ChromaDB persistent storage (Git ignored)
├── reports/                  # Generated Investigation Reports (Markdown + JSON)
├── datasets/                 # Mock logs and incident logs for local testing
├── docs/                     # Architecture designs, manuals, and schemas
├── tests/                    # Unit and integration tests
└── .gitignore                # File exclusions (env, DB, build outputs)
```

---

## 📊 Core System Components

### 1. React Dashboard (Frontend)
- **Role:** Human-in-the-loop (HITL) interface.
- **Features:** Incident input panel, real-time agent execution timeline (LangGraph execution visualization), evidence board (commits, log snippets, runbook pages), Root Cause Analysis preview, and human interactive approval button (Approve / Reject / Request Investigation).

### 2. FastAPI Backend
- **Role:** Web server and API gateway.
- **Endpoints:**
  - `POST /api/investigate` - Starts a new LangGraph investigation.
  - `GET /api/status/{investigation_id}` - Polls the current execution state.
  - `POST /api/approve/{investigation_id}` - Submits human approval to proceed with report generation.
  - `GET /api/reports/{investigation_id}` - Fetches the finalized markdown/JSON investigation report.

### 3. LangGraph Supervisor
- **Role:** The Orchestration Brain. Actively decodes the incident details, schedules specialized agents to execute in parallel, and coordinates their results.

### 4. Agent Framework
- **GitHub Agent:** Performs source control delta analysis using the **GitHub Tool** (connects to GitHub API). Writes recent commit messages, authors, and affected files to the shared state.
- **Logs Agent:** Analyzes system logs using the **Log Parser Tool** to identify service exceptions, HTTP 5xx codes, Redis timeouts, or performance bottlenecks.
- **Knowledge Agent:** Acts as the RAG client, using the **Knowledge Tool** to search vector-indexed documentation.
- **Root Cause Agent:** Does not call tools. Evaluates the merged `Shared State` to formulate hypotheses, assign confidence scores, and propose corrective actions.

### 5. Knowledge Layer & Indexer
- **Obsidian Vault:** A local directory containing Markdown files representing Runbooks, Service docs, Incident histories, API specs, and Troubleshooting guides.
- **Offline Indexer:** A Python ingestion script that parses, chunks, embeds (using LangChain/OpenAI/Ollama embeddings), and upserts text segments into **ChromaDB**.

---

## 🔄 Data & Execution Flow

1. **Incident Trigger:** An engineer inputs an incident description (e.g., *"Checkout API latency increased significantly after deployment"*).
2. **Supervisor Planning:** The Supervisor agent runs, parses the input, and spins up `GitHub Agent`, `Logs Agent`, and `Knowledge Agent` concurrently.
3. **Execution & State Merge:** Each agent executes its respective tools and writes findings directly to the `Shared State` (no agent talks directly to another).
4. **Root Cause Analysis:** Once sub-agents complete, the `Root Cause Agent` reads the consolidated `Shared State`, synthesizes the clues, and drafts the RCA.
5. **Human Approval:** Execution pauses at a state node awaiting human interaction (Approval/Rejection) via the React dashboard.
6. **Report Generation:** Upon approval, the final markdown report is generated, saved to `reports/`, and displayed on the dashboard.
