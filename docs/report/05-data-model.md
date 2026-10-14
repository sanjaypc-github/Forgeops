# 05 — Data model

Feeds **Chapter 4 (Implementation)** and the report's ER diagram. Source of truth:
`backend/forgeops/db/models.py`, `backend/forgeops/engine/state.py`,
`backend/forgeops/engine/models.py`, `backend/forgeops/events/models.py`.

---

## 5.1 Database overview

PostgreSQL (hosted on Supabase), **nine tables** in a private schema named `forgeops`. The schema is
selected through the connection `search_path`, so none of these tables is reachable through
Supabase's public data API. Migrations live in `backend/alembic/versions/`.

```
workspaces ──1:N── memberships ──N:1── users
     │                                   │
     ├──1:N── investigations ──1:N── events
     │              │
     │              └──1:N── chat_messages
     ├──1:N── connections
     ├──1:N── audit_log
     └──1:N── auth_sessions ──N:1── users
```

## 5.2 Table reference

### `workspaces`
One tenant. The MVP exposes a single workspace; the model is ready for multi-tenant SaaS.

| Column | Type | Notes |
|---|---|---|
| `id` | String(40) PK | prefixed id, `ws_…` |
| `name` | String(200) | display name |
| `created_at` | timestamptz | |

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | String(40) PK | `usr_…` |
| `email` | String(320) unique, indexed | login identity |
| `password_hash` | String(255) | hashed, never plain |
| `created_at` | timestamptz | |

### `memberships`
Join table between users and workspaces, carrying the role (`admin` in the MVP).

| Column | Type | Notes |
|---|---|---|
| `id` | String(40) PK | `mem_…` |
| `workspace_id` | FK → workspaces, cascade | |
| `user_id` | FK → users, cascade, indexed | |
| `role` | String(20) | default `admin` |
| `created_at` | timestamptz | |

### `auth_sessions`
| Column | Type | Notes |
|---|---|---|
| `id` | String(64) PK | **SHA-256 of the cookie token**, so the raw token is never stored |
| `user_id` | FK → users, cascade, indexed | |
| `workspace_id` | FK → workspaces, cascade | |
| `csrf_token` | String(64) | compared against the `X-CSRF-Token` header on unsafe methods |
| `expires_at` | timestamptz | TTL from configuration |
| `created_at` | timestamptz | |

### `investigations`
The central record.

| Column | Type | Notes |
|---|---|---|
| `id` | String(40) PK | `inv_…`; also the LangGraph `thread_id` |
| `workspace_id` | FK → workspaces, cascade, indexed | |
| `description` | Text | the problem as the user stated it |
| `service_id` | String(40) nullable | optional service hint |
| `source` | String(20) | `web` or `chat` |
| `status` | String(30) | `queued`, `running`, `awaiting_approval`, `acting`, `completed`, `rejected`, `failed` |
| `created_by` | String(40) nullable | user id |
| `window_start`, `window_end` | timestamptz nullable | time window under investigation |
| `usage` | JSONB nullable | token accounting: totals and per-desk breakdown |
| `created_at`, `updated_at` | timestamptz | |

### `events`
Append-only log; the user interface is a function of this table.

| Column | Type | Notes |
|---|---|---|
| `id` | BigInteger PK, autoincrement | |
| `investigation_id` | FK → investigations, cascade | |
| `workspace_id` | String(40) | denormalised for scoping |
| `seq` | Integer | monotonic **per investigation**; unique with `investigation_id` |
| `type` | String(50) | one of the 27 event types |
| `agent` | String(40) nullable | which desk emitted it |
| `ts` | timestamptz | |
| `data` | JSONB | event-specific payload |

`seq` is what makes Server-Sent Events replayable: a reconnecting browser sends `Last-Event-ID` and
receives everything after it.

### `connections`
A connected tool.

| Column | Type | Notes |
|---|---|---|
| `id` | String(40) PK | `con_…` |
| `workspace_id` | FK → workspaces, cascade | |
| `type` | String(40) | catalog key: `github`, `supabase`, `knowledge`, … |
| `name` | String(120) | user-chosen label |
| `config` | JSONB | non-secret settings (repository, project ref, flags) |
| `secret_encrypted` | Text nullable | **Fernet-encrypted JSON**: tokens, OAuth session |
| `status` | String(20) | `connected`, `error`, `connecting` |
| `last_error` | Text nullable | health-check detail shown in the UI |
| `created_at`, `updated_at` | timestamptz | |

### `chat_messages`
| Column | Type | Notes |
|---|---|---|
| `id` | String(40) PK | `msg_…` |
| `workspace_id` | FK → workspaces | |
| `investigation_id` | FK → investigations, cascade | |
| `role` | String(20) | `user` or `supervisor` |
| `text` | Text | |
| `created_at` | timestamptz | |

### `audit_log`
Who did what, for accountability: connection created, tested or deleted; OAuth started and completed;
approval decisions. Columns: workspace, actor, channel (`web`), action, target, JSONB detail, timestamp.

## 5.3 Investigation state (LangGraph)

`backend/forgeops/engine/state.py`. This is the "shared investigation state" of the paper. Lists
written by parallel desks are merged with `operator.add` reducers, so concurrent writes never
overwrite one another.

| Channel | Type | Reducer | Meaning |
|---|---|---|---|
| `workspace_id`, `investigation_id` | str | last write | identity |
| `incident` | `Incident` | last write | the problem, window, notes |
| `capabilities` | dict | last write | desks and their capabilities |
| `plan` | `Plan \| None` | last write | the Supervisor's plan |
| `pending_tasks` | list[`AgentTask`] | last write | what to fan out next |
| `evidence` | list[`Evidence`] | **add** | findings from all desks |
| `tool_calls` | list[`ToolCallRecord`] | **add** | the audit trail of every call |
| `questions` | list[`AgentQuestion`] | **add** | inter-desk questions and answers |
| `errors` | list[`AgentError`] | **add** | desks that failed |
| `warnings` | list[str] | **add** | unavailable connectors, offline-mode notice |
| `context_saved_chars` | int | **add** | characters not resent, thanks to compaction |
| `review_rounds`, `followup_rounds` | int | last write | loop counters against budgets |
| `rca` | `RCA \| None` | last write | the root-cause analysis |
| `decision` | `Decision \| None` | last write | the human decision |
| `action_results` | list[`ActionResult`] | **add** | outcome of approved actions |
| `report_markdown` | str \| None | last write | the final report |

The state is checkpointed to PostgreSQL by `AsyncPostgresSaver`, with a serializer that allows only
the project's own types to be deserialised — a defensive measure against unexpected objects entering
a checkpoint.

## 5.4 Core contracts (`engine/models.py`)

| Type | Important fields | Purpose |
|---|---|---|
| `Incident` | text, source, window_start, window_end, service_hint, notes | the problem statement |
| `Plan` | summary, hypotheses, tasks, skipped, window | the Supervisor's typed output |
| `AgentTask` | agent, objective, hints | one desk's assignment |
| `ToolCallRecord` | id (`tc_…`), agent, tool, connector_type, connection_id, args_summary, ok, duration_ms, truncated, result_excerpt, error | the audit trail; **the citation target** |
| `Evidence` | id (`ev_…`), agent, capability, connection_id, connector_type, finding, failure_point, artifacts, severity, confidence, limitations, **tool_call_ids** | a cited finding |
| `Artifact` | type, ref, url, timestamp, excerpt | the concrete object (commit, query, document) |
| `AgentQuestion` | id, from_agent, to_agent, question, answer, status, reason | inter-desk exchange |
| `RCA` | summary, failure_point, category, confidence, timeline, supporting_evidence, contradicting_evidence, alternative_hypotheses, missing_information, recommendations | the result |
| `Recommendation` | id (`rec_…`), title, description, action, parameters, requires_approval | proposed next step |
| `Decision` | kind (`approve`/`reject`/`investigate_more`), approved_recommendation_ids, note, decided_by, channel | the human's choice |
| `ActionResult` | recommendation_id, status, detail, url | what the Action desk did |

**The citation chain, which the report should state explicitly:**

```
Evidence.tool_call_ids → ToolCallRecord.id → the real tool call, its arguments and its result
RCA.supporting_evidence → Evidence.id → that chain again
```

Nothing in a report can be traced to nothing; a claim either reaches a successful tool call or it is
rejected by the harness.

## 5.5 Event catalogue (27 types)

| Group | Events |
|---|---|
| Lifecycle | `investigation_started`, `investigation_completed`, `investigation_failed` |
| Supervisor | `supervisor_started`, `plan_created`, `agent_skipped`, `review_completed` |
| Desk work | `agent_started`, `agent_completed`, `agent_failed`, `tool_called`, `tool_completed`, `evidence_added` |
| Collaboration | `agent_question`, `agent_answer`, `agent_question_failed`, `chat_message` |
| Decision | `rca_started`, `rca_completed`, `approval_requested`, `approval_granted`, `approval_rejected` |
| Action & output | `action_started`, `action_completed`, `report_ready` |
| Observability | `llm_usage`, `context_compacted` |

Each event carries `seq`, `type`, `agent`, `ts` and a JSONB `data` payload. The War Room reducer in
`frontend/src/war-room/officeState.ts` maps these onto the office: `tool_called` makes a desk type a
speech bubble, `agent_question` makes an agent walk to another desk, `evidence_added` pins a card to
the evidence wall, `llm_usage` updates the cost meter.
