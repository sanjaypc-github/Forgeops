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

Requirements: [uv](https://docs.astral.sh/uv/), Node.js 20+, and a Supabase project for ForgeOps' own data. Docker is optional.

1. Create the config file:

   ```bash
   cd backend
   uv sync
   uv run python -m forgeops.devtools.envfile   # creates ../.env with generated secrets
   ```

2. In `.env`, set `DATABASE_URL` to your Supabase project's **Session pooler** connection string
   (Supabase → Connect → Session pooler), with `postgresql://` changed to `postgresql+asyncpg://`
   and special characters in the password URL-encoded (`@` → `%40`, `*` → `%2A`).
   ForgeOps keeps its tables in the private `forgeops` schema, not in Supabase's public API schema.

3. Create the tables and start the API:

   ```bash
   cd backend
   uv run alembic upgrade head
   uv run python -m forgeops.devtools.serve      # API on http://localhost:8000
   ```

4. Start the web app (new terminal):

   ```bash
   cd frontend
   npm install
   npm run dev                                  # http://localhost:5173
   ```

Sign in with `FORGEOPS_ADMIN_EMAIL` and `FORGEOPS_ADMIN_PASSWORD` from `.env`.

## Run an investigation

Add your OpenRouter key to `.env` (`OPENROUTER_API_KEY=...`), then run one live investigation against the starter runbooks in `knowledge-vault/`:

```bash
cd backend
uv run python -m forgeops.devtools.smoke "Checkout requests are timing out and users see errors"
```

It prints every agent event as it happens (plan, tool calls, questions between desks, evidence), then the root cause, confidence and recommendations. The agents' rules are described in [docs/HARNESS.md](docs/HARNESS.md).

Tests:

```bash
cd backend && uv run pytest     # uses the same database, isolated in the forgeops_test schema
cd frontend && npm test
```

Optional local database instead of Supabase: leave `DATABASE_URL` empty when running the env generator, then `docker compose --profile local-db up -d postgres`.
