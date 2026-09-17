# ForgeOps / EOPS — Canonical Architecture Diagrams

**Implementation status: NOT STARTED.** These diagrams describe the target architecture that Claude Code should build.

---

# 1. System context

```mermaid
flowchart TB
    Engineer[Software Engineer]
    UI[ForgeOps Engineering War Room]
    API[FastAPI Application Layer]
    LG[LangGraph Orchestration]
    Tools[Tool / Capability Layer]
    External[Customer Engineering Systems]
    Memory[Engineering Memory<br/>Obsidian / Markdown + Chroma]

    Engineer --> UI
    UI --> API
    API --> LG
    LG --> Tools
    Tools --> External
    LG --> Memory
```

---

# 2. Layered architecture

```mermaid
flowchart TB
    P[Presentation Layer<br/>React + Engineering War Room]
    A[Application Layer<br/>FastAPI + Auth + Investigation Lifecycle]
    O[Multi-Agent Orchestration Layer<br/>LangGraph + Supervisor + Shared State]
    AG[Agent Layer<br/>10 Core Agents]
    T[Tool / Capability Layer<br/>MCP + Native Python Tools]
    C[Connector Layer<br/>External Integrations]
    E[External Engineering Systems]
    M[Engineering Memory Layer<br/>Obsidian + RAG + Chroma]
    H[Human Approval Layer]

    P --> A
    A --> O
    O --> AG
    AG --> T
    T --> C
    C --> E

    AG --> M
    O --> H
    H --> A
```

---

# 3. Ten-agent architecture

```mermaid
flowchart TB
    INCIDENT[Incident Request]
    SUP[Supervisor / Director Agent]

    CODE[Code Agent]
    OBS[Observability Agent]
    DEP[Deployment Agent]
    INFRA[Infrastructure Agent]
    DB[Database Agent]
    KNOW[Knowledge Agent]
    INC[Incident Agent]

    STATE[(Shared Investigation State)]

    RCA[RCA Agent]
    ACTION[Action Agent]
    HUMAN[Human Approval]

    INCIDENT --> SUP

    SUP --> CODE
    SUP --> OBS
    SUP --> DEP
    SUP --> INFRA
    SUP --> DB
    SUP --> KNOW
    SUP --> INC

    CODE --> STATE
    OBS --> STATE
    DEP --> STATE
    INFRA --> STATE
    DB --> STATE
    KNOW --> STATE
    INC --> STATE

    STATE --> RCA
    RCA --> ACTION
    ACTION --> HUMAN
```

---

# 4. Parallel investigation

```mermaid
flowchart LR
    I[Incident]
    S[Supervisor]

    C[Code Agent]
    O[Observability Agent]
    D[Deployment Agent]
    K[Knowledge Agent]

    STATE[(Shared Investigation State)]
    R[RCA Agent]

    I --> S
    S --> C
    S --> O
    S --> D
    S --> K

    C --> STATE
    O --> STATE
    D --> STATE
    K --> STATE

    STATE --> R
```

Independent specialist investigations should execute concurrently.

---

# 5. Agent-to-capability model

```mermaid
flowchart TB

    CODE[Code Agent]
    OBS[Observability Agent]
    DEP[Deployment Agent]
    INFRA[Infrastructure Agent]
    DB[Database Agent]
    KNOW[Knowledge Agent]
    INC[Incident Agent]
    ACTION[Action Agent]

    GH[GitHub]
    GL[GitLab]
    BB[Bitbucket]

    PROM[Prometheus]
    GRAF[Grafana]
    LOKI[Loki]
    TEMPO[Tempo / Jaeger]
    DD[Datadog]

    GHA[GitHub Actions]
    JEN[Jenkins]
    ARGO[Argo CD]

    K8S[Kubernetes]
    DOCKER[Docker]
    CLOUD[AWS / Azure / GCP]

    PG[PostgreSQL]
    MYSQL[MySQL]
    MONGO[MongoDB]
    REDIS[Redis]

    JIRA[Jira]
    PD[PagerDuty]
    SLACK[Slack]
    SNOW[ServiceNow]

    CODE --> GH
    CODE --> GL
    CODE --> BB

    OBS --> PROM
    OBS --> GRAF
    OBS --> LOKI
    OBS --> TEMPO
    OBS --> DD

    DEP --> GHA
    DEP --> JEN
    DEP --> ARGO

    INFRA --> K8S
    INFRA --> DOCKER
    INFRA --> CLOUD

    DB --> PG
    DB --> MYSQL
    DB --> MONGO
    DB --> REDIS

    INC --> JIRA
    INC --> PD
    INC --> SLACK
    INC --> SNOW

    ACTION --> JIRA
    ACTION --> GHA
    ACTION --> K8S
```

The agent count stays fixed while customer connectors vary.

---

# 6. MCP integration

```mermaid
flowchart TB
    LLM[Agent LLM]
    AGENT[Agent]
    LG[LangGraph]
    MCPC[MCP Client]
    MCPS[MCP Server]
    API[External API / System]

    LLM --> AGENT
    AGENT --> LG
    LG --> MCPC
    MCPC --> MCPS
    MCPS --> API
```

Example:

```text
Code Agent
 → MCP Client
 → GitHub MCP
 → GitHub

Observability Agent
 → MCP Client
 → Prometheus MCP
 → Prometheus

Incident Agent
 → MCP Client
 → Jira MCP
 → Jira
```

MCP is connectivity, not orchestration.

---

# 7. Native internal tool path

```mermaid
flowchart LR
    AG[Agent]
    TOOL[Native Python Tool]
    SERVICE[Internal Service]
    DATA[(Internal Data)]

    AG --> TOOL
    TOOL --> SERVICE
    SERVICE --> DATA
```

Suitable internal components:
- RAG retrieval;
- Chroma;
- BM25;
- Markdown parsing;
- log parsing;
- evidence normalization;
- report generation;
- shared state utilities.

---

# 8. Capability registry

```mermaid
flowchart TB
    CUSTOMER[Customer Connects Tool]
    AUTH[Authentication / Validation]
    DISCOVER[Capability Discovery]
    REG[Capability Registry]

    CODEMAP[Code Agent]
    OBSMAP[Observability Agent]
    DEPMAP[Deployment Agent]
    INFRAMAP[Infrastructure Agent]
    DBMAP[Database Agent]
    INCMAP[Incident Agent]
    ACTIONMAP[Action Agent]

    CUSTOMER --> AUTH
    AUTH --> DISCOVER
    DISCOVER --> REG

    REG --> CODEMAP
    REG --> OBSMAP
    REG --> DEPMAP
    REG --> INFRAMAP
    REG --> DBMAP
    REG --> INCMAP
    REG --> ACTIONMAP
```

Example mapping:

```text
GitHub:
  read_commits        → Code Agent
  read_pull_requests  → Code Agent
  read_files          → Code Agent
  read_issues         → Incident Agent
  read_actions        → Deployment Agent
```

---

# 9. Customer connection onboarding

```mermaid
flowchart LR
    U[Customer]
    UI[Connections UI]
    AUTH[OAuth / Token / Endpoint]
    TEST[Connection Health Check]
    CAPS[Capability Discovery]
    POLICY[Permission Policy]
    READY[Connected Tool]

    U --> UI
    UI --> AUTH
    AUTH --> TEST
    TEST --> CAPS
    CAPS --> POLICY
    POLICY --> READY
```

Customers configure tools, not agents.

---

# 10. Permission architecture

```mermaid
flowchart TB
    CONN[Connected System]
    READ[Read Capabilities]
    WRITE[Write Capabilities]
    EXEC[Execution Capabilities]
    APPROVAL[Human Approval]
    ACTION[Action Agent]

    CONN --> READ
    CONN --> WRITE
    CONN --> EXEC

    WRITE --> APPROVAL
    EXEC --> APPROVAL
    APPROVAL --> ACTION
```

Defaults:

```text
READ    = available when needed
WRITE   = disabled
EXECUTE = disabled
```

---

# 11. Human approval

```mermaid
flowchart LR
    RCA[RCA Agent]
    REC[Recommendation]
    REVIEW[Engineer Review]
    APPROVE{Approved?}
    ACTION[Action Agent]
    EXEC[External Write / Execute]
    REJECT[Reject / Request More Investigation]

    RCA --> REC
    REC --> REVIEW
    REVIEW --> APPROVE

    APPROVE -->|Yes| ACTION
    APPROVE -->|No| REJECT
    ACTION --> EXEC
```

---

# 12. Engineering memory

```mermaid
flowchart TB
    OBS[Obsidian Vault / Markdown]
    PARSE[Markdown Parser]
    CHUNK[Chunking]
    EMBED[Embedding Model]
    CHROMA[(ChromaDB)]
    BM25[BM25 Index]
    HYBRID[Hybrid Retriever]
    KNOW[Knowledge Agent]
    STATE[(Shared Investigation State)]

    OBS --> PARSE
    PARSE --> CHUNK
    CHUNK --> EMBED
    EMBED --> CHROMA

    CHUNK --> BM25

    CHROMA --> HYBRID
    BM25 --> HYBRID

    HYBRID --> KNOW
    KNOW --> STATE
```

---

# 13. Real-time War Room events

```mermaid
flowchart LR
    GRAPH[LangGraph Execution]
    EVENTS[Investigation Event Stream]
    API[FastAPI WebSocket / SSE]
    UI[Engineering War Room]

    GRAPH --> EVENTS
    EVENTS --> API
    API --> UI
```

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

---

# 14. War Room visual layout

```mermaid
flowchart TB

    HEADER[Incident Header / Status]
    SUP[Supervisor Station]

    CODE[Code Desk]
    OBS[Observability Desk]
    DEP[Deployment Desk]
    INFRA[Infrastructure Desk]
    DB[Database Desk]
    KNOW[Knowledge Desk]
    INC[Incident Desk]

    BOARD[Shared Investigation Board]
    RCA[RCA Desk]
    APPROVAL[Human Approval Desk]

    HEADER --> SUP

    SUP --> CODE
    SUP --> OBS
    SUP --> DEP
    SUP --> INFRA
    SUP --> DB
    SUP --> KNOW
    SUP --> INC

    CODE --> BOARD
    OBS --> BOARD
    DEP --> BOARD
    INFRA --> BOARD
    DB --> BOARD
    KNOW --> BOARD
    INC --> BOARD

    BOARD --> RCA
    RCA --> APPROVAL
```

The War Room should resemble a modern engineering office:
- desks/stations;
- shared evidence wall;
- live status;
- subtle motion;
- clear state indicators.

All motion should be driven by actual backend events.

---

# 15. End-to-end target architecture

```mermaid
flowchart TB

    USER[Engineer]
    UI[React Engineering War Room]
    API[FastAPI]

    SUP[Supervisor]

    CODE[Code]
    OBS[Observability]
    DEP[Deployment]
    INFRA[Infrastructure]
    DB[Database]
    KNOW[Knowledge]
    INC[Incident]

    STATE[(Shared Investigation State)]
    RCA[RCA]
    ACTION[Action]
    HUMAN[Human Approval]

    REG[Capability Registry]
    TOOLS[MCP Client / Native Tools]
    EXT[External Engineering Systems]

    MEMORY[Engineering Memory<br/>Obsidian / Chroma]

    USER --> UI
    UI --> API
    API --> SUP

    SUP --> CODE
    SUP --> OBS
    SUP --> DEP
    SUP --> INFRA
    SUP --> DB
    SUP --> KNOW
    SUP --> INC

    CODE --> STATE
    OBS --> STATE
    DEP --> STATE
    INFRA --> STATE
    DB --> STATE
    KNOW --> STATE
    INC --> STATE

    STATE --> RCA
    RCA --> ACTION
    ACTION --> HUMAN

    SUP --> REG
    CODE --> REG
    OBS --> REG
    DEP --> REG
    INFRA --> REG
    DB --> REG
    KNOW --> REG
    INC --> REG
    ACTION --> REG

    REG --> TOOLS
    TOOLS --> EXT

    KNOW --> MEMORY
    MEMORY --> KNOW
```

---

# 16. Runtime mental model

```text
LLM
 ↓
Agent
 ↓
LangGraph
 ↓
Tool interface
 ↓
MCP Client OR Native Python Tool
 ↓
Connector
 ↓
External Engineering System
```

Globally:

```text
10 Core Agents
      +
Dynamic Connectors
      +
Capability Registry
      +
Least-Privilege Permissions
      +
Shared Investigation State
      +
Human Approval
```

---

# 17. Explicit non-requirement

Do not add Munder Difflin or another external agentic harness as a required runtime layer.

Use:

```text
LangGraph = orchestration
MCP/native tools = tool connectivity
FastAPI = application/backend
React = War Room UI
```

A dedicated harness/runtime can be considered later for:
- observability;
- execution control;
- evaluation;
- cost tracking;
- retries/timeouts;
- sandboxing.

It is not part of the required first implementation.
