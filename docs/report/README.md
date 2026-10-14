# ForgeOps / EOPS — documentation pack for the final-year project report

This folder exists for one purpose: **another person (or another AI agent) should be able to clone
this repository, read this folder, and write the ~60-page final-year project report without asking
us anything and without inventing anything.**

Read this page first. It explains the rules, the file map, and the order to read in.

---

## 1. What this project is, in three sentences

ForgeOps (published under the name **EOPS**) is a multi-agent AI platform that finds the **root cause
of a production software incident** and shows the exact failure point with evidence. A customer
connects their own engineering tools (GitHub, Supabase, a knowledge vault, and more) through a
connector catalog; when something breaks, a Supervisor agent plans an investigation and several
specialised agents — called **desks** — investigate those tools **in parallel**, ask each other
questions, and write every finding into one shared investigation state. A Root Cause Analysis agent
then produces the root cause, the failure point and a confidence value, and a **human engineer must
approve** before the system writes anything back to the customer's systems.

The academic paper describing this architecture was accepted and presented at **ICSIE 2026**.

---

## 2. Rules for whoever writes the report

These rules exist because the project's own design principle is "evidence or silence". The report
must follow the same standard.

| Rule | Why |
|---|---|
| **Never invent experimental results.** | This project is a working prototype with a defined evaluation protocol. The large-scale empirical study has **not** been run yet. Numbers that exist are listed in `10-results-and-measurements.md`; nothing beyond those may be reported as a result. |
| **Distinguish "measured" from "computed" from "planned".** | Each number in `10-results-and-measurements.md` is tagged with which one it is. Carry those tags into the report wording. |
| **Cite the code.** | When describing a module, cite the real file path (e.g. `backend/forgeops/engine/specialist.py`). Paths in this pack are accurate as of the commit that contains it. |
| **Use the literature in `02-literature-survey.md`.** | Those references were verified against the real papers. Do not add references that were not checked. |
| **Keep the honest framing.** | The system is a *decision-support* tool, not an autonomous fixer. Every write needs human approval. Saying otherwise misrepresents the work. |
| **British or Indian English, consistent throughout.** | Pick one and keep it. |

If a fact is needed that is not in this pack, the answer is in the code — read it — or it does not
exist yet, in which case it belongs in `13-limitations-and-future-work.md`, not in the results.

---

## 3. Reading order and file map

| # | File | What it gives the report |
|---|---|---|
| 01 | `01-project-overview.md` | Problem, motivation, objectives, scope, stakeholders — Chapter 1 |
| 02 | `02-literature-survey.md` | 14 verified works, what each contributes, its limitation, the research gap — Chapter 2 |
| 03 | `03-system-architecture.md` | Six layers, the investigation flow, component diagram, design decisions with rationale — Chapter 3 |
| 04 | `04-module-guide.md` | Every module: purpose, files, inputs, outputs, key classes and algorithms — Chapter 4 |
| 05 | `05-data-model.md` | 9 database tables, the LangGraph state, the 27 event types, data contracts — Chapter 4 |
| 06 | `06-agent-harness.md` | Prompts, budgets, evidence rules, confidence calibration, context discipline — Chapter 4/5 |
| 07 | `07-api-reference.md` | All 21 REST endpoints with request and response shapes — Chapter 4 appendix |
| 08 | `08-frontend-guide.md` | The War Room UI, pages, the event-driven reducer — Chapter 4 |
| 09 | `09-testing.md` | Test strategy, suites, how to run them, what each proves — Chapter 5 |
| 10 | `10-results-and-measurements.md` | Everything measurable, tagged measured/computed/planned — Chapter 5 |
| 11 | `11-milestones-and-status.md` | M0 to M5, what is complete, what is pending, with dates — Chapter 5/6 |
| 12 | `12-setup-guide.md` | Environment, configuration, how to run it — Appendix |
| 13 | `13-limitations-and-future-work.md` | Honest limitations and the roadmap — Chapter 6 |
| 14 | `14-glossary.md` | Every term and abbreviation used in the project | 
| 15 | `15-report-outline.md` | **The 60-page chapter plan**: page budget per chapter, which file feeds it, and the figure and table list |

**Start at `15-report-outline.md`** if you are writing the report. It tells you what to write, in what
order, how many pages each part should take, and which of these files supplies the material.

---

## 4. Where the real material lives outside this folder

| Path | Contents |
|---|---|
| `AGENTS.md` / `CLAUDE.md` | Engineering guide: repo map, non-negotiable rules, how to add a connector |
| `docs/PRD.md` | Product requirements: users, goals, user stories, release definition |
| `docs/TRD.md` | Technical requirements: stack, schema, configuration, milestones |
| `docs/HARNESS.md` | The agent harness contract — role prompts, honesty rules, budgets, confidence rubric |
| `docs/superpowers/plans/` | One implementation plan per milestone, written before the code |
| `docs/presentation/` | The ICSIE conference deck, the speaker script and the defence preparation pack |
| `backend/` | Python backend: API, engine, connectors, database |
| `frontend/` | React frontend: the War Room, Connectors page, investigation history |

---

## 5. Project identity

| Field | Value |
|---|---|
| Product name | ForgeOps (code and repository) |
| Academic name | EOPS — Engineering Operations Platform (paper and report) |
| Paper | "EOPS: A Multi-Agent AI Engineering Operations Platform for Automated Incident Investigation and Root Cause Analysis" |
| Venue | ICSIE 2026 — accepted and presented |
| Team | Sanjay P C · Sam Benadick J · Praveenkumar S · Nibuna A |
| Guide | Ms D. Hemamalini |
| Department | Artificial Intelligence & Data Science, Sri Eshwar College of Engineering, Coimbatore |
| Repository | `github.com/sanjaypc-github/Forgeops` |
