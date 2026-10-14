# 03 — System architecture

Feeds **Chapter 3 (System Design / Proposed Methodology)**. Diagrams here are ASCII so they can be
redrawn in Visio, draw.io or PowerPoint for the report.

---

## 3.1 Architectural style

ForgeOps is a **layered, event-driven, multi-agent system**. Three properties define it:

1. **Separation by system area, not by task.** There is one agent per area of a customer's stack
   (code, hosting, backend, database, observability, knowledge), not one agent per step of a plan.
   The number of agents therefore stays constant as a customer's system grows; only the number of
   tools behind each desk grows.
2. **Everything is an event.** Every meaningful action emits a persisted event. The user interface
   is a pure function of the event stream, so refreshing the page replays the same state.
3. **The harness enforces correctness.** Validation, budgets, evidence rules and confidence caps live
   in code, not in prompts. A prompt can be ignored by a model; a validator cannot.

## 3.2 The six layers

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1. PRESENTATION LAYER            React 19 + TypeScript + Vite            │
│    War Room (2D office) · Chat bar · Connectors page · History · Report  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ REST + Server-Sent Events
┌───────────────────────────────▼──────────────────────────────────────────┐
│ 2. APPLICATION LAYER             FastAPI                                 │
│    Auth & sessions · Investigation lifecycle · Chat · Connections · SSE  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│ 3. ORCHESTRATION LAYER           LangGraph StateGraph                    │
│    plan → specialists (parallel) → review → rca → approval → action →    │
│    report, over one checkpointed shared state                            │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│ 4. SPECIALISED AGENT LAYER        One desk per system area               │
│    Code · Frontend & Hosting · Backend & Services · Database ·           │
│    Observability · Knowledge · (Action, writes only)                     │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ capability registry (routing + policy)
┌───────────────────────────────▼──────────────────────────────────────────┐
│ 5. CONNECTOR & MEMORY LAYER                                              │
│    MCP connectors (GitHub, Supabase, …) · Engineering Memory Layer       │
│    (Markdown → chunks → embeddings → Chroma + BM25 → RRF)                │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────┐
│ 6. DECISION & PERSISTENCE LAYER                                          │
│    RCA agent · human approval · Markdown report · PostgreSQL (Supabase)  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Layer responsibilities

| Layer | Responsibility | Key code |
|---|---|---|
| Presentation | Interaction only; no reasoning. Renders the live investigation from events. | `frontend/src/` |
| Application | HTTP surface, authentication, lifecycle, event streaming. | `backend/forgeops/api/` |
| Orchestration | The investigation graph, state merging, checkpointing, the approval interrupt. | `backend/forgeops/engine/graph.py`, `runner.py` |
| Specialised agents | One budgeted reason-act loop per desk; produces cited findings only. | `backend/forgeops/engine/specialist.py` |
| Connectors & memory | Tool access with an allow-list; retrieval over team documentation. | `backend/forgeops/connectors/`, `knowledge/` |
| Decision & persistence | Root cause, approval, report, durable storage. | `backend/forgeops/engine/rca.py`, `report.py`, `db/` |

## 3.3 The investigation graph

```
                         ┌──────────┐
      incident text ────►│   PLAN   │  Supervisor writes a typed plan;
                         └────┬─────┘  may assign only connected desks
                              │ fan-out (LangGraph Send)
        ┌──────────┬──────────┼──────────┬──────────┐
        ▼          ▼          ▼          ▼          ▼
    ┌───────┐ ┌───────┐  ┌───────┐  ┌───────┐  ┌─────────┐
    │ Code  │ │Hosting│  │  DB   │  │ Obsv. │  │Knowledge│   desks run concurrently;
    └───┬───┘ └───┬───┘  └───┬───┘  └───┬───┘  └────┬────┘   each may ask a colleague
        └─────────┴──────────┼──────────┴───────────┘        one budgeted question
                             │ fan-in (reducer merge)
                       ┌─────▼──────┐
                       │   REVIEW   │  Supervisor: is the evidence enough?
                       └─────┬──────┘  (at most one extra round)
                             ▼
                       ┌─────────────┐
                       │     RCA     │  reads evidence lines only, never raw logs
                       └─────┬───────┘
                             ▼
                       ┌─────────────┐
                       │  APPROVAL   │  graph interrupts; waits for a human
                       └─┬────┬────┬─┘
            approve ──────┘    │    └────── investigate more → back to PLAN
                  ▼            ▼ reject
            ┌──────────┐  ┌─────────┐
            │  ACTION  │─►│ REPORT  │  deterministic Markdown; no model involved
            └──────────┘  └─────────┘
```

**Implementation note for the report:** the fan-out is `langgraph.types.Send`, the fan-in is a state
channel reduced with `operator.add`, and the approval pause is `interrupt()` over an
`AsyncPostgresSaver` checkpoint — so the investigation survives a server restart and can wait hours
for a human.

## 3.4 Capability routing — why a new tool needs no new agent

A connector does not choose an agent. It declares **capabilities**, and the registry routes each
capability to the desk that owns that area.

| Capability | Desk that receives it |
|---|---|
| `code` | Code |
| `hosting` | Frontend & Hosting |
| `backend`, `content` | Backend & Services |
| `database` | Database |
| `errors`, `logs`, `metrics` | Observability |
| `knowledge` | Knowledge |
| `write` | Action (only after approval) |

Consequence: adding Cloudflare, Sentry or Datadog means adding a `ConnectorDefinition` with an
allow-list of tools and their capabilities. No agent code changes. This is the property that makes
the system **customer-side and tool-agnostic**, and it is a central novelty claim.

Code: `backend/forgeops/capabilities/routing.py`, `registry.py`.

## 3.5 The Engineering Memory Layer

```
Markdown runbooks, architecture notes, postmortems
            │  offline preprocessing
            ▼
      chunking (heading-aware, overlapping)
            │
            ▼
   embeddings ──────► Chroma vector store ──┐
                                            ├──► reciprocal rank fusion ──► cited evidence
   tokenised text ──► BM25 lexical index ───┘
```

Hybrid retrieval is used because incident queries mix natural language ("checkout is slow") with
exact identifiers ("`orders_by_user`", "`config/db.ts`"). Dense vectors handle the first; BM25
handles the second; reciprocal rank fusion merges the two ranked lists without tuning weights.

Code: `backend/forgeops/knowledge/`, `backend/forgeops/connectors/knowledge.py`.

## 3.6 Key design decisions and their rationale

A good Chapter 3 explains *why*, not just *what*. Use this table.

| Decision | Alternative rejected | Rationale |
|---|---|---|
| One agent per **system area** | One agent per task, created dynamically | Constant agent count; each desk's tools and prompt stay small and specialised; predictable cost |
| **Parallel** desks with isolated context | One agent with all tools and one long context | Bounded context per step; wall-clock follows the slowest desk, not the sum; avoids degradation in very long contexts |
| **Enforced citation** in the harness | Prompt instruction "please cite your sources" | A prompt can be ignored; a validator cannot. Roy et al. [11] show grounding is the main lever on honesty |
| **Confidence capped in code** | Trusting the model's self-reported confidence | Models are poorly calibrated; caps make the number mean something (no evidence ≤ 0.2; single source ≤ 0.6) |
| **MCP connectors with an allow-list** | Direct API clients per tool | One integration contract; new tools are configuration, not code; the allow-list bounds what an agent can ever do |
| **Read-only investigation, writes behind approval** | Autonomous remediation | Published agents resolve only 11–15% of real scenarios [13][15]; acting on that would be unsafe |
| **Events as the single source of UI truth** | Pushing UI state from the server | Refresh-safe replay, auditability, and a UI that can be tested as a pure reducer |
| **Budgets on every loop** | Letting agents run to completion | Guarantees termination and a bounded bill; a desk that runs out is forced to report what it has |
| **Rolling context compaction** | Resending every tool result each turn | Input cost grows quadratically with steps; compaction keeps citations valid while cutting resent context |

## 3.7 Technology stack

| Concern | Choice | Why |
|---|---|---|
| Backend language | Python 3.12 (uv) | Ecosystem for LLM orchestration and MCP |
| API framework | FastAPI + Pydantic v2 | Async, typed request/response contracts |
| Orchestration | LangGraph 1.2 | Typed state, parallel `Send`, reducers, durable checkpoints, `interrupt` |
| Database | PostgreSQL via Supabase; SQLAlchemy 2 async + asyncpg; Alembic | Managed Postgres with a private schema; migrations under version control |
| Model access | OpenAI-compatible SDK against OpenRouter | Model-agnostic; per-role model configuration |
| Tool access | Model Context Protocol (MCP) 2.2 | One contract for every external tool; HTTP and stdio transports |
| Retrieval | Chroma + BM25 + reciprocal rank fusion | Semantic plus lexical matching for technical queries |
| Frontend | React 19, TypeScript, Vite 8, TanStack Query | Typed UI, SSE-driven live updates |
| Testing | pytest (backend), Vitest + Testing Library (frontend) | Fast, offline, no live provider calls |

## 3.8 Non-functional requirements

| Requirement | How it is met |
|---|---|
| **Bounded cost** | Budgets per desk (8 tool calls, 300 s) and per run (1800 s); per-tool output caps; token metering per desk |
| **Bounded context** | Per-desk isolation; rolling compaction keeping the newest 3 results whole |
| **Safety** | Read-only investigating desks; write tools opt-in and approval-gated; tool output treated as data, never as instructions |
| **Auditability** | Persisted events, an audit log table, and evidence that cites tool calls |
| **Resilience** | Durable checkpoints; the approval pause survives restart; a failing desk does not stop the others |
| **Confidentiality** | Connector tokens encrypted at rest (Fernet) and never returned to the browser |
| **Extensibility** | New connectors are declarative; capability routing requires no agent change |
