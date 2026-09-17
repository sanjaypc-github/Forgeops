# ForgeOps / EOPS — Project Specification for Claude Code

## 1. Purpose

Build **ForgeOps (Engineering Operations Platform / EOPS)** from scratch as a real multi-agent engineering incident investigation platform.

**Current status: NOT IMPLEMENTED.** Do not assume an MVP already exists. This document is the implementation baseline.

The product goal is to help software engineers investigate incidents across code, observability, deployments, infrastructure, databases, engineering knowledge, and incident history, then produce an evidence-based root-cause analysis with human approval before actions.

---

## 2. Core problem

Engineering incident investigation is fragmented across:
- source repositories;
- commits and pull requests;
- application logs;
- metrics and monitoring;
- traces;
- deployment history;
- infrastructure;
- databases;
- runbooks and architecture documentation;
- previous incidents and team discussions.

ForgeOps should unify these sources into one investigation workflow so multiple specialist AI agents can collect evidence concurrently and a dedicated RCA agent can correlate the evidence.

The project’s research framing is a **supervisor-driven multi-agent architecture** with concurrent evidence collection, centralized shared state, RAG-based engineering memory, and explicit human oversight. This is consistent with the existing EOPS paper. fileciteturn8file0L10-L21

---

## 3. Product flow

Example incident:

> “Checkout API latency increased immediately after yesterday’s deployment.”

Expected flow:

1. Engineer submits incident.
2. Supervisor understands the incident.
3. Supervisor creates an investigation plan.
4. Relevant specialist agents are selected.
5. Independent investigations run concurrently.
6. Agents write structured evidence into shared investigation state.
7. RCA Agent correlates evidence.
8. Recommendation is generated.
9. Human reviews/approves/rejects.
10. Action Agent performs only approved write/execute operations.
11. Final report/postmortem is generated.
12. Useful incident knowledge can be stored for future investigations.

The paper’s current methodology already specifies incident initialization, planning, parallel evidence collection, and collaborative RCA reasoning. fileciteturn8file0L56-L92

---

# 4. Final agent architecture: 10 core agents

Do **not** create one agent for every external product.

Use 10 stable specialist roles. External integrations are dynamic capabilities assigned to these agents.

### 1. Supervisor / Director Agent

Responsible for:
- understanding incidents;
- planning investigations;
- selecting relevant specialist agents/capabilities;
- coordinating concurrent work;
- tracking progress;
- deciding when sufficient evidence exists;
- invoking RCA.

Implementation:
- LangGraph;
- LLM-based planning;
- shared investigation state.

The existing EOPS architecture explicitly defines the supervisor as the planning and coordination component. fileciteturn8file0L10-L21

### 2. Code Agent

Investigates:
- repositories;
- recent commits;
- pull requests;
- changed files;
- relevant source code;
- suspicious code changes.

Initial connector:
- GitHub.

Future:
- GitLab;
- Bitbucket.

### 3. Observability Agent

Combine logs + metrics + traces under one agent to prevent agent explosion.

Investigates:
- errors;
- warnings;
- exceptions;
- latency;
- throughput;
- error rates;
- anomalies;
- trace/span failures;
- service dependencies.

Possible connectors:
- Prometheus;
- Grafana;
- Loki;
- Tempo;
- Jaeger;
- Datadog;
- New Relic;
- CloudWatch.

Initial implementation:
- local/simulated logs;
- Prometheus where practical.

### 4. Deployment Agent

Investigates:
- recent deployments;
- versions/releases;
- deployment timing;
- CI/CD execution;
- commit-to-deployment relationships.

Possible connectors:
- GitHub Actions;
- GitLab CI;
- Jenkins;
- Argo CD.

Initial implementation:
- GitHub Actions/repository workflow data.

### 5. Infrastructure Agent

Investigates:
- Kubernetes pods;
- nodes;
- containers;
- resource pressure;
- restarts;
- infrastructure failures.

Possible connectors:
- Kubernetes;
- Docker;
- AWS;
- Azure;
- GCP.

### 6. Database Agent

Investigates:
- database errors;
- connection pool exhaustion;
- slow queries;
- locks;
- saturation;
- database-related application failures.

Possible connectors:
- PostgreSQL;
- MySQL;
- MongoDB;
- Redis;
- cloud database monitoring.

### 7. Knowledge Agent

Investigates organizational knowledge:
- runbooks;
- troubleshooting guides;
- architecture docs;
- previous technical knowledge.

Knowledge architecture:
- Obsidian/Markdown;
- Markdown parsing;
- chunking;
- embeddings;
- ChromaDB;
- semantic + BM25 hybrid retrieval.

Important:
- Obsidian is the human-facing documentation source.
- ChromaDB is the retrieval store.
- GraphRAG is a future extension, not required for the initial implementation.

The existing EOPS paper specifies Obsidian/Markdown preprocessing into embeddings stored in Chroma, with graph-augmented retrieval treated as future work. fileciteturn8file0L35-L47

### 8. Incident Agent

Investigates historical/contextual engineering information:
- similar incidents;
- previous resolutions;
- tickets;
- incident records;
- team discussions.

Possible connectors:
- Jira;
- PagerDuty;
- ServiceNow;
- Slack;
- Linear;
- previous postmortems.

### 9. RCA Agent

Consumes structured evidence from shared state and produces:
- root-cause hypothesis;
- supporting evidence;
- confidence;
- contradictions;
- uncertainty;
- missing information;
- recommended remediation.

The existing paper defines the RCA component as the final reasoning stage that aggregates specialist evidence and presents the result for human acceptance. fileciteturn8file0L48-L54

RCA Agent should not independently perform broad evidence collection.

### 10. Action Agent

Handles:
- remediation recommendations;
- issue/ticket creation;
- report/postmortem generation;
- approved remediation execution.

Early builds should keep write/execute functionality disabled or read-only.

---

# 5. Agent vs connector model

The architecture must NOT become:

```text
GitHub Agent
Jira Agent
Slack Agent
Prometheus Agent
Kubernetes Agent
...
```

Instead:

```text
10 Core Agents
      +
Dynamic Connectors
      +
Capability Registry
```

Example:

```text
Code Agent
 ├── GitHub
 ├── GitLab
 └── Bitbucket

Observability Agent
 ├── Prometheus
 ├── Grafana
 ├── Loki
 ├── Tempo
 └── Datadog

Incident Agent
 ├── Jira
 ├── PagerDuty
 └── Slack

Infrastructure Agent
 ├── Kubernetes
 ├── Docker
 └── Cloud
```

A customer may connect 3 tools or 10 tools without changing the agent architecture.

---

# 6. MCP strategy

MCP is the external tool connectivity layer, not the orchestration framework.

Preferred conceptual model:

```text
Agent LLM
   ↓
Agent
   ↓
LangGraph
   ↓
Tool interface
   ↓
MCP Client OR native Python service
   ↓
External system
```

Use MCP where a reliable MCP server is available and appropriate.

Use native Python/service integrations for internal components such as:
- RAG;
- Chroma retrieval;
- Markdown parsing;
- evidence normalization;
- investigation state utilities;
- report generation.

Do not force MCP onto every internal function.

Do not blindly trust third-party MCP servers. Validate them, scope credentials, and prefer read-only access.

---

# 7. Customer onboarding

Customers configure **connections**, not agents.

Example:

```text
Connect your engineering stack

Code
  GitHub ✓

Observability
  Prometheus ✓
  Loki +

Incident Management
  Jira ✓

Collaboration
  Slack +

Infrastructure
  Kubernetes +
```

After connection:
1. authenticate;
2. validate connection;
3. discover capabilities;
4. apply permission policy;
5. register capabilities;
6. map capabilities to agents.

---

# 8. Permission model

Use least privilege.

Default for the initial product:
- GitHub: read-only;
- Prometheus: read-only;
- Loki: read-only;
- Jira: read-only;
- Slack: read-only;
- Kubernetes: read-only.

Write and execute permissions must:
- be explicitly enabled;
- be clearly visible;
- be separated from read permissions;
- require human approval;
- be disabled by default in the initial implementation.

Example:

```text
GitHub
 ✓ read commits
 ✓ read pull requests
 ✓ read files
 ✓ read issues
 ✗ merge pull request
 ✗ push code
```

```text
Kubernetes
 ✓ read pods
 ✓ read events
 ✓ read deployments
 ✗ restart pod
 ✗ scale deployment
 ✗ delete pod
```

---

# 9. Human-in-the-loop

ForgeOps is a decision-support platform first.

AI may investigate and recommend.

AI must not silently:
- merge production code;
- deploy;
- delete infrastructure;
- restart production services;
- modify production databases;
- execute destructive operations.

Required path:

```text
RCA
 ↓
Recommendation
 ↓
Human Approval
 ↓
Action Agent
 ↓
Write / Execute
```

The existing EOPS paper explicitly describes the platform as a decision-support system with an approval stage. fileciteturn8file4L401-L409

---

# 10. Shared investigation state

All agents must communicate through a structured shared state.

Illustrative shape:

```python
class InvestigationState(TypedDict):
    investigation_id: str
    incident: dict
    plan: dict

    code_evidence: list
    observability_evidence: list
    deployment_evidence: list
    infrastructure_evidence: list
    database_evidence: list
    knowledge_evidence: list
    incident_evidence: list

    hypotheses: list
    rca: dict
    recommendations: list

    approval_status: str
    action_results: list

    errors: list
    warnings: list
    events: list
```

Specialist agents contribute structured evidence.

The RCA Agent consumes that evidence and creates the final reasoning output.

---

# 11. Evidence contract

All tool/agent results should be structured.

Example:

```json
{
  "source": "github",
  "agent": "code_agent",
  "finding": "Database pool configuration changed",
  "evidence": [
    {
      "type": "commit",
      "id": "abc123",
      "timestamp": "..."
    }
  ],
  "severity": "high",
  "confidence": 0.87
}
```

Every evidence object should preserve:
- source;
- finding;
- evidence;
- timestamp where applicable;
- confidence;
- uncertainty/limitations.

---

# 12. Real-time execution events

The frontend must visualize actual backend events.

Canonical events:

```text
investigation_started
supervisor_started
agent_started
tool_called
tool_completed
evidence_added
agent_failed
agent_completed
rca_started
rca_completed
approval_requested
approval_granted
approval_rejected
action_started
action_completed
investigation_completed
```

Do not create fake "agent working" animations that are disconnected from backend execution.

---

# 13. Frontend concept: Engineering War Room

The frontend should feel like a modern engineering office/war room where specialist AI workers collaborate on a live incident.

The concept is **inspired by an office-style agent visualization**, but all visual design, layouts, assets, naming, and interactions must be original to ForgeOps.

Do not copy Munder Difflin assets, branding, characters, or proprietary UI details.

## Main visual zones

- incident intake/header;
- Supervisor station;
- specialist desks/stations;
- shared investigation board;
- live evidence feed;
- RCA station;
- human approval station.

## Example visual state

```text
                 INCIDENT
                    │
              SUPERVISOR
                    │
       ┌────────────┼────────────┐
       ↓            ↓            ↓
     CODE     OBSERVABILITY   DEPLOYMENT
      🧑‍💻         📊             🚀
       │            │            │
       └────────────┼────────────┘
                    ↓
          SHARED INVESTIGATION
                  BOARD
                    ↓
                  RCA
                    ↓
             HUMAN APPROVAL
```

Use CSS/SVG first. Do not introduce Pixi.js or another heavy graphics engine unless it is actually needed.

Use WebSocket/SSE so the frontend reacts to real execution events.

---

# 14. Backend / frontend stack

## Frontend
- React
- TypeScript
- responsive UI
- component-based structure
- WebSocket or SSE for investigation events

## Backend
- Python
- FastAPI
- LangGraph
- Pydantic
- asynchronous execution
- structured logging

## AI
Make LLM provider configurable through environment/configuration.

Possible providers:
- OpenAI;
- Anthropic;
- Google;
- OpenRouter;
- compatible model providers.

Do not hard-code one provider into the whole codebase.

## RAG
- Markdown;
- Obsidian;
- embeddings;
- ChromaDB;
- BM25;
- hybrid retrieval.

---

# 15. Suggested repository structure

```text
forgeops/
│
├── backend/
│   ├── api/
│   ├── agents/
│   ├── graph/
│   ├── state/
│   ├── connectors/
│   ├── tools/
│   ├── services/
│   ├── models/
│   ├── config/
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── features/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── war-room/
│   └── tests/
│
├── knowledge/
│   ├── vault/
│   ├── ingestion/
│   ├── retrieval/
│   └── indexing/
│
├── docs/
│   ├── PROJECT_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── API_CONTRACT.md
│   ├── STATE_CONTRACT.md
│   ├── TOOL_CONTRACT.md
│   └── CONNECTOR_GUIDE.md
│
├── scripts/
├── .env.example
├── docker-compose.yml
└── README.md
```

---

# 16. Implementation sequence

## Stage 0 — Foundation
Build:
- repository structure;
- FastAPI shell;
- React shell;
- shared schemas;
- investigation state;
- graph skeleton;
- event system;
- configuration;
- test structure.

## Stage 1 — Core agent workflow
Build:
- Supervisor;
- Code;
- Observability;
- Deployment;
- Knowledge;
- RCA;
- shared state;
- parallel execution;
- live event stream;
- War Room UI.

Mock connectors where necessary.

## Stage 2 — Real integrations
Prioritize:
1. GitHub;
2. Prometheus;
3. Knowledge/RAG;
4. GitHub Actions;
5. local logs.

Then:
6. Jira;
7. Slack;
8. Kubernetes;
9. Loki;
10. tracing.

## Stage 3 — Connection management
Build:
- connections page;
- credential/configuration flow;
- health checks;
- capability discovery;
- capability registry;
- permission policy;
- workspace-level connection configuration.

## Stage 4 — Action controls
Build:
- approval gate;
- ticket creation;
- report generation;
- audit trail;
- safe remediation abstraction.

---

# 17. Harness decision

Do **not** add Munder Difflin or another external agentic harness as a mandatory runtime dependency.

Use:
- LangGraph for orchestration;
- MCP/native tools for connectivity;
- your own War Room UI for agent visualization.

A future agent-runtime/harness layer may be added for:
- execution observability;
- cost tracking;
- retries/timeouts;
- evaluation;
- sandboxing;
- large-scale agent management.

It is not required for the first build.

---

# 18. Definition of first complete working build

Given:

```text
"Checkout API latency increased after deployment."
```

the platform should:

1. create an investigation;
2. activate the Supervisor;
3. plan the investigation;
4. run relevant specialists concurrently;
5. inspect connected evidence sources;
6. write findings to shared state;
7. run RCA;
8. show supporting evidence;
9. generate confidence + uncertainty;
10. produce recommendations;
11. request human approval;
12. optionally create a ticket/report;
13. show all real execution events in the War Room.

This is the primary end-to-end target.

---

# 19. Development rules for Claude Code

Before changing code:
- inspect the repository;
- preserve working code;
- check current dependencies;
- keep agent and connector logic separate.

During implementation:
- use interfaces/contracts;
- use Pydantic models;
- keep credentials out of source code;
- use environment variables;
- prefer asynchronous execution for independent work;
- emit structured events;
- write tests;
- use mocks when integrations are unavailable;
- document setup;
- never pretend a mock is a real integration;
- keep production writes disabled by default.

The intended architecture prioritizes modularity, concurrent specialist investigation, and centralized evidence sharing. fileciteturn8file1L102-L147
