# ForgeOps (EOPS — Engineering Operations Platform)

ForgeOps finds the root cause of a production problem in minutes instead of hours. A SaaS team connects the tools its product runs on (GitHub, Cloudflare, Vercel, Supabase, Sentry, Sanity, AWS, …) from a **connector catalog**, where every connector is an MCP server. When something breaks, they paste the symptom into the **chat bar**: a **Supervisor** agent splits the work across **specialist agents** that investigate their own tools **in parallel** and **ask each other questions**, and an **RCA** step returns the root cause, the exact point of failure and the evidence. A human approves any action before it happens.

Everything is shown live in the **War Room**: a 2D office where each agent works at its own desk and walks to other desks when they talk, driven only by real backend events.

> **Status:** MVP in development. See the milestones in [docs/TRD.md](docs/TRD.md#17-milestones).

## How it works

```text
Chat bar: "site is very slow, sometimes shows a warning"
        │
        ▼
   Supervisor ── plans, picks the desks whose connectors are relevant
        │
   ┌────────┬───────────────┬──────────────┬──────────┬───────────────┬───────────┐   (parallel,
   ▼        ▼               ▼              ▼          ▼               ▼               asking each
  Code   Frontend &      Backend &      Database  Observability   Knowledge         other questions)
         Hosting         Services
 GitHub  Cloudflare,     Supabase,      Supabase, Sentry,         Obsidian /
 GitLab  Vercel,Netlify  Sanity, AWS    Postgres  Datadog         Markdown vault
   └────────┴───────────────┴──────────────┴──────────┴───────────────┘
                   │  structured evidence → shared state
                   ▼
                  RCA ── root cause, exact failure point, evidence, confidence
                   │
                   ▼
            Human approval (chat)
                   │
                   ▼
          Action ── GitHub issue + report
```

Principles:
- **Real data only.** No mock data at runtime; every finding links to the real tool call behind it.
- **Works with any subset of tools.** Missing connectors are reported as missing information, never invented.
- **Read-only by default.** Write tools exist only after a recorded human approval.
- **Fixed agents by system area + pluggable connectors.** New platforms are added as connectors, not new agents.

## Stack

| Part | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, LangGraph, Pydantic, SQLAlchemy |
| Database | Supabase Postgres (ForgeOps' own data) |
| LLM | OpenRouter (model configurable per agent role) |
| Connectors | Official MCP servers (GitHub, Cloudflare, Supabase, Sanity, Sentry) |
| Knowledge | Markdown/Obsidian vault, ChromaDB, BM25 hybrid retrieval |
| Frontend | React, TypeScript, Vite; SVG/CSS War Room |

## Repository layout

```text
Forgeops/
├── backend/          FastAPI app, LangGraph engine, agents, connectors, knowledge
├── frontend/         React War Room
├── knowledge-vault/  Starter runbooks and service docs
└── docs/             PRD, TRD, plans, original spec and diagrams
```

## Documents

- [Product requirements (PRD)](docs/PRD.md)
- [Technical requirements (TRD)](docs/TRD.md) — architecture, flow diagrams, contracts, milestones
- [Original project spec](docs/reference/PROJECT_SPEC.md) and [architecture diagrams](docs/reference/ARCHITECTURE_DIAGRAMS.md)

## Local setup

Requirements: Docker Desktop, [uv](https://docs.astral.sh/uv/), Node.js 20+.

```bash
cd backend
uv sync
uv run python -m forgeops.devtools.envfile   # creates ../.env with generated secrets
cd ..
docker compose up -d --build                 # Postgres + API on http://localhost:8000
cd frontend
npm install
npm run dev                                  # web app on http://localhost:5173
```

Sign in with `FORGEOPS_ADMIN_EMAIL` and `FORGEOPS_ADMIN_PASSWORD` from `.env`.

Tests:

```bash
cd backend && uv run pytest     # needs the Postgres container running
cd frontend && npm test
```
