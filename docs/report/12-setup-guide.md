# 12 — Setup and operation guide

Feeds the report's **Appendix (System Requirements / Installation)** and lets anyone reproduce the
system from a clean clone.

---

## 12.1 System requirements

### Software

| Component | Version | Purpose |
|---|---|---|
| Python | 3.12 | Backend runtime |
| uv | latest | Python environment and dependency manager |
| Node.js | 20 or newer | Frontend build; also used by `npx` for stdio MCP servers |
| PostgreSQL | 15+ (Supabase managed, or local) | Application data and LangGraph checkpoints |
| Git | any recent | Version control |

Operating system: developed on Windows 11; the code runs on Linux and macOS. Two Windows-specific
accommodations are built in — the selector event loop required by `psycopg`, and resolving `npx` to
`npx.cmd` through `shutil.which`.

### Hardware (development)

| Resource | Minimum | Comfortable |
|---|---|---|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Disk | 5 GB | 10 GB (embeddings and the Chroma index grow with the vault) |
| Network | Required — the model provider and the connected tools are remote | |

No GPU is required: the system calls a hosted model through an API and runs only small embedding
models locally.

### External accounts

| Account | Needed for |
|---|---|
| OpenRouter (or any OpenAI-compatible endpoint) | The language model. Optional during development — see offline mode |
| Supabase | Managed PostgreSQL for the application itself |
| GitHub | The GitHub connector, using a fine-grained personal access token |
| Any further tools | Their own tokens or OAuth consent, entered on the Connectors page |

## 12.2 Installation

```bash
git clone https://github.com/sanjaypc-github/Forgeops.git
cd Forgeops

# backend
cd backend
uv sync                      # creates .venv and installs dependencies
uv run alembic upgrade head  # applies the database migrations
cd ..

# frontend
cd frontend
npm install
cd ..
```

## 12.3 Configuration

Create `.env` in the repository root. **Never commit it.**

```ini
# ── core ────────────────────────────────────────────────────────────────
FORGEOPS_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:5432/postgres
FORGEOPS_SECRET_KEY=<32+ random characters; encrypts connector secrets>
FORGEOPS_ADMIN_EMAIL=you@example.com
FORGEOPS_ADMIN_PASSWORD=<first sign-in password>
FORGEOPS_WORKSPACE_NAME=My workspace

# ── model provider ──────────────────────────────────────────────────────
FORGEOPS_LLM=openrouter          # or "offline" to build without a key
OPENROUTER_API_KEY=<key>
FORGEOPS_MODEL_SUPERVISOR=<model id>
FORGEOPS_MODEL_SPECIALIST=<model id>
FORGEOPS_MODEL_RCA=<model id>
FORGEOPS_PROMPT_CACHE=false      # true on paid models that cache the prompt prefix

# ── budgets (raise for slower models) ───────────────────────────────────
FORGEOPS_SPECIALIST_SECONDS=300
FORGEOPS_ANSWER_SECONDS=90
FORGEOPS_RUN_SECONDS=1800

# ── context discipline ──────────────────────────────────────────────────
FORGEOPS_TOOL_OUTPUT_CHARS=8000
FORGEOPS_KEEP_FULL_TOOL_OUTPUTS=3

# ── knowledge layer ─────────────────────────────────────────────────────
KNOWLEDGE_DATA_DIR=./.knowledge
KNOWLEDGE_VAULT_ROOTS=../knowledge-vault
```

**Two configuration rules worth stating in the report:**

1. The database password must be **URL-encoded** in `DATABASE_URL` (for example `@` → `%40`,
   `*` → `%2A`), otherwise the connection string parses incorrectly.
2. `KNOWLEDGE_VAULT_ROOTS` bounds which folders a knowledge connection may point at. Without it, an
   operator could point a connection at any path on the server; the restriction was added after an
   internal security review.

**Connector tokens are never placed in `.env`.** They are entered on the Connectors page and stored
encrypted in the database.

## 12.4 Running the system

```bash
# backend API — use this launcher on Windows (selector event loop for psycopg)
cd backend && uv run python -m forgeops.devtools.serve      # http://localhost:8000

# frontend
cd frontend && npm run dev                                   # http://localhost:5173
```

Sign in with `FORGEOPS_ADMIN_EMAIL` and `FORGEOPS_ADMIN_PASSWORD`; the admin user and workspace are
created on first start.

## 12.5 Connecting tools

| Connector | What to prepare |
|---|---|
| **Knowledge vault** | A folder of Markdown notes inside one of `KNOWLEDGE_VAULT_ROOTS` |
| **GitHub** | A fine-grained personal access token limited to one repository, read-only on Contents, Metadata, Pull requests, Actions and Issues. Add Issues write **only** if you want approved issue creation |
| **Supabase** | A personal access token and the project reference. ForgeOps starts the official Supabase MCP server with `--read-only` and `--project-ref`, so SQL cannot modify data |
| **OAuth connectors** | Click Connect and approve in the provider's own window; ForgeOps never sees the password |

Each connection is health-checked immediately and reports how many allow-listed tools the server
actually offers.

## 12.6 Running an investigation

- **From the interface:** type the problem into the chat bar in the War Room.
- **From the command line:**
  ```bash
  cd backend && uv run python -m forgeops.devtools.smoke "checkout is slow since the morning deploy"
  ```
  This prints the live event stream and the final root cause — the quickest demonstration for a viva.

## 12.7 Building without a model key

```ini
FORGEOPS_LLM=offline
```

The real graph runs against the real connectors, but no analysis is performed. Every output is
labelled, confidence is zero, no actions are proposed, and the mode refuses to start when
`FORGEOPS_ENV=production`. Use it to demonstrate the interface and the connector plumbing; never use
it to judge answer quality.

## 12.8 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `tenant/user … not found` | The Supabase project is paused or removed | Restore or recreate it; update `DATABASE_URL`; run `alembic upgrade head` |
| Connection attempts time out on port 5432 | The network blocks outbound PostgreSQL (common on campus and office Wi-Fi) | Use a mobile hotspot or a VPN |
| `NotImplementedError` from psycopg on Windows | Wrong event loop | Start the API with `forgeops.devtools.serve` |
| A Supabase connector fails to start | `npx` not found, or Node missing | Install Node.js; the first run downloads the MCP server |
| "OpenRouter returned no answer" | A busy free-tier provider | The client retries three times; otherwise switch model |
| A desk reports "no connector" | No tool is connected for that area | Connect one, or accept it — the gap is reported honestly in the result |
