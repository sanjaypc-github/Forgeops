# 10 — Results and measurements

Feeds **Chapter 5 (Results and Discussion)**.

> **The single most important instruction in this pack:** every number below is tagged
> **[MEASURED]**, **[COMPUTED]** or **[PLANNED]**. Carry the tag's meaning into the report's wording.
> Do not promote a computed or planned number into a result. This project is a working prototype with
> a defined evaluation protocol; the large-scale empirical study has not yet been run.

---

## 10.1 What exists today

| # | Item | Tag | Value |
|---|---|---|---|
| 1 | Implementation size | [MEASURED] | 66 Python files (≈5,340 lines) + 35 TypeScript files (≈3,590 lines); 45 commits |
| 2 | Agent roles implemented | [MEASURED] | 9 (Supervisor, 6 specialist desks, RCA, Action) |
| 3 | Connectors working | [MEASURED] | 3 (GitHub, Supabase, knowledge vault) + 13 declared "coming soon" |
| 4 | REST endpoints | [MEASURED] | 21 |
| 5 | Event types | [MEASURED] | 27 |
| 6 | Database tables | [MEASURED] | 9, in a private schema |
| 7 | Automated tests | [MEASURED] | 232 (198 backend + 34 frontend); see `09-testing.md` for the current pass state |
| 8 | Full backend suite run | [MEASURED] | 195 tests passed in 744 s on 28 September 2026 |
| 9 | Pilot investigation, end to end | [MEASURED] | ≈461 s (≈7.7 min) on a free-tier model with the knowledge connector only |

**About item 9 — say it exactly like this:** *"A pilot investigation on our own deployment completed
end to end in approximately 7.7 minutes using a free-tier model with a single connector. This is an
engineering observation of the implemented pipeline, not an evaluation result: the incident was not
drawn from a benchmark and the output was not scored against ground truth."*

## 10.2 Context compaction — the quantitative result

This is the project's one quantified efficiency result. It is **[COMPUTED]** from the system's own
configured limits, and the mechanism is verified by a unit test that asserts the saving at runtime.

### The mechanism being measured

Large-language-model APIs are **stateless**: on every turn the entire conversation is retransmitted.
In an agent loop, therefore, the first tool result is sent again on every subsequent turn. With *n*
tool calls, the number of result-copies transmitted is 1 + 2 + … + *n* = n(n+1)/2 — quadratic in the
number of steps.

Compaction keeps the newest *k* results whole and collapses older ones to their opening *s*
characters, retaining the `call_id` so findings can still cite them.

### Formulae

With a per-result cap of *C* characters:

```
Without compaction:   T(n) = C · n(n+1)/2
With compaction:      T'(n) = C · [k·n − k(k−1)/2]  +  s · (n−k)(n−k+1)/2      for n ≥ k
```

### Results with the shipped defaults (C = 8,000, k = 3, s = 500)

| Tool calls per desk | Without compaction (chars) | With compaction (chars) | Reduction |
|---|---|---|---|
| 2 | 24,000 | 24,000 | 0.0% |
| 4 | 80,000 | 72,500 | 9.4% |
| 6 | 168,000 | 123,000 | 26.8% |
| **8 (the configured budget)** | **288,000** | **175,500** | **39.1%** |
| 10 | 440,000 | 230,000 | 47.7% |
| 12 | 624,000 | 286,500 | 54.1% |

At the default budget of eight tool calls this is ≈72,000 versus ≈43,900 tokens for one desk
(at roughly four characters per token).

**The property worth discussing:** the saving *grows with investigation depth*. Shallow
investigations gain nothing; the difficult incidents that need many tool calls gain the most. That is
the correct shape for this problem.

**Honest wording for the report:** *"With the system's configured limits, and assuming each result
reaches its cap, a desk performing eight tool calls retransmits 288,000 characters of context; with
rolling compaction this falls to 175,500 — a reduction of 39.1%. The runtime meter records the actual
saving for each run, and a unit test asserts that citations survive compaction."*

Source: `backend/forgeops/engine/budgets.py`, `specialist.py` (`_view`),
test `test_older_tool_output_is_collapsed_but_still_citable`.

## 10.2b Triage — a measured before-and-after

This is the project's second quantified result, and unlike §10.2 it is **[MEASURED]** on a real run
rather than computed.

**Before.** The question *"is all the connectors connected successfully?"* was treated as an incident
and investigated by the full agent pipeline. Recorded in `investigations.usage`:

| Desk | Model calls | Input tokens | Share |
|---|---|---|---|
| Knowledge | 12 | 50,085 | 72% |
| Database | 4 | 11,774 | 17% |
| Supervisor | 3 | 5,251 | 8% |
| RCA | 1 | 2,185 | 3% |
| **Total** | **20** | **69,295 in + 5,555 out = 74,850** | 7,688 saved by compaction |

The Knowledge desk spent nearly three quarters of the run searching a vault that contained nothing
about the subject, because nothing stopped it after the first fruitless searches.

**The diagnosis.** The question is not an incident. It asks about ForgeOps' own connectors, and the
answer is already in ForgeOps' database.

**After.** A rule-based classifier (`engine/triage.py`) runs before the graph. A platform question is
answered from the connections table with **zero model calls and zero tokens**; an incident is
investigated exactly as before; anything ambiguous is treated as an incident, because wrongly
skipping a real incident is far worse than spending tokens. A second mechanism stops a desk after
`empty_results_before_stop` consecutive fruitless searches.

| Metric | Before | After |
|---|---|---|
| Model calls for that question | 20 | **0** |
| Tokens | 74,850 | **0** |
| Answer quality | a negative finding from the wrong source | the actual connection status, from records |

Tests: `tests/engine/test_triage.py` (classification, including the original message verbatim),
`tests/test_chat_api.py` (asserts the model is never called), and
`tests/engine/test_specialist.py` (asserts a desk stops after two empty results).

## 10.3 Other efficiency properties (qualitative, not yet quantified)

| Property | Status | Explanation |
|---|---|---|
| Bounded context per step | [MEASURED as a design property] | A desk's window contains only its own tools and results; the RCA agent reads one-line evidence, never raw logs. No window grows with total investigation length |
| Parallel wall-clock | [MEASURED as a design property] | Desks fan out through LangGraph `Send`; elapsed time follows the slowest desk rather than the sum. The speed-up factor has not yet been measured against a sequential baseline |
| Prompt-prefix caching | [IMPLEMENTED, unmeasured] | System prompts are byte-identical across a desk's turns; cached tokens are reported when the provider supports it |
| Per-tool output caps | [IMPLEMENTED] | 16,000 characters for a CI job log, 2,000 for a branch list, and so on |

**Do not claim** that the system uses fewer total tokens than a single large prompt. A multi-agent
system uses more total tokens; what it buys is bounded context per step, parallel wall-clock and
enforced grounding. State the trade-off explicitly — doing so strengthens the report.

## 10.4 The evaluation protocol (not yet executed) — [PLANNED]

Four metric families:

| Family | Metrics | Compared against |
|---|---|---|
| **Correctness** | Root-cause accuracy @1 and @3; failure-point localisation (file, service, query or configuration) | Single ReAct agent with the same tools; one-shot prompt with all context |
| **Honesty** | Unsupported-claim rate (statements with no verifiable citation); citation validity | Published figures from Roy et al.: 6% / 18% / 49% |
| **Cost** | Input, output and cached tokens per investigation and per desk; tool calls; cost in currency | The same architecture without compaction |
| **Time** | Wall-clock to root cause; human time to a decision | Manual investigation of the same injected fault |

Three settings, in increasing strength:

1. **Public benchmarks** — OpenRCA (335 real failures) and AIOpsLab fault scenarios. Report honestly
   against published baselines (the best model with a purpose-built agent solved 11.34% of OpenRCA).
2. **Controlled fault injection** — 20–30 faults of known type (configuration regression, slow query,
   failed deployment, broken content, expired credential) on a live stack.
3. **Human study** — 6–10 engineers diagnosing with and without the system; time to a correct
   diagnosis and a usefulness rating.

Five ablations, designed to isolate the **architecture** rather than the model:

- multi-agent versus a single agent holding the same tools;
- with and without the Engineering Memory Layer;
- with and without enforced evidence citation;
- with and without rolling compaction;
- parallel versus sequential desk execution.

## 10.5 Expected discussion points

The report's discussion section can argue the following, provided each is marked as expectation
rather than finding:

1. **Coverage over accuracy.** Parallel specialists should raise the probability that the relevant
   evidence is collected at all, which is the precondition for a correct diagnosis.
2. **Honesty is architectural.** Because the harness rejects uncited findings, the unsupported-claim
   rate should be structurally lower than for systems that merely ask a model to cite sources.
3. **Cost is predictable.** Budgets bound the worst case; metering makes the typical case visible.
   Most published systems report neither.
4. **The human gate is justified by the literature**, not by caution alone: 11–15% autonomous
   resolution on public benchmarks is not a basis for automatic action.

## 10.6 Threats to validity — state these in the report

| Threat | Why it matters | Mitigation planned |
|---|---|---|
| Injected faults are cleaner than production incidents | Over-estimates performance | Add public benchmarks and real incidents on a live site |
| A single team's documentation in the knowledge vault | Retrieval quality is corpus-dependent | Report corpus size and composition with results |
| One model family | Results may not transfer | The harness is model-agnostic; repeat the protocol across models |
| Small sample in the human study | Weak statistical power | Report as a pilot with effect sizes, not as a significance claim |
| The pilot timing used a free-tier model | Latency is provider-dependent | Report model, provider and date with every timing |
