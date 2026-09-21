# ForgeOps — Product Requirements Document (MVP)

| | |
|---|---|
| Product | ForgeOps (Engineering Operations Platform, EOPS) |
| Document | PRD v2, MVP scope |
| Status | Draft for review |
| Date | 2026-09-21 |
| Companion | [TRD.md](TRD.md) (technical design), [reference/PROJECT_SPEC.md](reference/PROJECT_SPEC.md) (original vision) |

> v2 replaces v1. Changes: agents grouped by system area (not by vendor), a Claude-style connector catalog where every external connector is an MCP server, agents that ask each other questions, a chat bar that starts investigations, and testing on a real customer website instead of a sample app.

---

## 1. Summary

ForgeOps is a SaaS product that finds the root cause of a production problem in **10–20 minutes instead of 2–3 hours**.

A SaaS founder or engineering team connects the tools their product runs on (GitHub, Cloudflare, Vercel, Supabase, Sentry, Sanity, AWS, …) from a **connector catalog**, the same way connectors are added in Claude. Each connector is an **MCP server** that gives ForgeOps' AI agents read access to that tool.

When something breaks, the user pastes the symptom into the **chat bar** ("the site is very slow and sometimes shows a warning"). A **Supervisor** agent splits the work across **specialist agents**, one per area of the system. They investigate **in parallel**, each through its own connectors, and **ask each other questions** when they need information from another area. An **RCA** step combines their findings into:

- the **root cause** (why it happened),
- the **exact point of failure** (commit, file, deploy, query, config, content change),
- the **evidence** (links to the real commits, logs, errors and deploys behind every claim),
- the **confidence** and what could not be checked.

Everything is shown live in the **War Room**: a 2D office where each agent sits at a desk and walks to another agent's desk when they talk.

## 2. Problem

When a SaaS product breaks, someone has to open GitHub, the hosting dashboard, the database console, the error tracker and the docs, and correlate them by hand. This takes a developer 2–3 hours, and small companies often have no one on call who knows every part of the stack. Hiring a debugger or waiting for the one engineer who knows the system is slow and expensive.

## 3. Target users

| Persona | Situation | What ForgeOps gives them |
|---|---|---|
| **SaaS founder / CTO** (primary) | Small team, no dedicated DevOps/SRE, product built on managed services | A "virtual SRE team": connect tools once, get an evidence-backed root cause in minutes |
| **B2B engineering team** | Several services and tools, on-call rotation | The first hours of investigation done automatically, across every tool at once |
| **Engineering lead** | Needs control over what AI can access | Read-only by default, human approval for every write, audit trail |

## 4. Goals and non-goals

### Goals (MVP)
1. A user connects their stack from a connector catalog; each connector shows what it can read and whether it can write.
2. A user pastes a problem into the chat bar and gets a root cause with exact failure point and evidence in **under 20 minutes** (target p50 under 10).
3. Agents investigate real tools only, in parallel, and ask each other questions.
4. The War Room office shows real agent work live, including agents walking to each other's desks.
5. ForgeOps works with any subset of connectors and says clearly what it could not check.
6. No write to any external system happens without explicit human approval.
7. The data model is multi-company ready (workspaces); the MVP UI exposes one workspace.

### Non-goals (MVP)
- Sign-up, billing, multiple workspaces in the UI, team roles beyond admin.
- OAuth "Sign in with …" connector flows (MVP uses API tokens; OAuth comes with multi-company SaaS).
- Automatic remediation (rollbacks, restarts, merges). The only MVP write is creating a GitHub issue after approval.
- Hosting decisions for ForgeOps itself (decided later).
- Kubernetes, Prometheus, Datadog, AWS, Jira, PagerDuty connectors (they appear in the catalog as "coming soon"; the design supports them without agent changes).

## 5. Agents

Agents are fixed roles grouped by **area of the system**. The same agents exist for every customer; only their connectors differ.

| Desk | Agent | Investigates | Example connectors |
|---|---|---|---|
| Supervisor | **Supervisor** | Understands the problem, plans, assigns tasks, decides when evidence is enough | none |
| Code | **Code** | What changed in the code: commits, diffs, pull requests | GitHub, GitLab, Bitbucket |
| Frontend & Hosting | **Frontend & Hosting** | Site deploys, build logs, CDN/edge, domains, SSL, edge functions | Cloudflare, Vercel, Netlify, Hostinger, Firebase Hosting, AWS Amplify |
| Backend & Services | **Backend & Services** | APIs, serverless functions, auth, CMS, containers | Supabase (functions, auth), Firebase, Sanity, Contentful, AWS Lambda/ECS, Render, Railway, Kubernetes |
| Database | **Database** | Slow queries, connection limits, locks, schema/migration changes | Supabase Postgres, PostgreSQL, MySQL, MongoDB Atlas, Firestore, Redis |
| Observability | **Observability** | Errors, stack traces, logs, metrics, traces | Sentry, Datadog, Prometheus, Grafana/Loki, New Relic, CloudWatch |
| Knowledge | **Knowledge** | Runbooks, architecture docs, past incidents | Obsidian/Markdown vault, Notion, Confluence |
| RCA | **RCA** | Combines all evidence into root cause, failure point, confidence | none (reads findings) |
| Action | **Action** | After approval: issue, report, message | GitHub Issues (MVP); Jira, Slack later |

One connector can serve several agents. Connecting Supabase once gives its database abilities to **Database**, its functions and auth to **Backend & Services**, and its logs to **Observability**.

## 6. Connectors

### 6.1 Connector catalog (MVP)

| Connector | Status in MVP | Serves |
|---|---|---|
| GitHub | Available | Code; Frontend & Hosting (Actions); Action (issues) |
| Cloudflare | Available | Frontend & Hosting; Backend & Services (Workers); Observability (logs, analytics) |
| Supabase | Available | Database; Backend & Services; Observability (logs) |
| Sanity | Available | Backend & Services (content changes) |
| Sentry | Available | Observability |
| Knowledge vault (Obsidian/Markdown) | Available | Knowledge |
| Vercel, Netlify, GitLab, Firebase, MongoDB Atlas, Datadog, Prometheus, AWS, Notion, Jira, Slack | Coming soon | shown in catalog, not connectable |

The first six match the owner's own website (GitHub + Cloudflare + Supabase + Sanity, with Sentry being added), which is the first real test customer.

### 6.2 Connector behavior
- Each connector is an MCP server (official server where one exists). The Knowledge vault is ForgeOps' own search and does not need MCP.
- Connecting asks for the tool's API token (and project/account ID where needed), tests it, and lists the abilities found.
- Every ability is labelled **read** or **write**. Only read abilities are used while investigating. Write abilities are off by default and used only by the Action agent after approval.

## 7. User experience

### 7.1 Screens
- **Sign in**
- **War Room** (home): the office, with the **chat bar** on the side
- **Connectors**: catalog grouped by agent, with connect/test/disconnect and read/write abilities
- **Investigations**: history with status, root cause and duration; any can be replayed in the office
- **Report**: root cause, failure point, evidence, timeline, recommendations

### 7.2 The office
- A top-down 2D office floor. Each agent is a character at a labelled desk; desks without a connected connector show "no connector".
- When the Supervisor assigns tasks, task cards travel to the chosen desks.
- Working agents type; a speech bubble shows the real tool call ("Supabase: slow queries, last 1 h").
- When an agent **asks another agent**, it walks to that agent's desk; both show the question and the answer; then it walks back.
- Findings are pinned to a shared **evidence wall**.
- The RCA analyst collects the pinned cards and writes the root cause on a board.
- Every movement is triggered by a real backend event. Refreshing the page replays the same state.

### 7.3 The chat bar
- The user types or pastes a problem ("site slow, sometimes a warning" + an error message or URL) and presses Enter: an investigation starts.
- The Supervisor replies in the chat with its plan and progress summaries.
- When the RCA is ready, the chat shows it with links to the evidence, plus buttons: **Approve actions**, **Reject**, **Investigate more**.
- After the RCA, the user can ask follow-up questions ("why do you think it's the deploy and not the database?"). The Supervisor answers from the collected evidence, or sends agents back to check.

## 8. User stories

### Setup
- **US-1** As an admin, I sign in with email and password.
- **US-2** As an admin, I open the connector catalog, grouped by agent, and see which connectors are available or coming soon.
- **US-3** As an admin, I connect a tool by entering its API token (and project ID when needed); ForgeOps tests it and shows the abilities it found, each labelled read or write.
- **US-4** As an admin, I see which agents each connector powers and which desks have no connector.
- **US-5** As an admin, I point ForgeOps at my knowledge vault (Obsidian folder or Markdown in a repo) and see how many documents are indexed.
- **US-6** As an admin, I describe my product's services once (name, repo, hosting project, database project) so agents know where to look.

### Investigating
- **US-7** As a user, I paste a problem into the chat bar and an investigation starts immediately.
- **US-8** As a user, I watch the office: the Supervisor plans, agents work at their desks, walk to each other to ask questions, and pin findings to the evidence wall.
- **US-9** As a user, I see which agents were skipped and why (not relevant, or no connector).
- **US-10** As a user, I open any evidence card and see its exact source (commit link, deploy ID, log lines, query, Sentry issue).
- **US-11** As a user, I read each agent-to-agent question and answer in the event feed.

### Deciding
- **US-12** As a user, I read the RCA: root cause, exact failure point, confidence, supporting and contradicting evidence, what could not be checked.
- **US-13** As a user, I approve or reject proposed actions, or ask for more investigation with a note.
- **US-14** As a user, on approval a GitHub issue is created with the RCA and evidence links, and a report is generated.
- **US-15** As a user, I ask follow-up questions in the chat after the RCA.
- **US-16** As an admin, I see an audit log of approvals, rejections and write actions.

### History
- **US-17** As a user, I see past investigations and replay any of them in the office.

## 9. Key product behaviors

1. **Real data only.** No invented data. If a connector is missing or a call fails, ForgeOps says so.
2. **Partial coverage is fine.** With only GitHub + Sentry connected, an investigation still completes and lists what it could not check.
3. **Every claim is traceable** to the tool calls that produced it.
4. **Honest confidence.** Confidence is capped when evidence is thin or contradictory.
5. **Human in the loop.** Investigating agents only read. Writes need a recorded approval.
6. **Truthful office.** Animation only follows real backend events.
7. **Bounded cost and time.** Each agent and each investigation has limits on tool calls, agent-to-agent questions, time and LLM spend.

## 10. Testing with a real website

The first test customer is the owner's own website (Cloudflare + GitHub + Supabase + Sanity, with Sentry being added).

| Step | Connected | Deliberate problem (on a preview branch) | Expected finding |
|---|---|---|---|
| 1 | GitHub + Sentry | JavaScript error in a page component | Commit + file + line from the stack trace |
| 2 | + Cloudflare | Broken build or bad redirect/header rule | Failing deploy or config change |
| 3 | + Supabase | Slow query (missing index) or wrong row-level security policy | Query/policy + the migration commit |
| 4 | + Sanity | Published content missing a required field that the site reads | Content change + the code path that breaks |
| 5 | + Knowledge vault | Any of the above | Matching runbook cited |

A **preview** is a separate copy of the site that Cloudflare builds automatically when a non-`main` branch is pushed; the live site is untouched. Each test uses a branch like `forgeops-test-1` with one deliberate bug, visited a few times so the tools record errors.

## 11. Success metrics (MVP)

| Metric | Target |
|---|---|
| Correct root cause on the test scenarios (§10) with relevant connectors connected | ≥ 4 of 5 |
| Time from chat message to RCA | p50 < 10 min, p95 < 20 min |
| Evidence claims with a traceable tool call | 100% |
| Writes executed without approval | 0 |
| Office animations matching backend events after refresh | 100% |

## 12. Credentials the owner provides

| Account | Needed at | Items |
|---|---|---|
| OpenRouter | Engine milestone | API key with a spending limit |
| Supabase (for ForgeOps' own data) | Now | A new, separate Supabase project for ForgeOps; its Postgres connection string |
| GitHub | Connector milestone | Fine-grained token, read access to the website repo (Issues write for the Action agent) |
| Sentry | Connector milestone | Auth token with read scopes, organization and project |
| Cloudflare | Connector milestone | API token with read permissions, account ID |
| Supabase (website's project) | Connector milestone | Personal access token, project ref |
| Sanity | Connector milestone | Read token, project ID, dataset |

Secrets live in `.env` (git-ignored) or are entered on the Connectors page and stored encrypted.

## 13. Risks

| Risk | Mitigation |
|---|---|
| The needed signal isn't recorded (e.g. browser errors without a tracker) | Report "not visible" honestly; recommend the connector that would reveal it |
| Short log retention on free plans | Investigate soon after the problem; show the retention window as a limitation |
| LLM makes unsupported claims | Citations required; confidence caps |
| Prompt injection through logs, commit messages or content | Tool output treated as data; investigating agents cannot write |
| Third-party MCP server risk | Official servers only, pinned versions, read-only modes and a per-connector allowlist of tools |
| Agents asking each other in loops | Limits on questions per agent and per investigation; no nested questions |
| API rate limits / LLM cost | Per-agent budgets, timeouts, result truncation, OpenRouter spend limit |

## 14. Release definition (MVP done)

Given a deliberate bug on a preview of the owner's website and the symptom pasted into the chat bar, with GitHub, Cloudflare, Supabase, Sanity, Sentry and the knowledge vault connected, ForgeOps plans, runs the relevant agents in parallel against the real tools, shows at least one real agent-to-agent question in the office, produces an RCA naming the root cause and exact failure point with evidence and confidence, asks for approval, creates a GitHub issue and report on approval, and every step is visible live in the War Room.
