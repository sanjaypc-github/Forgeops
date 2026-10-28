# M6 — Triage, search discipline and the Cloudflare connector

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Why:** a measured investigation ("is all the connectors connected successfully?") cost **74,850
tokens across 20 model calls**, of which the Knowledge desk alone spent **50,085 input tokens in 12
calls** — 72% of the run — searching a vault that contained nothing relevant. Two further
investigations failed on OpenRouter free-tier daily rate limits. Cost is now the product's main
weakness, and the Frontend & Hosting desk is empty in the demo.

**Goal:** stop paying full investigation price for questions that are not incidents, stop a desk
searching after it has learned there is nothing to find, and fill the hosting desk with Cloudflare.

## Measured baseline (keep for the report)

| Desk | Calls | Input tokens | Share |
|---|---|---|---|
| knowledge | 12 | 50,085 | 72% |
| database | 4 | 11,774 | 17% |
| supervisor | 3 | 5,251 | 8% |
| rca | 1 | 2,185 | 3% |
| **total** | **20** | **69,295 in / 5,555 out** | 7,688 saved by compaction |

## Tasks

1. **Intent triage before the graph.** Classify an incoming chat message as `status`, `followup` or
   `incident`. A `status` message is answered from the database — connections, their health and their
   abilities — with **no model call at all**. A `followup` on a finished investigation is answered
   from stored evidence with one small call. Only `incident` starts the investigation graph. The
   decision and its reason are emitted as an event so the War Room can show it.
   *Target: the measured question drops from ~74,800 tokens to under 1,000.*

2. **Search discipline in the specialist loop.** Track consecutive tool results that return nothing
   useful. After `Budgets.empty_results_before_stop` (default 2), the desk is told to stop searching
   and submit what it has, with the gap recorded as a limitation. A knowledge connector also caps how
   many results it returns per query.
   *Target: the knowledge desk's 12 calls become 3–4 on a vault with no relevant content.*

3. **Cloudflare connector.** `https://mcp.cloudflare.com/mcp?codemode=false` with an API token as a
   bearer header, so the agent gets specific read endpoints instead of the `execute` tool that can
   call any Cloudflare API. Tools serve the Frontend & Hosting and Observability desks. Because
   upstream tool names cannot be guessed, ship a discovery command that lists what a live account
   actually offers, then pin those names in `test_catalog.py` with the verification date.

4. **Per-desk token visibility in the War Room.** The cost meter already shows run totals; add the
   per-desk breakdown that is already stored in `investigations.usage`, so the biggest spender is
   visible during a demo.

## Constraints (unchanged)

- Allowlist only; a tool the server does not offer is reported by the health check, never faked.
- Investigating desks keep read tools only; writes stay behind human approval.
- No mock data at runtime; triage answers come from the real connections table.
- Every number claimed in the report must be measured, computed or planned — and labelled.

## Out of scope for this milestone

- Notion connector (hosted server is OAuth-only and not built for headless agents; the local server
  takes an integration token and is the fallback if time allows).
- Model cascade and prompt caching: configuration changes that need a paid model, not code.
