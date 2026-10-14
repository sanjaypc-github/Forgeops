# 04 — Module guide

Feeds **Chapter 4 (System Implementation)**. One section per module: what it does, which files, the
important classes and functions, and the algorithm in words.

Code size as of this commit: **66 Python files, ≈5,340 lines** in `backend/forgeops/`;
**35 TypeScript files, ≈3,590 lines** in `frontend/src/`.

---

## 4.1 Module map

| # | Module | Package | Lines | Responsibility |
|---|---|---|---|---|
| 1 | Configuration | `forgeops/config.py` | 70 | Typed settings from `.env`; model and budget selection |
| 2 | Application entry | `forgeops/main.py` | 94 | App factory, lifespan, dependency wiring |
| 3 | API layer | `forgeops/api/` | ~740 | 21 REST endpoints, SSE stream, auth, CSRF |
| 4 | Investigation engine | `forgeops/engine/` | ~1,700 | Graph, supervisor, specialists, questions, RCA, report, runner |
| 5 | LLM layer | `forgeops/engine/llm/` | ~460 | Provider client, structured output, metering, offline stand-in |
| 6 | Capability layer | `forgeops/capabilities/` | ~250 | Tool registry, routing, policy, retry, truncation |
| 7 | Connector layer | `forgeops/connectors/` | ~890 | Catalog, MCP client, OAuth, token refresh, knowledge connector |
| 8 | Knowledge index | `forgeops/knowledge/` | ~160 | Chunking, embeddings, hybrid retrieval |
| 9 | Event system | `forgeops/events/` | ~140 | Persisted event bus, SSE replay |
| 10 | Persistence | `forgeops/db/` | ~190 | SQLAlchemy models, session factory, Alembic migrations |
| 11 | Security | `forgeops/security/` | ~90 | Password hashing, Fernet secret box, token hashing |
| 12 | Dev tools | `forgeops/devtools/` | ~240 | Windows-safe server launcher, CLI smoke run, `.env` helper |
| 13 | Frontend | `frontend/src/` | ~3,590 | War Room, Connectors page, history, report, event stream |

---

## 4.2 Configuration (`forgeops/config.py`)

A single Pydantic `Settings` class reads the repository-root `.env`. Groups: database, security and
admin bootstrap, CORS, LLM provider and per-role models, time budgets, context-discipline limits,
knowledge paths.

Key methods:
- `model_for(role)` — returns the model id for `supervisor`, `specialist` or `rca`, so each role can
  use a different model.
- `budgets()` — builds the `Budgets` dataclass from environment values, so limits are tunable
  without touching code.

## 4.3 API layer (`forgeops/api/`)

| File | Endpoints |
|---|---|
| `auth.py` | login, logout, me — cookie session, CSRF token issued on login |
| `investigations.py` | create, list, detail, decision, report, SSE event stream with `Last-Event-ID` replay |
| `chat.py` | post a chat message; starts an investigation or adds a note to a running one |
| `connections.py` | connector catalog, create/test/delete a connection, list its abilities |
| `oauth_flow.py` | start an OAuth consent, handle the provider callback |
| `agents.py` | desk roster with connected capabilities, for the War Room |
| `health.py` | liveness and database check |
| `deps.py` | `current_user`, `require_csrf` dependencies |

Security properties worth describing in the report: session cookie + CSRF header on unsafe methods;
secrets never returned by any endpoint; the OAuth callback page HTML-escapes every value and posts
its result only to configured origins; a consent is single-use, expires in 10 minutes, and can only
be completed by the workspace that started it.

## 4.4 Investigation engine (`forgeops/engine/`)

### 4.4.1 `graph.py` — the orchestration graph (219 lines)

Builds the LangGraph `StateGraph` with nodes `plan`, `specialist`, `review`, `rca`, `approval`,
`action`, `report`. `RunDeps` carries the LLM, registry, tool runner, event emitter, budgets, clock,
service map and usage meter.

- `to_specialists()` returns a list of `Send` objects — this is the fan-out that makes desks parallel.
- `after_review()` either loops back for one more round or proceeds to RCA.
- `approval_node()` calls `interrupt()`, which suspends the graph and persists the checkpoint.
- `action_node()` executes only the recommendations whose ids the human approved.

### 4.4.2 `supervisor.py` — planning and review (183 lines)

`plan_investigation()` sends the incident and the list of **connected** desks to the model and
requires a typed `submit_plan` tool call. A validator rejects a plan that assigns a desk with no
tools, so the plan can never promise an investigation the system cannot perform.
`review_evidence()` decides, once, whether the collected evidence is sufficient or whether specific
follow-up tasks are needed.

### 4.4.3 `specialist.py` — one desk at work (319 lines, the largest module)

`SpecialistLoop` implements the budgeted reason-act loop:

```
run(task, incident, plan_summary):
    messages ← [task message with clock, objective, hints, incident, plan]
    loop until submit or budget exhausted:
        reply ← LLM(system prompt, compacted message view, tool schemas)
        for each tool call in reply:
            if call is submit_findings:  validate citations → accept or request one repair
            if call is ask_agent:        broker asks another desk, returns its evidence-backed answer
            otherwise:                   run the read tool through the ToolRunner
        append results; register a short form of each result for later compaction
    on timeout: force submit_findings so the desk always reports what it has
```

Three mechanisms inside this class are central to the contribution:
- **Citation validation** (`_accept`): a finding whose `tool_call_ids` do not correspond to
  successful calls is rejected with an explanatory message; a second failure fails that desk visibly.
- **Rolling compaction** (`_view`): the newest `keep_full_tool_outputs` results stay whole; older ones
  collapse to their opening while keeping their `call_id`, so earlier findings remain citable.
- **Forced submission** (`_forced_submit`): a desk that exhausts its time budget is made to report
  partial findings rather than hanging.

### 4.4.4 `questions.py` — the question broker (89 lines)

Lets a desk ask one precise question of another desk. Enforces per-agent and global question budgets,
prevents a desk asking itself, and returns the answer **together with the answering desk's evidence**,
so the asking desk can cite it. This is the bounded alternative to free-form multi-agent chat.

### 4.4.5 `rca.py` — root cause analysis (93 lines)

Receives only **evidence lines** — never raw tool output — plus the plan, the inter-desk questions,
errors, and the list of areas that could not be checked. Produces a typed `submit_rca` with summary,
failure point, category, confidence, timeline, supporting and contradicting evidence, alternative
hypotheses, missing information and recommendations. `apply_confidence_caps()` then overrides the
model's confidence in code.

### 4.4.6 `report.py` — deterministic report (114 lines)

Renders Markdown from the final state with **no model involvement**: root cause, timeline, evidence
table with links, inter-desk questions, what could not be checked, recommendations with their
approval outcome, errors, and the run-cost table.

### 4.4.7 `runner.py` — background execution (192 lines)

Owns the lifecycle: start, resume after approval, recover on restart. Wraps the LLM in `MeteredLLM`,
builds the per-workspace registry, enforces the whole-run timeout, records usage on the investigation
row, and converts any failure into a visible `investigation_failed` event.

### 4.4.8 `budgets.py`, `state.py`, `models.py`, `roster.py`, `prompts.py`

- `budgets.py` — every limit in one dataclass (tool calls, seconds, question budgets, output caps,
  compaction window, review and follow-up rounds).
- `state.py` — the LangGraph `TypedDict`; lists written by parallel desks merge through `operator.add`.
- `models.py` — the data contracts: `Incident`, `Plan`, `AgentTask`, `Evidence`, `ToolCallRecord`,
  `AgentQuestion`, `RCA`, `Recommendation`, `Decision`, `ActionResult`.
- `roster.py` — the nine agent profiles (title, area, focus).
- `prompts.py` + `prompt_templates/*.md` — prompt loading; the shared `common.md` plus one file per
  role. System prompts are kept identical across a desk's turns so a provider can cache the prefix.

## 4.5 LLM layer (`forgeops/engine/llm/`)

| File | Purpose |
|---|---|
| `base.py` | Provider-neutral types: `Message`, `ToolCall`, `ToolSchema`, `LLMRequest`, `LLMReply`, error classes |
| `openrouter.py` | OpenAI-compatible client against OpenRouter; retries empty answers; optional prompt-cache breakpoint; reports cached tokens |
| `structured.py` | `ask_structured()` — forces a named tool call, validates with Pydantic, allows exactly one repair attempt, then fails loudly |
| `metering.py` | `MeteredLLM` wrapper and `UsageMeter`: tokens per desk, events, run totals, merge on resume |
| `offline.py` | A labelled stand-in used when no provider key is available; drives the real graph against real connectors but performs no analysis, and refuses to run in production |

## 4.6 Capability layer (`forgeops/capabilities/`)

- `registry.py` — builds the tool list from all connected connectors; `tools_for(agent)` returns
  **read** tools for investigating desks and **write** tools only for the Action desk;
  `connected_agents()` tells the Supervisor which desks may be assigned.
- `runner.py` — every tool call passes through here: allow-list check, timeout, retry with backoff on
  transient errors, output truncation to the tool's own cap, event emission, and a `ToolCallRecord`
  with a 500-character excerpt for the audit trail.
- `routing.py` — capability → desk mapping.
- `models.py` — `ToolSpec`, `ToolResult`, `HealthStatus`, the `Connector` protocol.

## 4.7 Connector layer (`forgeops/connectors/`)

- `definitions.py` — the catalog. Each `ConnectorDefinition` declares transport, auth mode, URL or
  command, header or environment templates, configuration fields, setup steps, the desks it serves, a
  context line for the Supervisor's service map, and the **tool allow-list** with capabilities and
  per-tool output caps.
- `mcp.py` — the MCP client: HTTP (streamable) and stdio transports, a session owned by a dedicated
  task, connection-level default arguments, fixed arguments the model cannot override, a separate
  write session, and a health check that reports which allow-listed tools the server does not offer.
- `oauth.py` — protected-resource and authorization-server discovery, dynamic client registration,
  PKCE (S256), code exchange and refresh.
- `tokens.py` — the stored OAuth session and a `TokenProvider` that refreshes once under a lock and
  persists rotated refresh tokens immediately.
- `knowledge.py` — the native knowledge connector over a vault folder, with path validation against
  allowed roots.
- `factory.py` — turns stored connection rows into live connectors and builds the per-workspace
  registry, plus the service-map lines given to the Supervisor.

**Catalog contents:** `knowledge`, `github`, `supabase` are available; thirteen further connectors
(Cloudflare, Vercel, Netlify, Sanity, Sentry, GitLab, Firebase, MongoDB, Datadog, Prometheus, Notion,
Jira, Slack) are declared as *coming soon* so the catalog communicates the roadmap.

## 4.8 Knowledge index (`forgeops/knowledge/`)

- `chunking.py` — heading-aware Markdown chunking with overlap, preserving the document path and
  heading trail so a citation can name the section.
- `index.py` — Chroma collection per connection, embedding function, BM25 index, and reciprocal rank
  fusion of the two result lists.

## 4.9 Event system (`forgeops/events/`)

- `models.py` — 27 event types, from `investigation_started` to `investigation_completed`, including
  `tool_called`, `evidence_added`, `agent_question`, `llm_usage` and `context_compacted`.
- `bus.py` — persists each event with a monotonic sequence number per investigation, fans it out to
  live subscribers, and replays from a given sequence so the UI can reconnect without losing anything.

## 4.10 Persistence (`forgeops/db/`)

Nine tables (see `05-data-model.md`). SQLAlchemy 2 async models; the schema is private
(`forgeops`), set through the connection `search_path` so nothing is exposed through Supabase's
public data API. Alembic migrations are checked into `backend/alembic/versions/`.

## 4.11 Security (`forgeops/security/`)

- Password hashing for the admin account.
- `SecretBox` — Fernet encryption of connector secrets, derived from `FORGEOPS_SECRET_KEY`.
- Session token hashing, so a stolen database row cannot be replayed as a session.

## 4.12 Development tools (`forgeops/devtools/`)

- `serve.py` — starts the API with the Windows selector event loop that psycopg requires.
- `smoke.py` — runs one complete investigation from the command line and prints the event stream;
  the fastest way to demonstrate the system without the UI.
- `envfile.py` — reads and validates `.env` for the other tools.

## 4.13 Frontend (`frontend/src/`)

| Area | Files | Purpose |
|---|---|---|
| War Room | `war-room/layout.ts`, `floor.ts`, `Office.tsx`, `AgentSprite.tsx`, `placement.ts`, `tiles.ts` | The 2D office: tile floor, desks, walking agents, speech bubbles |
| Office state | `war-room/officeState.ts` (334 lines) | A **pure reducer** from events to UI state; fully unit-tested |
| Panels | `war-room/ChatPanel.tsx`, `SidePanels.tsx` | Chat with approval buttons, evidence wall, activity feed, run-cost meter |
| Art | `war-room/art/portraitArt.ts` (618 lines) | Procedural pixel characters (engine adapted from an MIT-licensed project; recipes are original) |
| Pages | `pages/WarRoomPage.tsx`, `ConnectorsPage.tsx`, `InvestigationsPage.tsx`, `ReportPage.tsx`, `LoginPage.tsx` | The five screens |
| API client | `api/client.ts`, `investigations.ts`, `connectors.ts`, `types.ts` | Typed fetch wrappers, CSRF handling |
| Live updates | `investigations/eventStream.ts` | SSE subscription with `Last-Event-ID` replay |

The reducer design is worth a paragraph in the report: because `officeState.ts` is a pure function of
the event list, the same events always produce the same office, the UI can be unit-tested without a
browser, and a page refresh mid-investigation replays rather than resets.
