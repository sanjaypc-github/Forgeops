# 01 — Project overview

Feeds **Chapter 1 (Introduction)** of the report.

---

## 1.1 The problem

Modern software products are built from many moving parts: application code, a continuous-deployment
pipeline, a hosting platform, one or more databases, third-party services, and content systems.
Teams deploy several times a day. Because of that pace, production incidents — a page becoming slow,
a feature breaking, an API failing — are unavoidable.

When an incident happens, the difficult part is not repairing it. **The difficult part is finding
what broke.** The evidence needed to answer that question is spread across systems that do not talk
to each other:

| Source | The question it answers |
|---|---|
| Source-code repository | What changed recently, and who changed it |
| Deployment and CI history | What was shipped, when, and whether it succeeded |
| Database | Schema changes, slow queries, missing indexes, security advisories |
| Application logs and error trackers | What the system itself reported at the time |
| Runbooks and architecture documents | What the team already knows about this subsystem |
| Chat history and past incident reports | What a colleague saw the last time this happened |

An engineer opens all of these, holds partial clues in working memory, and correlates them by hand.
This has three costs: it is slow, it is cognitively expensive, and the quality of the answer depends
on which engineer happens to be on call.

**Scale of the problem.** A published analysis of one year of production incidents at Microsoft
reported a *median time to mitigate of 52.5 hours*, with a 10% trimmed mean of 83.0 hours
(see reference [14] in `02-literature-survey.md`). A large share of that time is spent locating the
cause rather than fixing it.

## 1.2 Why existing AI does not solve it

Three categories of existing systems are close, and none of them closes the gap:

1. **Code agents** (SWE-agent and similar) operate inside a repository. They can edit code and close
   issues, but they never observe the live system, and they have no incident context.
2. **One-shot LLM root-cause analysis** (Ahmed et al.; RCACopilot) predicts a root-cause *category*
   from telemetry that was gathered beforehand. These systems are *provider-side* — built inside one
   cloud provider's own telemetry — and each alert type needs a hand-written collection handler.
3. **Conversational assistants** answer questions about systems but hold no tools, so they cannot
   gather evidence and cannot verify what they say.

The missing capability is a system that investigates **a customer's own, heterogeneous set of tools**,
with **several specialised agents working in parallel** over **one shared body of evidence** in which
**every claim is traceable to the tool call that produced it**.

## 1.3 Aim

To design, implement and evaluate a supervisor-driven multi-agent platform that investigates a
software production incident across the team's own engineering tools and returns an evidence-backed
root cause, while keeping a human engineer in control of every action.

## 1.4 Objectives

1. Design a **supervisor-driven multi-agent architecture** in which one agent per system area
   investigates independently and concurrently.
2. Build a **connector catalog** so that any customer's tools can be attached without writing new
   agent code, with each connector exposing only an allow-listed set of abilities.
3. Maintain a **shared investigation state** in which every finding carries the identifier of the
   tool call that produced it, so that no claim can be made without evidence.
4. Provide an **Engineering Memory Layer** that makes the team's own documentation searchable and
   citable during an investigation (Retrieval-Augmented Generation).
5. Produce a **root-cause report** with the failure point, supporting evidence, a calibrated
   confidence value, and an explicit list of what could not be checked.
6. Keep a **human approval gate** before any action that writes to the customer's systems.
7. Make the system's own **cost and context usage observable and bounded**, so that investigation
   remains affordable and repeatable.

## 1.5 Scope

### In scope

- Incident investigation and root-cause analysis as **decision support** for a software team.
- A connector catalog with three working connectors (GitHub, Supabase, knowledge vault) and an
  OAuth connect flow for further providers.
- A live web interface — the **War Room** — that shows the investigation as it happens.
- One workspace per installation; the data model supports multiple workspaces for future SaaS use.
- One write action: creating a GitHub issue, only after explicit human approval.

### Out of scope (deliberately)

- Automatic remediation — rollbacks, restarts, scaling, merges. The system investigates; the human acts.
- Replacing monitoring and alerting. ForgeOps consumes what those systems expose; it is not an
  anomaly detector.
- Sign-up, billing, and multi-tenant operations UI. The data model is ready; the interface is not.
- Fine-tuning or training a model. The contribution is the harness around a general model.

## 1.6 Stakeholders and users

| Stakeholder | What they need from the system |
|---|---|
| **Developer on call** in a small or mid-size software team | A cited root cause within minutes, not a chat transcript |
| **Technical lead** | Confidence that nothing was changed without approval and that gaps are reported honestly |
| **Team without a dedicated SRE** | The investigation capability that larger companies build in-house |
| **Researchers** | A reproducible architecture and an evaluation protocol |

## 1.7 Expected outcomes

1. A working platform: backend engine, connector framework, web interface, and tests.
2. An architecture that extends to new tools without changing the agents.
3. A published and presented conference paper (ICSIE 2026).
4. A defined evaluation protocol against public benchmarks, ready to execute.

## 1.8 Organisation of the report

See `15-report-outline.md` for the chapter plan. In brief: Chapter 1 states the problem and
objectives; Chapter 2 reviews the literature and identifies the gap; Chapter 3 presents the system
architecture; Chapter 4 describes the implementation module by module; Chapter 5 covers testing,
measurements and the evaluation protocol; Chapter 6 concludes with limitations and future work.
