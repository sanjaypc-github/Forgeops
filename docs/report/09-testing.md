# 09 — Testing and verification

Feeds **Chapter 5 (Testing / Results)**.

---

## 9.1 Testing philosophy

Three rules shape every test in this project:

1. **No test reaches a real model or a real customer tool.** Model behaviour is scripted; MCP servers
   are replaced by a local fixture server; HTTP is intercepted in memory. Tests are therefore fast,
   deterministic and free.
2. **Tests encode the product promises, not just the code paths.** For example, there is a test
   asserting that an uncited finding is rejected, and one asserting that an investigating desk is
   never handed a write tool. If someone breaks a promise, a test fails.
3. **Fakes live only in `backend/tests/`.** Runtime code contains no mock data. The single, explicit
   exception is the clearly labelled offline mode (§9.6).

## 9.2 Test inventory

| Suite | Location | What it covers |
|---|---|---|
| Engine | `backend/tests/engine/` | Specialist loop, questions, supervisor, RCA, report, graph, structured output, prompts, metering, checkpointing, offline mode |
| Capabilities | `backend/tests/capabilities/` | Registry routing and policy; tool runner retry, timeout, truncation, events |
| Connectors | `backend/tests/connectors/` | Catalog pinning, MCP client over stdio and HTTP, OAuth, token refresh, knowledge connector |
| Knowledge | `backend/tests/knowledge/` | Chunking and hybrid retrieval |
| API | `backend/tests/test_*_api.py`, `test_auth.py`, `test_security.py`, `test_health.py`, `test_database_schema.py` | Endpoints, authentication, CSRF, scoping, SSE replay, OAuth flow |
| Frontend | `frontend/src/**/*.test.ts(x)` | Office reducer, chat panel, connectors page, login, event stream, layout |

**Totals as of this commit: 228 backend tests and 36 frontend tests — 264 automated tests.**

## 9.3 Current pass state (be precise about this in the report)

| Group | Count | Status |
|---|---|---|
| Backend | 228 | **All passing** (342 s, 28 October 2026) |
| Frontend | 36 | **All passing** |

Earlier in the project the Supabase instance was paused twice by the provider's free-tier inactivity
policy, which blocked the 60 database-backed tests. After the project was restored, the complete
suite passes. If a run is ever reported with fewer tests, check database availability first — it is
an infrastructure condition, not a code defect.

## 9.4 Representative tests worth naming in the report

| Test | What it proves |
|---|---|
| `test_tool_then_cited_findings` | A desk calls a real tool and submits a finding citing that call |
| `test_findings_without_valid_citations_are_rejected` | The harness refuses an uncited claim and offers one repair |
| `test_older_tool_output_is_collapsed_but_still_citable` | Compaction shrinks context while citations stay valid |
| `test_the_system_prompt_is_identical_across_turns_so_it_can_be_cached` | Prompt-prefix stability for caching |
| `test_a_tool_may_cap_its_own_output_below_the_run_budget` | Per-tool output caps are honoured |
| `test_every_tool_routes_to_a_desk_the_connector_lists` | Capability routing is consistent across the catalog |
| `test_supabase_is_read_only_pinned_and_never_exposes_keys` | The Supabase connector cannot leak project keys |
| `test_an_oauth_connection_sends_the_token_its_provider_hands_over` | The refreshed token is the one actually used |
| `test_parallel_desks_refresh_the_token_only_once` | Concurrent desks do not stampede the token endpoint |
| `test_another_workspace_cannot_finish_someone_elses_consent` | OAuth consents are bound to the workspace that started them |
| `test_the_callback_page_escapes_what_the_provider_sent` | The cross-site-scripting defect found in review stays fixed |
| `test_approval_pause_survives_a_restart` | The graph resumes from its checkpoint after a restart |
| `test_events_stream_honours_last_event_id` | Event replay is correct, so the UI is refresh-safe |
| `test_run_cost_reports_what_each_desk_spent` | Token accounting is attributed per desk |

## 9.5 How to run the tests

```bash
# backend — everything (needs the database for 60 of them)
cd backend && uv run pytest -q

# backend — only what runs without a database
cd backend && uv run pytest tests/engine tests/capabilities tests/connectors tests/knowledge -q

# lint
cd backend && uv run ruff check forgeops tests

# frontend
cd frontend && npx vitest run && npx tsc -b && npm run lint
```

## 9.6 Test doubles

| Double | File | Replaces |
|---|---|---|
| `ScriptedLLM` | `tests/engine/fakes.py` | The model: returns a scripted reply per purpose, and records every request for assertions |
| `FakeConnector` | `tests/engine/fakes.py` | A connector with fixed tool specs and scripted results |
| `HashEmbedder` | `tests/engine/fakes.py` | Sentence embeddings, so no model is downloaded |
| MCP fixture server | `tests/fixtures/mcp_test_server.py` | A real MCP server over stdio or HTTP, including a deliberately destructive tool that must never be exposed |
| `httpx2.MockTransport` | throughout | All outbound HTTP, including the OpenRouter and OAuth endpoints |

A note the report can use: `respx`, the usual HTTP mocking library, does not work here because the
OpenAI SDK uses `httpx2`; the project therefore uses `MockTransport` directly.

## 9.7 Verification beyond unit tests

| Activity | What it adds |
|---|---|
| **Schema validation** | A test asserts the tables are created in the private `forgeops` schema and not in `public` |
| **Security review** | An automated review found a reflected cross-site-scripting defect in the OAuth callback page; it was fixed (escaping plus origin-restricted messaging) and two regression tests were added |
| **Live smoke run** | `uv run python -m forgeops.devtools.smoke "…"` runs one real investigation end to end and prints the event stream |
| **Manual UI verification** | The War Room is exercised through `/dev/office`, which replays scripted events without a backend |

## 9.8 Offline mode as a verification tool

`FORGEOPS_LLM=offline` runs the **real graph against real connectors** with a stand-in in place of the
model. It is used to verify plumbing — connectors, events, the office, the report — without a
provider key. Every answer it produces is labelled `OFFLINE MODE (no language model connected)`,
findings carry confidence `0.0`, no actions are proposed, the report warns at the top, and the mode
refuses to start when `FORGEOPS_ENV=production`.

This is the project's one deliberate exception to "no mock data", and the report should present it
that way: an explicitly labelled development aid, fenced off from production by code.
