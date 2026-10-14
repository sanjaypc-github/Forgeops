# 14 — Glossary and abbreviations

Feeds the report's **List of Abbreviations** and keeps terminology consistent throughout.

---

## 14.1 Project-specific terms

| Term | Meaning |
|---|---|
| **ForgeOps** | The product and repository name |
| **EOPS** | Engineering Operations Platform — the name used in the paper and this report |
| **Desk** | One specialised agent responsible for one system area (Code, Database, Observability, …). Named after the office metaphor in the interface |
| **War Room** | The 2D top-down office interface where the investigation is watched live |
| **Investigation** | One run: from the problem statement to the approved or rejected root-cause report |
| **Shared investigation state** | The typed state object all desks write into, where every finding carries its tool-call citation |
| **Capability** | What a tool can do (`code`, `hosting`, `database`, `logs`, `knowledge`, `write`), used to route the tool to the right desk |
| **Connector** | A configured connection to one external tool, exposing only an allow-listed set of abilities |
| **Ability** | One tool a connector exposes to agents, with its capability and read/write permission |
| **Engineering Memory Layer** | The retrieval layer over the team's own Markdown documentation |
| **Harness** | Everything around the model: prompts, contracts, validators, budgets, policy and calibration |
| **Compaction** | Collapsing older tool results to their opening while keeping their citation identifier |
| **Service map** | One line per connected tool, telling the Supervisor what the customer's stack contains |
| **Offline mode** | A labelled development stand-in that runs the real graph with no model and no analysis |
| **Budget** | A hard limit on tool calls, time or questions, enforced by the harness |
| **Evidence** | A finding that cites the identifiers of successful tool calls |
| **Failure point** | The precise location of the cause: a file and line, a query, a configuration value, a deployment |

## 14.2 Technical abbreviations

| Abbreviation | Expansion | Relevance here |
|---|---|---|
| **AI** | Artificial Intelligence | |
| **AIOps** | Artificial Intelligence for IT Operations | The field this work sits beside |
| **API** | Application Programming Interface | The backend's HTTP surface |
| **BM25** | Best Matching 25 | Lexical ranking function used alongside dense retrieval |
| **CI/CD** | Continuous Integration / Continuous Deployment | A source of deployment evidence |
| **CSRF** | Cross-Site Request Forgery | Defended with a per-session token on unsafe methods |
| **CRUD** | Create, Read, Update, Delete | |
| **DOM** | Document Object Model | |
| **ER** | Entity-Relationship | The database diagram |
| **GROQ / SQL** | Query languages (Sanity / relational) | Used by connectors |
| **HTTP / HTTPS** | Hypertext Transfer Protocol (Secure) | |
| **JSON / JSONB** | JavaScript Object Notation / its binary PostgreSQL form | Event payloads, configuration, usage |
| **JWT** | JSON Web Token | Not used; sessions are opaque cookies with hashed storage |
| **LLM** | Large Language Model | The reasoning component |
| **MCP** | Model Context Protocol | The standard contract through which connectors expose tools |
| **MRR** | Mean Reciprocal Rank | Retrieval metric in Experiment 2 |
| **MTTR** | Mean Time To Resolution | The headline operational metric |
| **MVP** | Minimum Viable Product | |
| **OAuth 2.1** | Authorisation framework | Used for providers that do not accept API tokens |
| **ORM** | Object-Relational Mapping | SQLAlchemy |
| **PKCE** | Proof Key for Code Exchange | Protects the OAuth authorisation code |
| **RAG** | Retrieval-Augmented Generation | The Engineering Memory Layer |
| **RCA** | Root Cause Analysis | The purpose of the system |
| **ReAct** | Reasoning and Acting | The per-desk loop pattern |
| **REST** | Representational State Transfer | The API style |
| **RRF** | Reciprocal Rank Fusion | Merges dense and lexical result lists |
| **SaaS** | Software as a Service | The intended delivery model |
| **SLO** | Service Level Objective | |
| **SRE** | Site Reliability Engineering | The discipline this assists |
| **SSE** | Server-Sent Events | How the interface receives live events |
| **TTM** | Time To Mitigate | The 52.5-hour motivation figure |
| **UI / UX** | User Interface / User Experience | |
| **XSS** | Cross-Site Scripting | The defect found in review and fixed |

## 14.3 Named systems referenced

| Name | What it is |
|---|---|
| **AutoGen** | Multi-agent conversation framework (Microsoft) |
| **LangGraph** | Graph orchestration library used for the investigation graph |
| **Chroma** | Vector database used by the memory layer |
| **SWE-agent / SWE-bench** | Agent and benchmark for repository issue resolution |
| **RCACopilot** | Microsoft's LLM root-cause system (EuroSys 2024) |
| **RCAgent** | Alibaba's tool-augmented RCA agent (CIKM 2024) |
| **OpenRCA** | Public RCA benchmark (ICLR 2025) |
| **AIOpsLab** | Agent evaluation platform for cloud operations (MLSys 2025) |
| **ITBench** | IBM benchmark for IT automation agents (ICML 2025) |
| **OpenRouter** | The model gateway used; any OpenAI-compatible endpoint works |
| **Supabase** | Managed PostgreSQL used for the application's own data |

## 14.4 Spelling and style decisions

| Convention | Choice |
|---|---|
| Product naming | "ForgeOps" in code and repository contexts; "EOPS" in the paper and report |
| "Root cause analysis" | Three words, no hyphen, except as the adjective "root-cause analysis" |
| Agent naming | "desk" for a specialist agent; "Supervisor", "RCA agent" and "Action desk" capitalised as roles |
| Numbers | Spell out below ten in prose; use figures for all measurements |
| Tense | Present tense for what the system does; past tense for what was built and measured |
