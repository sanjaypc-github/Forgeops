# ForgeOps (EOPS — Engineering Operations Platform)

ForgeOps investigates software incidents for engineering teams. A company connects the tools it already uses (GitHub, Sentry, Prometheus, Loki, its runbooks). When something breaks, a **Supervisor** agent plans the investigation, **specialist agents** collect evidence from those tools in parallel, an **RCA agent** correlates the evidence into a root cause with confidence and citations, and a **human approves** any action before it happens.

Everything is shown live in the **War Room**: a top-down office where each agent works at its own desk, driven only by real backend events.

> **Status:** MVP in development. See the milestones in [docs/TRD.md](docs/TRD.md#17-milestones).

## How it works

```text
Incident (web form or Slack)
        │
        ▼
   Supervisor ── plans, picks agents whose tools are connected
        │
   ┌────┼──────────────┬──────────────┐       (in parallel)
   ▼    ▼              ▼              ▼
 Code  Deployment  Observability  Knowledge
 GitHub GitHub      Sentry         Markdown vault
        Actions     Prometheus     (ChromaDB + BM25)
                    Loki
   └────┴──────────────┴──────────────┘
                   │  structured evidence → shared state
                   ▼
                  RCA ── root cause, confidence, evidence, gaps
                   │
                   ▼
            Human approval (web or Slack)
                   │
                   ▼
          Action ── GitHub issue + postmortem report
```

Principles:
- **Real data only.** No mock data at runtime; every finding links to the real tool call behind it.
- **Works with any subset of tools.** Missing tools are reported as missing information, never invented.
- **Read-only by default.** Write tools exist only after a recorded human approval.
- **10 fixed agent roles + pluggable connectors.** New platforms are added as connectors, not new agents.

## Stack

| Part | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, LangGraph, Pydantic, SQLAlchemy, PostgreSQL |
| LLM | OpenRouter (model configurable per agent role) |
| Tools | Official GitHub MCP server; HTTP clients for Sentry, Prometheus, Loki |
| Knowledge | Markdown/Obsidian vault, ChromaDB, BM25 hybrid retrieval |
| Frontend | React, TypeScript, Vite; SVG/CSS War Room |
| Integrations | Slack (Socket Mode) |

## Repository layout

```text
Forgeops/
├── backend/          FastAPI app, LangGraph engine, agents, connectors, knowledge
├── frontend/         React War Room
├── sample-saas/      A real sample shop used as the system under test
├── knowledge-vault/  Starter runbooks and service docs
├── scripts/          Setup and evaluation
└── docs/             PRD, TRD, original spec and diagrams
```

## Documents

- [Product requirements (PRD)](docs/PRD.md)
- [Technical requirements (TRD)](docs/TRD.md) — architecture, flow diagrams, contracts, milestones
- [Original project spec](docs/reference/PROJECT_SPEC.md) and [architecture diagrams](docs/reference/ARCHITECTURE_DIAGRAMS.md)

Setup instructions will be added with milestone M0.
