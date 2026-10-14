# 11 — Milestones and project status

Feeds **Chapter 5/6** and any project-management section the report requires. Dates come from the
Git history; status is as of the commit containing this file.

---

## 11.1 Milestone summary

| Milestone | Scope | Status | Dates |
|---|---|---|---|
| **M0** — Foundation | Repository, backend skeleton, data model, auth and sessions, event bus with SSE, React shell, login | ✅ Complete | 17–21 Sep 2026 |
| **M0.5** — Managed database | Move from local Docker Postgres to Supabase; private `forgeops` schema; Docker made optional | ✅ Complete | 21 Sep 2026 |
| **M1** — Agent engine | Capability registry, MCP client layer, LLM client with structured output, the investigation graph, supervisor, specialists, agent-to-agent questions, RCA with confidence caps, report, knowledge connector, runner, smoke tool | ✅ Complete | 21 Sep 2026 |
| **M2** — War Room | Pixel office, floor plan and path-finding, walking agents, evidence wall, RCA board, chat bar with approval buttons, office reducer, history page | ✅ Complete | 22 Sep 2026 |
| **M3** — Connector catalog | GitHub and Supabase connectors verified against the live servers, catalog with coming-soon entries, connection APIs (abilities, test, tools), service map for planning, Connectors page | ✅ Complete | 22 Sep 2026 |
| **M3.5** — Observability and context discipline | Token metering per desk, run-cost reporting, rolling compaction, per-tool output caps, cache-stable prompts, configurable budgets, checkpoint serializer allow-list | ✅ Complete | 28 Sep 2026 |
| **M4** — OAuth and further connectors | OAuth client (discovery, dynamic registration, PKCE, refresh), token storage and refresh under lock, connect flow and callback, Connectors-page consent button | 🟡 **Partially complete** — framework done and tested; Cloudflare, Sanity and Sentry connector definitions not yet pinned | 28 Sep 2026 |
| **M5** — Actions and hardening | GitHub issue creation on approval (implemented, not yet exercised live), audit log (implemented), budget tuning (implemented), evaluation write-up | 🟡 **Partially complete** | — |
| **Evaluation study** | Execute the protocol in `10-results-and-measurements.md` | ⬜ Not started | — |

## 11.2 What "partially complete" means precisely

**M4.** The OAuth framework is implemented and tested offline: protected-resource and
authorization-server discovery, RFC 7591 dynamic client registration, PKCE with S256, code exchange,
refresh under a lock with rotation-safe storage, the start and callback endpoints, and the consent
button in the user interface. What remains is to pin the **actual tool names** for Cloudflare, Sanity
and Sentry against live accounts. Those names were deliberately *not* guessed: during M3 the project
learned that GitHub had consolidated its MCP tool names and that Supabase had renamed `get_logs` to
`query_logs`, so the rule became "verify against the live server, then pin in a test".

**M5.** The write path exists end to end — an approved recommendation of type `github_issue` calls
the allow-listed `github.create_issue` tool through a separate write session — but it has not yet been
exercised against a real repository, because that requires a live token and a real incident.

## 11.3 Chronology for the report

| Date | Event |
|---|---|
| 6 Aug 2026 | First structural sketch of the repository |
| 17 Sep 2026 | Repository restructured for the real build |
| 21 Sep 2026 | PRD and TRD written; M0, M0.5 and M1 implemented |
| 22 Sep 2026 | M2 War Room and M3 connector catalog implemented |
| 28 Sep 2026 | M3.5 observability and context discipline; OAuth framework; security review and fix |
| Oct 2026 | Paper accepted and **presented at ICSIE 2026**; documentation pack for this report prepared |

## 11.4 Engineering practice worth describing

The report can legitimately claim a disciplined process:

1. **Plan before code.** Each milestone has a written plan in `docs/superpowers/plans/`, created
   before implementation, listing tasks and constraints.
2. **Tests encode promises.** 232 automated tests; the product rules (citation, read-only, approval)
   each have a test.
3. **External facts are verified, not assumed.** Third-party tool names were checked against live
   servers and then pinned in `tests/connectors/test_catalog.py` with the verification date.
4. **Security review was acted upon.** An automated review found a reflected cross-site-scripting
   defect in the OAuth callback page; it was fixed with escaping and origin-restricted messaging, and
   two regression tests were added.
5. **Documentation is part of the deliverable.** `AGENTS.md`, `docs/HARNESS.md`, `docs/PRD.md`,
   `docs/TRD.md` and this report pack are maintained with the code.

## 11.5 Known infrastructure issue at the time of writing

The Supabase PostgreSQL instance used for development (`ldiotijmcnlxaawrbyps`) is **currently
unreachable**: the pooler reports `tenant/user … not found` and the project's REST endpoint does not
respond. The project is either paused or has been removed from the Supabase account.

Consequences and required action:

- 60 of the 198 backend tests cannot run until a database is available.
- The fix is to restore or recreate the Supabase project, put the new connection string in `.env`,
  and run `uv run alembic upgrade head`. No code change is needed — the schema is in migrations.
- The report should mention this only if it discusses the current test state; it is an infrastructure
  availability issue, not a defect in the system.
