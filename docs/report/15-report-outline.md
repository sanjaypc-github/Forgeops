# 15 — The 60-page report outline

**Read this file first if you are writing the report.** It gives the chapter plan, a page budget for
every section, the source file that supplies each part, and the complete figure and table list.

Target: **60 pages of body text**, excluding front matter and appendices.

---

## 15.1 Front matter (not counted in the 60)

Title page · Bonafide certificate · Declaration · Acknowledgement · Abstract (one page, 250–300
words) · Table of contents · List of figures · List of tables · List of abbreviations (take from
`14-glossary.md`).

**Abstract source:** adapt the paper's abstract, then add one sentence on implementation status
(232 automated tests, three working connectors) and one on the evaluation protocol.

---

## 15.2 Chapter plan

### Chapter 1 — Introduction · 8 pages
| Section | Pages | Source |
|---|---|---|
| 1.1 Background: modern software operations | 1.5 | `01-project-overview.md` §1.1 |
| 1.2 The incident-investigation problem (six disconnected systems, 52.5 h) | 1.5 | §1.1 |
| 1.3 Motivation: why existing AI assistants do not solve it | 1.5 | §1.2 |
| 1.4 Problem statement | 0.5 | §1.3 |
| 1.5 Aim and objectives | 1 | §1.4 |
| 1.6 Scope and limitations of scope | 1 | §1.5 |
| 1.7 Organisation of the report | 1 | §1.8 |

### Chapter 2 — Literature Survey · 12 pages
| Section | Pages | Source |
|---|---|---|
| 2.1 Foundations: transformers and retrieval-augmented generation | 2 | `02-literature-survey.md` §2.2 |
| 2.2 Agentic reasoning and multi-agent orchestration | 2.5 | §2.3 |
| 2.3 LLM agents in software engineering | 2 | §2.4 |
| 2.4 LLM-based root cause analysis | 3 | §2.5 |
| 2.5 Benchmarks and the state of the art | 1.5 | §2.6 |
| 2.6 Comparative analysis and research gap | 1 | §2.7, §2.8 |

Write each work as: what it does → its key result → its limitation for *this* problem. Three to four
works per page is the right density. End with the gap statement verbatim.

### Chapter 3 — System Design · 14 pages
| Section | Pages | Source |
|---|---|---|
| 3.1 Design goals and principles | 1 | `03-system-architecture.md` §3.1 |
| 3.2 Overall architecture: the six layers | 2.5 | §3.2 |
| 3.3 The investigation workflow (five phases) | 2.5 | §3.3 + `01` objectives |
| 3.4 Agent roles and responsibilities | 2 | `06-agent-harness.md` §6.2 |
| 3.5 Capability routing and the connector model | 2 | §3.4 |
| 3.6 The Engineering Memory Layer | 1.5 | §3.5 |
| 3.7 Design decisions and rationale | 1.5 | §3.6 |
| 3.8 Technology stack and non-functional requirements | 1 | §3.7, §3.8 |

### Chapter 4 — Implementation · 16 pages
| Section | Pages | Source |
|---|---|---|
| 4.1 Development environment and project structure | 1 | `12-setup-guide.md`, `04-module-guide.md` §4.1 |
| 4.2 Data model: tables, state, events | 2.5 | `05-data-model.md` |
| 4.3 The orchestration graph | 2 | `04` §4.4.1 |
| 4.4 The specialist loop and inter-agent questions | 2.5 | `04` §4.4.3–4.4.4 |
| 4.5 The harness: contracts, citation, budgets, calibration | 3 | `06-agent-harness.md` |
| 4.6 Connector layer and the MCP client | 2 | `04` §4.7 |
| 4.7 Knowledge layer and hybrid retrieval | 1 | `04` §4.8 |
| 4.8 API layer | 1 | `07-api-reference.md` |
| 4.9 Frontend: the War Room | 1 | `08-frontend-guide.md` |

Include short code excerpts (10–15 lines) for: the citation validator, the compaction view, the
confidence caps, and a connector definition. Never paste a whole file.

### Chapter 5 — Testing and Results · 8 pages
| Section | Pages | Source |
|---|---|---|
| 5.1 Testing strategy and test doubles | 1.5 | `09-testing.md` §9.1, §9.6 |
| 5.2 Test coverage by module, with representative tests | 2 | §9.2, §9.4 |
| 5.3 Implementation results (what exists and runs) | 1 | `10-results-and-measurements.md` §10.1 |
| 5.4 Context-efficiency measurement | 2 | §10.2 (include the formula, the table and the chart) |
| 5.5 Evaluation protocol for the empirical study | 1 | §10.4 |
| 5.6 Threats to validity | 0.5 | §10.6 |

### Chapter 6 — Conclusion and Future Work · 4 pages
| Section | Pages | Source |
|---|---|---|
| 6.1 Summary of contributions | 1 | `13` §13.3 |
| 6.2 Limitations | 1.5 | `13` §13.1 |
| 6.3 Future work | 1.5 | `13` §13.2 |

**Total: 8 + 12 + 14 + 16 + 8 + 4 = 62 pages**, which lands on target once figures are placed.

---

## 15.3 Appendices (not counted)

| Appendix | Contents | Source |
|---|---|---|
| A | Installation and configuration guide | `12-setup-guide.md` |
| B | Complete API reference | `07-api-reference.md` |
| C | Database schema with all columns | `05-data-model.md` |
| D | The agent prompts | `backend/forgeops/engine/prompt_templates/` |
| E | Sample investigation report produced by the system | run the smoke tool and paste the output |
| F | Conference paper acceptance and presentation | `docs/presentation/` |

---

## 15.4 Figure list (aim for 18–22 figures)

| # | Figure | Chapter | Source |
|---|---|---|---|
| 1.1 | Fragmented investigation across six systems | 1 | Redraw from `01` §1.1 table |
| 1.2 | Time-to-mitigate motivation chart | 1 | `10` §10.1 |
| 2.1 | Taxonomy of related work | 2 | `02` §2.7 |
| 3.1 | Six-layer system architecture | 3 | `03` §3.2 |
| 3.2 | Investigation graph (plan → desks → review → RCA → approval → report) | 3 | `03` §3.3 |
| 3.3 | Agent collaboration: desk-to-desk questions | 3 | `06` §6.11 |
| 3.4 | Capability-to-desk routing | 3 | `03` §3.4 |
| 3.5 | Engineering Memory Layer pipeline | 3 | `03` §3.5 |
| 3.6 | Sequence diagram of one investigation | 3 | draw from `03` §3.3 |
| 4.1 | Entity-relationship diagram (9 tables) | 4 | `05` §5.1 |
| 4.2 | Shared state and reducer merge | 4 | `05` §5.3 |
| 4.3 | Specialist loop flowchart | 4 | `04` §4.4.3 |
| 4.4 | Citation chain: evidence → tool call → result | 4 | `05` §5.4 |
| 4.5 | Context compaction before and after | 4 | `06` §6.9 |
| 4.6 | Event flow from backend to War Room | 4 | `08` §8.4 |
| 5.1 | Context resent per desk (bar chart) | 5 | `10` §10.2 |
| 5.2 | Saving versus number of tool calls (line chart) | 5 | `10` §10.2 table |
| S1–S7 | Screenshots: War Room, agent walking, approval card, Connectors page, abilities, report, Swagger UI | 4/5 | `08` §8.9 |

## 15.5 Table list (aim for 12–15 tables)

| # | Table | Chapter | Source |
|---|---|---|---|
| 1.1 | Evidence sources and the question each answers | 1 | `01` §1.1 |
| 2.1 | Summary of related work with limitations | 2 | `02` §2.5 |
| 2.2 | Capability comparison against prior systems | 2 | `02` §2.7 |
| 3.1 | Layer responsibilities | 3 | `03` §3.2 |
| 3.2 | Capability-to-desk routing | 3 | `03` §3.4 |
| 3.3 | Design decisions and rationale | 3 | `03` §3.6 |
| 3.4 | Technology stack | 3 | `03` §3.7 |
| 4.1 | Module inventory with line counts | 4 | `04` §4.1 |
| 4.2 | Database tables | 4 | `05` §5.2 |
| 4.3 | Event catalogue | 4 | `05` §5.5 |
| 4.4 | Budgets and their defaults | 4 | `06` §6.7 |
| 4.5 | Confidence caps | 4 | `06` §6.8 |
| 5.1 | Test inventory by suite | 5 | `09` §9.2 |
| 5.2 | Context reduction by number of tool calls | 5 | `10` §10.2 |
| 5.3 | Evaluation metric families | 5 | `10` §10.4 |

---

## 15.6 Writing rules for this report

1. **Tag every number.** If it is not in `10-results-and-measurements.md`, it is not a result.
2. **Say "proposed" or "planned"** for the evaluation; say "implemented" for what exists; say
   "measured" only for §10.1 and §10.2.
3. **Explain why, not only what.** Chapter 3 earns its pages through rationale, not description.
4. **Cite the code** by path when describing implementation.
5. **One idea per paragraph**, 3–5 sentences. Avoid long unbroken blocks.
6. **Keep the honest framing**: decision support, human approval, limitations stated plainly.
7. **Consistent terminology** — see `14-glossary.md`. "Desk" always means a specialist agent.
8. **Do not pad.** If a section is short, add a figure or an example, not adjectives.

## 15.7 Suggested writing order

1. Chapter 4 (Implementation) — the most concrete, and it clarifies everything else.
2. Chapter 3 (Design) — now that the implementation is written down.
3. Chapter 2 (Literature) — the sources are already summarised; write the comparison last.
4. Chapter 5 (Testing and Results).
5. Chapter 1 (Introduction) — easiest to write once the rest exists.
6. Chapter 6 (Conclusion), abstract, and front matter.
