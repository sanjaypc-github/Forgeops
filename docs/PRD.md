# ForgeOps — Product Requirements Document (MVP)

| | |
|---|---|
| Product | ForgeOps (Engineering Operations Platform, EOPS) |
| Document | PRD, MVP scope |
| Status | Draft for review |
| Date | 2026-09-21 |
| Companion | [TRD.md](TRD.md) (technical design), [reference/PROJECT_SPEC.md](reference/PROJECT_SPEC.md) (original vision) |

---

## 1. Summary

ForgeOps is a SaaS platform that investigates software incidents for engineering teams. A company connects the tools it already uses (GitHub, Sentry, Prometheus, Loki, its runbooks). When something breaks, a Supervisor AI agent plans an investigation, specialist agents collect evidence from those tools **in parallel**, an RCA agent correlates the evidence into a root cause with confidence and citations, and a human approves any action before it happens. The whole investigation is shown live in the **War Room**: a top-down office where each agent works at its own desk, driven only by real backend events.

The MVP is a **minimal, real, deployable product**. It uses no mock data at runtime. Every finding comes from a real API call to a connected tool.

## 2. Problem

When production breaks, engineers investigate by hand across many tabs: the repo, CI runs, error tracker, metrics, logs, and outdated runbooks. The first 20–40 minutes of every incident are spent collecting context rather than fixing. Small SaaS teams have no dedicated SRE; larger teams page engineers about services they do not own.

## 3. Target users

| Persona | Situation | What ForgeOps gives them |
|---|---|---|
| **SaaS founder / CTO** (primary for MVP) | 5–20 engineers, founders on call, no SRE | A "virtual SRE": connect tools once, get an evidence-backed root cause in minutes |
| **On-call engineer** at a scale-up | Paged about a service they don't own | The first 30 minutes of investigation done, with runbooks and code changes pulled in |
| **Platform / SRE lead** | Needs control over AI access to production | Read-only by default, human approval for every write, full audit trail |

## 4. Goals and non-goals

### Goals (MVP)
1. An engineer can start an investigation from the web app or Slack and see a root cause with cited evidence in under 5 minutes.
2. Agents investigate **real** tools: GitHub (code + Actions), Sentry, Prometheus, Loki, and a Markdown knowledge vault.
3. ForgeOps works with **any subset** of connected tools and says clearly what it could not check.
4. The War Room shows real agent activity live, as an office floor.
5. No write to any external system happens without explicit human approval.
6. The product is multi-company ready in its data model (workspaces), with one workspace exposed in the MVP UI.

### Non-goals (MVP)
- Sign-up, billing, multiple workspaces in the UI, team roles beyond admin.
- Vercel, Supabase, Kubernetes, Datadog, Jira, PagerDuty connectors (post-MVP; the capability model is built so they plug in without agent changes).
- Infrastructure, Database and Incident agents doing work (their desks exist in the War Room as "not connected").
- Automatic remediation (rollbacks, restarts, merges). The only MVP write is creating a GitHub issue.
- Production hosting decisions (the user decides deployment later; the MVP runs via Docker Compose).

## 5. MVP scope

### 5.1 Agents

| Agent | MVP status | Uses capability |
|---|---|---|
| Supervisor | Active | service map, capability registry |
| Code | Active | `code` (GitHub) |
| Deployment | Active | `deployments` (GitHub Actions, releases) |
| Observability | Active | `errors` (Sentry), `metrics` (Prometheus), `logs` (Loki) |
| Knowledge | Active | `knowledge` (vault RAG) |
| RCA | Active | reads shared evidence only |
| Action | Active, limited | `create_issue` (GitHub), report generation |
| Infrastructure, Database, Incident | Desk shown, "not connected" | none in MVP |

### 5.2 Connectors

| Connector | Access | Notes |
|---|---|---|
| GitHub | Read (code, PRs, Actions); write only `create_issue` after approval | Via official GitHub MCP server |
| Sentry | Read | Issues, events, stack traces, releases |
| Prometheus | Read | PromQL instant/range queries, alerts |
| Loki | Read | LogQL queries |
| Knowledge vault | Read | Markdown/Obsidian folder, hybrid search |
| Slack | Bot | Start investigations, post status/RCA, approve/reject buttons |

### 5.3 Sample SaaS (test target, part of the repo)
A small real online shop — web frontend, checkout API, Postgres — instrumented with Sentry, Prometheus, Loki and Grafana, with its own GitHub repo and CI/CD. It exists so ForgeOps has a real system to investigate; it contains **planned fault scenarios** that are real code changes, each with a known root cause for accuracy testing.

## 6. User stories

### Setup
- **US-1** As an admin, I sign in to ForgeOps with email and password.
- **US-2** As an admin, I add a connection (GitHub, Sentry, Prometheus, Loki, knowledge vault) by entering its URL/token; ForgeOps tests it and shows healthy/unhealthy and the capabilities it provides.
- **US-3** As an admin, I see exactly which read and write permissions each connection gives ForgeOps; write tools are off unless I enable them.
- **US-4** As an admin, I define services (name, aliases, GitHub repo, Sentry project, Prometheus job label, Loki label selector).
- **US-5** As an admin, I point ForgeOps at a knowledge vault folder and see how many documents are indexed.
- **US-6** As an admin, I connect Slack and choose the incident channel.

### Investigating
- **US-7** As an engineer, I describe an incident in the web form (text, optional service, optional time window) and an investigation starts immediately.
- **US-8** As an engineer, I type `/forgeops investigate <description>` in Slack and get a link to the live War Room.
- **US-9** As an engineer, I watch the War Room: the Supervisor plans, agents work at their desks, tool calls appear as speech bubbles, evidence cards are pinned to the board.
- **US-10** As an engineer, I see which agents were skipped and why (not relevant, or tool not connected).
- **US-11** As an engineer, I open any evidence card and see the exact source: commit link, Sentry issue link, PromQL/LogQL query, log excerpt.

### Deciding
- **US-12** As an engineer, I read the RCA: root cause, confidence, supporting and contradicting evidence, alternative hypotheses, what could not be checked.
- **US-13** As an engineer, I approve or reject each proposed action, or send the investigation back with a note ("also check the Redis change").
- **US-14** As an engineer, I can approve/reject from Slack buttons.
- **US-15** As an engineer, after approval, a GitHub issue is created with the RCA and evidence links, and a postmortem report is generated.
- **US-16** As an admin, I see an audit log of every approval, rejection and write action (who, when, what).

### History
- **US-17** As an engineer, I see a list of past investigations with status, service, root cause and duration, and can reopen any War Room as a replay.

## 7. Key product behaviors

1. **Real data only.** If a tool is not connected or a call fails, ForgeOps says so; it never fills gaps with invented data.
2. **Graceful partial coverage.** With only Sentry + GitHub connected, a frontend error investigation still completes; the RCA lists "metrics/logs not connected" under missing information.
3. **Evidence is traceable.** Every finding links to the tool calls that produced it.
4. **Honest confidence.** RCA confidence is capped when it cites little or conflicting evidence.
5. **Human in the loop.** Investigating agents hold read-only tools. Write tools exist only in the Action step, only after a recorded approval.
6. **Live and truthful UI.** War Room animation is driven only by backend events; refreshing the page replays the same state.

## 8. Testing path (owner-driven)

The product owner tests incrementally. The MVP must support each step without code changes, only by connecting more tools:

| Step | Connected | Example incident on the sample SaaS |
|---|---|---|
| 1 | GitHub + Sentry | "Checkout button throws an error on the website" (frontend JS error) |
| 2 | + GitHub Actions | "Errors started after the last deploy" |
| 3 | + Prometheus | "Checkout API latency is high" |
| 4 | + Loki | "Orders failing with 500s" |
| 5 | + Knowledge vault | Any of the above, with runbook guidance |
| 6 | + Slack | Start from Slack, approve from Slack |

## 9. Success metrics (MVP)

| Metric | Target |
|---|---|
| RCA correct on sample-SaaS fault scenarios (root cause matches known cause) | ≥ 4 of 5 scenarios with all tools connected |
| Time from incident submit to RCA | < 5 minutes (p50) |
| Evidence claims with a traceable tool call | 100% |
| Writes executed without approval | 0 |
| War Room events matching backend events after refresh | 100% |

## 10. Credentials the user provides

| Account | Needed at | Items |
|---|---|---|
| OpenRouter | Engine milestone | API key with spending limit |
| GitHub | Connector milestone | Fine-grained token (Contents/PRs/Actions read, Issues read+write) on the sample repo; empty sample repo; self-hosted runner registration |
| Sentry | Connector milestone | Organization; 2 projects (web, api); DSNs; auth token with read scopes |
| Slack | Slack milestone | Workspace; app from provided manifest; bot token, app token, channel ID |

All secrets live in `.env` (git-ignored) or are entered on the Connections page and stored encrypted.

## 11. Risks

| Risk | Mitigation |
|---|---|
| LLM makes unsupported claims | Evidence citations required; confidence caps; RCA prompt forbids uncited claims |
| Prompt injection via logs/commit messages | Tool output treated as data; investigating agents are read-only; writes need human approval with visible parameters |
| Third-party MCP server risk | Only the official GitHub MCP server, pinned version, read-only mode; others use direct HTTP clients |
| API rate limits / cost | Per-agent tool-call budget, timeouts, result truncation, OpenRouter spend limit |
| Free-tier limits (Sentry, OpenRouter) | Document limits; degrade gracefully |

## 12. Release definition (MVP done)

Given the incident "Checkout API latency increased after the last deployment" on the sample SaaS with all MVP tools connected, ForgeOps: creates an investigation, plans, runs relevant specialists concurrently against real tools, writes evidence to shared state, runs RCA with supporting evidence, confidence and uncertainty, requests approval (web or Slack), creates a GitHub issue and report on approval, and shows every real execution event in the War Room.
