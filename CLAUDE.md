# ForgeOps — guide for AI agents and new engineers

> This file is a copy of `AGENTS.md`, kept so Claude Code loads it automatically. Edit `AGENTS.md`;
> copy it here in the same commit.
Read this before changing anything. It says what ForgeOps is, where each piece lives, the rules the
code follows, and how to run and verify it. `CLAUDE.md` is a symlink-free copy pointer: this file is
the single source.

## 1. What the product is

ForgeOps finds the **root cause of a production problem in 10–20 minutes** and shows the exact failure
point with evidence. A customer connects their own tools (GitHub, Supabase, Cloudflare, …), pastes a
symptom into a chat bar, and watches a 2D office where one agent per system area investigates in
parallel, asks colleagues questions, and pins findings to an evidence wall. Every write needs human
approval.

It is a SaaS product for software teams, not a script for one company. The owner's own website
(Cloudflare + GitHub + Supabase + Sanity) is only the first test target.

## 2. Non-negotiable rules

These are product promises. Breaking one is a bug, even if tests pass.

| Rule | What it means in code |
|---|---|
| **No mock data at runtime** | Fakes live in `backend/tests/` only. The one exception is `FORGEOPS_LLM=offline` (§7), which labels every answer and refuses to run in production. |
| **Evidence or silence** | A finding must cite `tool_call_ids` of successful calls. `SpecialistLoop._accept` rejects uncited findings; the RCA rejects unknown `ev_` ids. |
| **Reads by default** | Investigating desks get read tools only (`CapabilityRegistry.tools_for`). Write tools exist only on a connection that opted in, and only the Action desk can call them, after approval. |
| **Human approval for writes** | The graph interrupts at `approval`; `action_node` runs only for recommendation ids the human approved. |
| **Allowlist only** | A connector exposes only tools named in its `ConnectorDefinition.tools`. A tool the server does not offer is reported by the health check, never faked. |
| **Secrets stay server-side** | Tokens are Fernet-encrypted in `connections.secret_encrypted` and never returned by the API. Do not log them. |
| **Tool output is data** | It is wrapped in `<tool_output>` and never treated as instructions. |
| **Say what you could not check** | Missing connectors and failed desks appear in the RCA's `missing_information` and in the report. |

## 3. Repository map

```
backend/forgeops/
  api/            FastAPI routers: auth, investigations, chat, connections, oauth_flow, agents, health
  engine/         the investigation itself
    graph.py      LangGraph: plan → specialists (parallel) → review → rca → approval → action → report
    specialist.py one desk working a task: think, call tools, ask colleagues, submit cited findings
    supervisor.py planning and review;  rca.py  root cause;  questions.py  desk-to-desk questions
    budgets.py    every limit in one place;  state.py  LangGraph state;  models.py  contracts
    report.py     deterministic Markdown report (no model involved)
    runner.py     runs investigations in the background, stores status and usage
    llm/          base.py (types), openrouter.py (real), offline.py (stand-in), metering.py, structured.py
    prompt_templates/*.md   the prompts; `common.md` is shared by every role
  capabilities/   registry.py (who may use which tool), runner.py (policy, retry, truncation, events)
  connectors/     definitions.py (the catalog), mcp.py (MCP client), knowledge.py, oauth.py, tokens.py
  events/         persisted event bus + SSE replay
  db/             SQLAlchemy models and session;  alembic/  migrations
  devtools/       serve.py (run the API on Windows), smoke.py (one investigation from the CLI)
frontend/src/
  war-room/       the office: layout, floor, sprites, reducer (officeState.ts), chat, side panels
  pages/          WarRoomPage, ConnectorsPage, InvestigationsPage, ReportPage, LoginPage
  api/            typed fetch wrappers;  investigations/eventStream.ts  SSE with Last-Event-ID replay
docs/             PRD.md (product), TRD.md (technical), HARNESS.md (how agents are made good)
```

## 4. How an investigation flows

1. `POST /api/chat` or `/api/investigations` creates the row and emits `investigation_started`.
2. `InvestigationRunner._run` builds the LLM (metered), the capability registry for that workspace,
   and the graph, then runs it under the run time budget.
3. **Supervisor** plans: it may only assign desks that have connected tools.
4. **Specialists** run in parallel (LangGraph `Send`). Each calls its own read tools, may call
   `ask_agent` to ask another desk one question, and finishes with `submit_findings`.
5. **Supervisor review** decides whether the evidence is enough, once.
6. **RCA** writes the root cause from evidence lines only; code caps its confidence.
7. **Approval** interrupts the graph. The human approves, rejects, or asks for more work.
8. **Action** runs approved writes (today: create a GitHub issue). **Report** renders Markdown.

Every step emits events; the War Room is a pure reducer over those events, so a refresh replays the
same state.

## 5. Where the harness quality lives

`docs/HARNESS.md` is the contract: role prompts, honesty rules, tool-use method, budgets, output
contracts, the confidence rubric, context discipline and observability. Change prompts there and in
`engine/prompt_templates/` together.

Two things to respect when editing prompts:

- **System prompts must be identical across a desk's turns**, so providers can cache the prefix.
  Anything per-call (the clock, the task) belongs in the first user message (`prompts.now_line`).
- **Older tool output is compacted** (`SpecialistLoop._view`): the newest 3 results stay whole, older
  ones collapse to their opening but keep their `call_id`, so findings can still cite them.

## 6. Setup

```bash
# backend (Python 3.12 via uv)
cd backend && uv sync
uv run alembic upgrade head
uv run python -m forgeops.devtools.serve      # http://localhost:8000

# frontend
cd frontend && npm install && npm run dev     # http://localhost:5173
```

`.env` at the repo root. The important settings:

| Setting | Meaning |
|---|---|
| `DATABASE_URL` | Supabase Postgres, `postgresql+asyncpg://…`; password must be URL-encoded |
| `FORGEOPS_SECRET_KEY`, `FORGEOPS_ADMIN_EMAIL`, `FORGEOPS_ADMIN_PASSWORD` | first sign-in |
| `FORGEOPS_LLM` | `openrouter` (default) or `offline` (§7) |
| `OPENROUTER_API_KEY`, `FORGEOPS_MODEL_*` | the real provider and per-role models |
| `FORGEOPS_SPECIALIST_SECONDS`, `FORGEOPS_ANSWER_SECONDS`, `FORGEOPS_RUN_SECONDS` | time budgets |
| `FORGEOPS_TOOL_OUTPUT_CHARS`, `FORGEOPS_KEEP_FULL_TOOL_OUTPUTS` | context discipline |
| `FORGEOPS_PROMPT_CACHE` | mark the stable prefix for caching (paid models) |
| `KNOWLEDGE_VAULT_ROOTS` | folders a knowledge connection may point at |

Connector tokens are entered on the Connectors page, never in `.env`.

Windows notes: psycopg needs the selector event loop — always start the API with
`forgeops.devtools.serve`, and tests set it through a fixture. `npx` is resolved via `shutil.which`.

## 7. Working without a model key (`FORGEOPS_LLM=offline`)

`engine/llm/offline.py` is a **stand-in, not a model**. It drives the real graph against the real
connectors — desks call their actual tools and real tool output becomes the evidence — but it does no
analysis. Therefore:

- every plan, finding and RCA it produces starts with `OFFLINE MODE (no language model connected)`,
- findings carry confidence `0.0`, the RCA proposes no actions,
- the run's warnings and the top of the report say so,
- `OfflineLLM.from_settings` raises when `FORGEOPS_ENV=production`.

Use it to build and demonstrate UI, connectors and the whole pipeline. Never use it to judge answer
quality, and never let its output reach a customer as an investigation.

## 8. Testing and verification

```bash
cd backend && uv run pytest -q          # 228 tests, needs the database
cd backend && uv run ruff check forgeops tests
cd frontend && npx vitest run && npx tsc -b && npm run lint
```

Conventions that matter:

- Tests use scripted doubles (`tests/engine/fakes.py`, `tests/fixtures/mcp_test_server.py`); no test
  reaches a real provider. HTTP is faked with `httpx2.MockTransport` (the OpenAI SDK uses httpx2, so
  `respx` does not work).
- Database tests run against the `forgeops_test` schema on the real Supabase instance.
- A live end-to-end check is `uv run python -m forgeops.devtools.smoke "…problem…"`.
- Tool names of third-party MCP servers are **verified against the live server before being pinned**
  (`tests/connectors/test_catalog.py` records what was verified and when). Never guess them.

## 9. Adding a connector

1. Add a `ConnectorDefinition` to `connectors/definitions.py`: transport, auth (`token` or `oauth`),
   config fields, setup steps, the desks it serves, a `context` line for the Supervisor's service map,
   and the tool allowlist with capabilities and per-tool `max_output_chars`.
2. Capability → desk routing is in `capabilities/routing.py`; do not route in the connector.
3. Verify the upstream tool names against the real server, then pin them in `test_catalog.py`.
4. A write tool needs `permission="write"`, `Capability.write`, an `allow_writes` config field, and a
   fixed argument set that the model cannot override.

## 9a. Writing the project report

`docs/report/` is a self-contained pack for whoever writes the final-year project report: project
overview, literature survey, architecture, module guide, data model, harness, API reference,
frontend guide, testing, results, milestones, setup, limitations, glossary, and a 60-page chapter
outline. Start at `docs/report/README.md`. Its rule is the project's rule: every number is tagged
measured, computed or planned, and nothing is invented.

## 10. Current state (2026-10-14)

Done: foundation and auth; the engine and War Room; the Connectors page with Knowledge, GitHub,
Supabase and Cloudflare; token metering and context discipline; the OAuth connect flow; intent
triage (`engine/triage.py`) that answers platform questions with no model call, and empty-result
backoff so a desk stops searching a source that keeps returning nothing.

Use `uv run python -m forgeops.devtools.mcp_tools [connection-id]` to list what a connected MCP
server really offers before pinning its tool names.

The ICSIE 2026 paper was presented. Next: pin Cloudflare, Sanity and Sentry tool names against
live accounts, execute the evaluation protocol in `docs/report/10-results-and-measurements.md`, and
run the first live root-cause investigation.
`docs/superpowers/plans/` holds the per-milestone plans; read the newest one before starting work.
