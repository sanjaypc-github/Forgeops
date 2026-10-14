# EOPS — ICSIE defence pack (8 min talk + 2 min Q&A)

Everything you need the night before: the script with timings, how to defend validation, the
literature you must be able to name, the algorithms, the novelty table, and a question bank.

---

## 0. The one thing to get right

Your paper is an **architecture / position paper**: it proposes EOPS and states *expected* outcomes.
That is legitimate at a conference, but it means **every hard question will be about evidence**.

Never say "we have results". Say this instead, in one breath:

> "The paper contributes the architecture. The system is now implemented — engine, connectors,
> orchestration, token accounting — and our evaluation protocol is defined against three public
> benchmarks. What I can show today is the design, the working implementation, and exactly how we
> will measure it."

Confidence without overclaiming is what gets respect in these rooms.

---

## 1. Eight-minute script (timings are hard limits)

| Time | Slide | What you say |
|---|---|---|
| 0:00–0:45 | **Hook** | "When production breaks, an engineer opens six tabs: GitHub, logs, the database console, the hosting dashboard, the runbook wiki, and Slack. A Microsoft study of a year of production incidents found a **median time-to-mitigate of 52.5 hours**. Most of that is not fixing. It is *finding*." |
| 0:45–1:30 | **Problem** | Investigation is fragmented across heterogeneous systems; evidence correlation is manual; it depends on one senior engineer's memory. State the research question verbatim from the paper. |
| 1:30–2:15 | **Why existing AI does not solve it** | Three honest buckets: (a) code agents (SWE-agent) fix code but do not investigate live systems; (b) one-shot LLM RCA (Ahmed et al. ICSE'23, RCACopilot EuroSys'24) predicts a root-cause *category* from pre-collected telemetry inside one company's internal stack; (c) conversational assistants answer questions but hold no tools. Gap: **no coordinated, multi-source, customer-side investigation**. |
| 2:15–3:30 | **EOPS architecture** | The six layers, but spend your words on the orchestration: Supervisor plans → specialist desks run **in parallel** → shared investigation state → RCA agent → human approval. Say "one agent per system area, not one agent per task." |
| 3:30–4:30 | **The harness is the contribution** | This is your strongest 60 seconds. Four mechanisms: evidence-citation enforcement, read-only capability separation, bounded budgets, context compaction. See §4. |
| 4:30–5:15 | **Engineering Memory Layer** | Obsidian/Markdown → chunk → embed → Chroma; hybrid dense + BM25 with reciprocal-rank fusion at query time; the Knowledge desk cites documents like any other evidence. |
| 5:15–6:15 | **Implementation status** | Working system: FastAPI + LangGraph 1.x, 9 agent roles, MCP connector catalog (GitHub, Supabase, knowledge vault live), 229 automated tests, live War Room UI. Show one screenshot of the office and one of the report. |
| 6:15–7:15 | **Evaluation protocol** | §3. Name the three benchmarks and the four metric families. This is where you prove you are a researcher, not a hobbyist. |
| 7:15–7:45 | **Limitations, honestly** | No large-scale empirical results yet; evaluation on injected faults may not reflect production; multi-agent costs more total tokens than a single prompt — we trade tokens for bounded context and wall-clock. |
| 7:45–8:00 | **Close** | "EOPS turns incident investigation from a manual, memory-dependent process into a coordinated, evidence-cited one, with the engineer still deciding. The architecture is published; the measurement is next." |

**Rehearsal rule:** read it aloud twice with a timer. If you overrun, cut slide 5 (memory layer) to one
sentence — never cut slide 7 (evaluation).

---

## 2. The literature you must be able to name

Your paper cites agent/RAG infrastructure (AutoGen, ReAct, LangGraph, Chroma, SWE-agent) but **not the
RCA domain**. If a chairperson knows this field, the first question is "are you aware of RCACopilot?"
Learn these eight. For each: what it does → what it lacks → why EOPS differs.

| Work | What it did | Its limitation | Your line |
|---|---|---|---|
| **Ahmed et al., ICSE 2023** — *Recommending root-cause and mitigation steps for cloud incidents using LLMs* | Fine-tuned GPT on incident title + summary to propose root cause | Only title/summary; fine-tuning is costly and goes stale | "One-shot prediction from a text description — no investigation" |
| **RCACopilot, EuroSys 2024** (Chen et al., Microsoft) | Alert-type "incident handlers" collect diagnostics; LLM predicts root-cause **category** + explanation. **Micro-F1 0.766**, 4.2 s overhead, real Microsoft incidents | Handlers are hand-built per alert type; provider-side; classifies into known categories | "Closest prior art. It needs a pre-built handler per alert type inside one company's telemetry. EOPS investigates a customer's own stack through generic connectors" |
| **Roy et al., FSE 2024 (industry)** — *Exploring LLM-based agents for RCA* | ReAct agent vs CoT vs retrieval baselines on production incidents. Accuracy ~35–39% for all; **hallucination 6% (ReAct) vs 18% (CoT) vs 49% (retrieval)** | Single agent, read-only diagnosis, no multi-source coordination | **Your best citation.** "Tool-grounded agents are not more accurate — they are dramatically more *honest*. EOPS makes that structural" |
| **RCAgent, CIKM 2024** (Alibaba) | Tool-augmented autonomous agent for cloud RCA, privacy-preserving, self-consistency | Single agent, internal platform | "Same instinct, one agent, one company" |
| **SWE-agent, NeurIPS 2024** + **SWE-bench, ICLR 2024** | Agent-computer interface; agents resolve real GitHub issues | Repository-only; no live telemetry, no incident context | Already cited in your paper — keep |
| **OpenRCA, ICLR 2025** (Microsoft) | First public RCA benchmark: 335 failures, 68 GB telemetry | Hard: best model + purpose-built agent solved **11.34%** | "The honest state of the art — this is why human approval is non-negotiable" |
| **AIOpsLab, MLSys 2025** (Microsoft) | Open agent-cloud evaluation platform: detection → localization → RCA → mitigation, fault injection | Built on two DeathStarBench apps, ten fault types | "Our Experiment 4 harness" |
| **ITBench, ICML 2025** (IBM) | Agents on real IT tasks; **SRE scenarios resolved ≈11–14%**; 2026 leaderboard still **<50%** | — | "Independent confirmation that autonomy is premature; decision support is the right target" |

Add one survey for breadth: *A Goal-Driven Survey on Root Cause Analysis* (arXiv:2510.19593, 2025).

**If asked "what did you read and what did you learn from it?"** — answer in this exact shape:

> "Three things. First, from Ahmed and RCACopilot: LLMs can reach useful accuracy on root-cause
> *classification*, but only inside a provider's own telemetry with handlers built per alert type.
> Second, from Roy et al.: giving an agent tools does not raise accuracy much, but it cuts
> hallucination from roughly half to under one in ten — so grounding, not raw model power, is the
> lever. Third, from OpenRCA and ITBench: the best systems still solve only ten to fifteen percent of
> real scenarios autonomously. Those three findings produced our design: multi-source investigation,
> enforced evidence citation, and a human approval gate."

That answer alone will carry the Q&A.

---

## 3. How you validate — the question you asked me

Validation has **four families**. Learn the table; it answers almost any evaluation question.

| Family | Metric | How measured | Baseline compared against |
|---|---|---|---|
| **Correctness** | Root-cause accuracy @1 / @3; failure-point localization (file, service, query, config) | Injected faults with known ground truth | Single-agent ReAct; one-shot prompt with all context; CoT without tools |
| **Honesty** | **Unsupported-claim rate** = statements in the RCA with no verifiable tool-call citation; evidence-citation validity | Automatic: every claim must map to a `tool_call_id` that really succeeded | Roy et al. reported 6% / 18% / 49% — directly comparable |
| **Cost** | Input + output tokens per investigation, per desk; tool calls per investigation; USD per incident | Already instrumented in our implementation (token metering per agent) | Single-agent with full context in one window |
| **Time** | Wall-clock to RCA; human time to decision | Timestamped events | Manual investigation by a developer on the same injected fault |

**Three evaluation settings**, in increasing strength:

1. **Public benchmark** — run the EOPS agent loop on **OpenRCA** (335 cases) and **AIOpsLab** fault
   scenarios. Even a low absolute score is publishable *if* you report it honestly against the
   published baselines (11.34% for the best model on OpenRCA).
2. **Controlled fault injection** — deploy a small reference app (DeathStarBench, or your own
   Cloudflare + Supabase + Sanity site), inject N = 20–30 faults of known type (bad config commit,
   slow query, failed deploy, broken content, expired key), and measure all four metric families.
   This is the one you can realistically complete next semester.
3. **Human study** — 6–10 engineers, each diagnosing incidents with and without EOPS, measuring time
   to correct diagnosis and a 5-point usefulness rating. Small N is acceptable if reported as such.

**Ablations that prove the architecture, not just the model** (this is what reviewers love):

- multi-agent **vs** single agent with the same tools → isolates coordination value
- with **vs** without the Engineering Memory Layer → isolates RAG value
- with **vs** without citation enforcement → isolates the honesty mechanism
- with **vs** without context compaction → isolates the efficiency mechanism
- parallel **vs** sequential desks → isolates the wall-clock claim

---

## 4. The efficiency claim — say it precisely

You asked how to argue "less computation, less time". Be careful: **a naive multi-agent system uses
MORE tokens than one prompt.** If you claim otherwise, a sharp chairperson will catch you. The
defensible claim has three parts.

**(a) Against humans — the big win.** Median time-to-mitigate in the Microsoft study: 52.5 hours. Our
target: a cited root cause in 10–20 minutes. Even a partial answer removes hours of tab-switching.

**(b) Against naive agent designs — measured, not asserted.** Three mechanisms in our implementation:

| Mechanism | Effect |
|---|---|
| **Per-desk context isolation** | Each desk's window holds only its own tools and results; the RCA agent reads one-line evidence, never raw logs. No window grows with the whole investigation. |
| **Rolling compaction** | A desk keeps its 3 newest tool results in full; older ones collapse to their opening but keep their citation id. For a desk making 8 calls at 8,000 characters: **288,000 → 175,500 characters resent, ≈39% fewer input tokens**, with no loss of citability. |
| **Per-tool output caps** | A job log may spend 16,000 characters; a branch list 2,000. Budgeted, not uniform. |

**(c) Against a single giant-context prompt.** Putting all logs, commits and docs into one window is
quadratic in resent context across turns, loses the middle of long contexts, and cannot parallelise.
EOPS bounds every window and runs desks concurrently, so **wall-clock scales with the slowest desk,
not the sum**.

**Honest sentence to use:** "We do not claim fewer total tokens than a single prompt. We claim bounded
context per step, parallel wall-clock, and a 39% reduction against the same architecture without
compaction — and we measure all of it per desk."

---

## 5. "What algorithm did you use?"

They will ask. Answer with five named components, not "we used an LLM".

1. **Supervisor planning with a constrained action space.** The planner may only assign desks that
   actually have connected tools; the plan is a typed object produced by a forced tool call and
   validated — an invalid plan gets exactly one repair attempt, then fails loudly. No free-text plans.
2. **Per-desk ReAct loop under budgets** (Yao et al. 2023). Think → call a read tool → observe →
   repeat, bounded by 8 tool calls and a wall-clock budget. On exhaustion the harness *forces*
   `submit_findings`, so a desk always reports what it has rather than hanging.
3. **Fan-out / fan-in over a shared state.** Implemented as LangGraph `Send` (map) with
   reducer-merged state channels (reduce) and a durable checkpoint, so the run survives restart and
   can pause at the approval interrupt for hours. This is the "shared investigation state" of the paper.
4. **Bounded inter-agent questioning.** A desk may ask another desk a precise question; the broker
   enforces per-agent and global question budgets and returns an evidence-backed answer, preventing
   the unbounded chat loops that make AutoGen-style systems expensive.
5. **Hybrid retrieval with reciprocal-rank fusion.** Dense embeddings (Chroma) + BM25, fused by RRF,
   for the Engineering Memory Layer — better than either alone on short technical queries.
6. **Deterministic confidence calibration.** Code, not the model, caps confidence: no supporting
   evidence → ≤0.2; evidence from a single source type → ≤0.6; any contradicting evidence → −0.1.

If they ask "is there a novel algorithm?" — be honest and reframe:

> "The novelty is not a new learning algorithm. It is a **coordination and verification protocol**:
> constrained planning, budgeted parallel ReAct desks, enforced evidence citation, and deterministic
> confidence calibration. Those are the parts that make LLM output trustworthy enough for operations."

---

## 6. Novelty table — what is uniquely yours

| Capability | Ahmed'23 | RCACopilot | Roy'24 agent | RCAgent | SWE-agent | **EOPS** |
|---|---|---|---|---|---|---|
| Multi-source investigation | ✗ | ✓ (via handlers) | partial | ✓ | ✗ | ✓ |
| **Parallel specialised agents** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| **Agent-to-agent questioning (budgeted)** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| **Customer-side, any stack via connector catalog (MCP)** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| **Enforced evidence citation** | ✗ | ✗ | partial | partial | ✗ | **✓** |
| **Read-only by construction; writes need approval** | n/a | n/a | n/a | partial | ✗ | **✓** |
| Organisational knowledge via RAG | ✗ | TSGs | ✓ | ✗ | ✗ | ✓ |
| **Per-agent token accounting + context compaction** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Live observable investigation UI | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |

**Your sharpest single differentiator, if you may say only one:**

> "Every prior system is **provider-side**: built inside Microsoft's or Alibaba's own telemetry, with
> handlers written per alert type. EOPS is **customer-side and tool-agnostic** — a small team connects
> their own GitHub, database and hosting through a connector catalog, and the abilities route
> automatically to the desk that owns that system area. Adding a new tool needs no new agent and no
> new code."

---

## 7. Question bank

**Evidence and evaluation**

1. *"You have no results. Why should we accept this?"* — "The contribution is the architecture and a
   working implementation; the paper states that explicitly. Our protocol is defined against OpenRCA,
   AIOpsLab and controlled fault injection, with four metric families. I would rather report a measured
   11% than an unmeasured claim."
2. *"How do you know it is better than one LLM with a big context window?"* — Ablation: same tools,
   same model, single agent versus EOPS. We measure accuracy, unsupported-claim rate, wall-clock and
   tokens. Plus the structural argument: one window cannot parallelise and degrades in the middle.
3. *"What is your ground truth?"* — Injected faults (we know the cause), plus public benchmarks with
   labelled causes, plus expert-rated reports for realism.
4. *"Is your sample size meaningful?"* — No, and we say so. N = 20–30 injected faults and 6–10 engineers
   is a pilot. It is reported as a pilot.

**Technical**

5. *"How do you prevent hallucination?"* — Three layers: findings are **rejected by the harness** unless
   they cite a successful tool call; the RCA may only cite evidence ids that exist; confidence is capped
   by code, not by the model. Roy et al. showed tool grounding takes hallucination from 49% to 6% — we
   make that structural rather than hopeful.
6. *"What if a tool returns a prompt-injection payload inside a log line?"* — Tool output is wrapped as
   `<tool_output>` and treated as data; investigating agents hold **read-only** tools, so even a
   successful injection cannot change the customer's systems; any write needs human approval.
7. *"Why MCP and not direct APIs?"* — One integration contract instead of N bespoke clients; new tools
   arrive as connectors with an allowlist of abilities, routed to desks by capability. No agent changes.
8. *"Does this scale to hundreds of services?"* — Desks are per *system area*, not per service, so agent
   count is constant; depth comes from tools, and budgets bound each desk.
9. *"What model do you use? What if it is weak?"* — Model-agnostic through OpenRouter; the per-role model
   is configuration. Our claim is about the harness, which is why we measure the same harness across models.
10. *"What happens when a desk has no connector?"* — It is reported as "no connector" and listed under
    *what could not be checked*. Silence is never mistaken for absence of a problem.
11. *"Latency?"* — Bounded by budgets: 8 tool calls and 300 s per desk, 30 min per run; desks run
    concurrently. A pilot run on our own instance completed end to end in about 7.7 minutes.
12. *"Cost per incident?"* — Measured per desk by our token meter. Compaction removes about 39% of
    resent input. We report tokens and USD per investigation as a first-class metric — most papers do not.

**Scope and product**

13. *"Is this not just AIOps?"* — Classical AIOps detects anomalies in metrics. EOPS answers *why*, across
    code, config, data and docs, and cites evidence. Complementary: an alert can start an EOPS investigation.
14. *"Who is the user?"* — Small and mid-size SaaS teams with no dedicated SRE — exactly the teams that
    cannot afford Microsoft's internal tooling.
15. *"Why keep the human?"* — Because the best public results are ~11–15% autonomous resolution. A system
    that acts on that is dangerous; a system that *investigates* and hands over evidence is useful today.
16. *"What is your biggest risk?"* — Evaluation realism: injected faults are cleaner than production.
    Mitigation: public benchmarks plus real incidents on our own deployed site.

**Personal**

17. *"What was the hardest engineering problem?"* — Keeping agents honest. The first version produced
    confident findings with no traceable source; we now reject uncited findings in the harness and cap
    confidence in code.
18. *"What would you do with more time?"* — The full measurement study, graph-augmented retrieval over
    code–service–document relations, and learning from accepted versus rejected recommendations.

---

## 8. Things not to say

- ❌ "Our system reduces MTTR by X%" — you have not measured it. Say "targets" or "is designed to".
- ❌ "It is fully automated" — your contribution is *decision support*; that is a strength, not a hedge.
- ❌ "Multi-agent is always better" — Roy et al. found accuracy roughly equal; the gain is honesty and
  coverage.
- ❌ "No one has done this" — RCACopilot, RCAgent and ITBench exist. Say "no one has done it
  **customer-side, across heterogeneous tools, with enforced evidence citation**."
- ❌ Guessing a number on the spot. "I do not have that measured yet; it is in our evaluation plan" is a
  perfectly strong answer and chairpersons respect it.

---

## 9. Night-before checklist

- [ ] Read §2 aloud until you can name the eight works without the sheet
- [ ] Rehearse the 8-minute script twice with a timer; cut to fit, never rush the evaluation slide
- [ ] Memorise four numbers: **52.5 h** median TTM, **0.766** RCACopilot Micro-F1, **6% vs 49%**
      hallucination (ReAct vs retrieval), **11.34%** best OpenRCA score
- [ ] Have two screenshots ready: the War Room mid-investigation, and a report with cited evidence
- [ ] Prepare the 20-second answer to "what is novel" (§6) — you will be asked it in some form
- [ ] Sleep. A calm delivery of an honest position paper beats a nervous oversell every time.
