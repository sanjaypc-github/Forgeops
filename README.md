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

## Install on a new machine

### 1. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.12.x (not 3.13) | `python --version` |
| [uv](https://docs.astral.sh/uv/) | any recent | `uv --version` |
| Node.js | 20+ | `node --version` |
| Git | any | `git --version` |

`uv` installs and pins Python itself, so Python 3.12 does not have to be on PATH beforehand.

### 2. Clone and install

```bash
git clone https://github.com/sanjaypc-github/Forgeops.git
cd Forgeops
cd backend && uv sync
cd ../frontend && npm install
```

### 3. Create `.env`

`.env` is **never committed** — it holds secrets. Generate a fresh one:

```bash
cd backend
uv run python -m forgeops.devtools.envfile   # writes ../.env with generated secrets
```

Then edit `.env` at the repository root:

| Setting | What to put |
|---|---|
| `DATABASE_URL` | Supabase → Connect → **Session pooler**, with `postgresql://` → `postgresql+asyncpg://` and the password URL-encoded (`@` → `%40`, `*` → `%2A`) |
| `OPENROUTER_API_KEY` | one key for every role, **or** the three per-role keys below |
| `OPENROUTER_API_KEY_SUPERVISOR` / `_SPECIALIST` / `_RCA` | optional; each falls back to `OPENROUTER_API_KEY`, so one role's rate limit cannot starve another |
| `FORGEOPS_MODEL_SUPERVISOR` / `_SPECIALIST` / `_RCA` | model per role; `:free` models work but cannot use prompt caching |
| `KNOWLEDGE_VAULT_ROOTS` | JSON list of folders a knowledge connection may point at — **absolute paths on this machine**, so they must be rewritten here |
| `FORGEOPS_ADMIN_EMAIL`, `FORGEOPS_ADMIN_PASSWORD` | the first sign-in |

### 4. Create the tables and run

```bash
cd backend
uv run alembic upgrade head
uv run python -m forgeops.devtools.serve      # API on http://localhost:8000
```

In a second terminal:

```bash
cd frontend
npm run dev                                   # http://localhost:5173
```

Sign in with `FORGEOPS_ADMIN_EMAIL` / `FORGEOPS_ADMIN_PASSWORD`.

### 5. Reconnect the connectors

Connector credentials live in the database, never in `.env`. On the Connectors page:

- **Knowledge vault** — the folder path on *this* machine; it must sit inside `KNOWLEDGE_VAULT_ROOTS`
- **GitHub** — a fine-grained token limited to the repository under investigation
- **Supabase** — the project ref and an access token
- **Cloudflare** — the account id, then **Connect**: Cloudflare's own window asks you to approve,
  read-only. It does not accept an API token

Verify what a connected server really offers:

```bash
cd backend && uv run python -m forgeops.devtools.mcp_tools
```

### Sharing one database between two machines

If the second machine points `DATABASE_URL` at the **same** Supabase project, one setting must be
copied rather than regenerated:

> **`FORGEOPS_SECRET_KEY` must be identical on both machines.**
> Connector tokens are Fernet-encrypted with it in `connections.secret_encrypted`. A machine with a
> different key cannot decrypt the connections the other one saved, and every connector will fail
> with a decryption error until it is reconnected.

Copy that one value by hand — never through Git, chat or email. If you would rather keep the
machines independent, point the second one at its own Supabase project and reconnect the connectors
there; nothing else is shared.

### Windows notes

- Always start the API with `forgeops.devtools.serve`. It installs the selector event loop that
  psycopg needs; `uvicorn` started directly will fail to reach the database.
- `npx` is resolved through `shutil.which`, so stdio connectors work without extra PATH setup.
- If `git push` reports `credential-manager-core is not a git command`, the credential helper name in
  your global Git config is stale — newer Git calls it `manager`.

### Troubleshooting

| Symptom | Cause |
|---|---|
| `tenant or user not found` | The Supabase project is paused, or the password is not URL-encoded |
| Connectors fail with a decryption error | `FORGEOPS_SECRET_KEY` differs from the one that saved them (see above) |
| `Connector … is not available` | The vault path is outside `KNOWLEDGE_VAULT_ROOTS` |
| Investigation stops with `RateLimitError` | OpenRouter free tier: 50 requests/day per account. Use per-role keys or add credit |
| Connected, but "the server offers none of the tools" | The pinned tool names do not match the live server — run `devtools.mcp_tools` |

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
