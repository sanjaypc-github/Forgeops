# 13 — Limitations and future work

Feeds **Chapter 6 (Conclusion and Future Work)**. An examiner respects a limitations section that is
specific and honest far more than one that is vague and defensive.

---

## 13.1 Limitations

### L1 — No large-scale empirical evaluation yet
The contribution is an architecture and a working implementation. The protocol in
`10-results-and-measurements.md` is defined but has not been executed, so no accuracy figure for the
system exists. Everything reported as a result is either an implementation fact or a computed
property of the configuration.

### L2 — The efficiency result is computed, not benchmarked
The 39.1% context reduction follows from the configured limits assuming each tool result reaches its
cap. The runtime meter records the actual saving per run, but a study across many real investigations
has not been performed.

### L3 — Quality depends on the connected tools
If a team has no error tracker connected, the Observability desk has nothing to investigate. The
system reports the gap honestly rather than guessing, but the diagnosis is necessarily weaker. The
quality ceiling is set by the customer's own instrumentation.

### L4 — Quality depends on the underlying model
The harness constrains the model but cannot make a weak model reason well. Development used a
free-tier model, which is slower and less capable than current paid models. The architecture is
model-agnostic, so this is a configuration limit rather than a design limit — but it has not been
measured across models.

### L5 — Compaction is deliberately lossy
Older tool output collapses to its opening. Citations and the stored record survive, and an agent can
call the tool again, but a detail that mattered might be re-fetched rather than remembered. The
accuracy cost has not been measured; it is one of the planned ablations.

### L6 — One workspace in the interface
The data model supports multiple tenants, but the interface exposes a single workspace. Sign-up,
billing, roles beyond admin and tenant isolation testing are not implemented.

### L7 — A single write action
The only implemented write is creating a GitHub issue after approval, and it has not yet been
exercised against a real repository. Remediation actions — rollback, restart, scaling — are out of scope.

### L8 — Connector coverage
Three connectors work. Thirteen more are declared in the catalog as "coming soon". Cloudflare, Sanity
and Sentry need their tool names verified against live accounts before they can be pinned, because
upstream MCP servers rename tools between versions.

### L9 — Prompt injection is mitigated, not eliminated
Tool output is wrapped as data and investigating desks hold only read tools, so an injection cannot
cause a write. It could still mislead an analysis. The citation requirement limits the damage —
a reader can check the source — but the risk is not zero.

### L10 — Evaluation realism
Injected faults are cleaner than production incidents: single cause, known time window, no competing
noise. Results from fault injection will over-estimate performance on real incidents.

## 13.2 Future work

### Near term — completing what is designed
1. **Execute the evaluation protocol**: OpenRCA and AIOpsLab, then 20–30 injected faults, then a small
   human study, with all four metric families and the five ablations.
2. **Finish M4**: pin Cloudflare, Sanity and Sentry tool names against live accounts and add them to
   the catalog with their capabilities and output caps.
3. **Exercise the write path** end to end: an approved recommendation creating a real GitHub issue,
   with the audit trail verified.
4. **Report cost per investigation in currency**, not only in tokens, using per-model pricing.

### Medium term — strengthening the method
5. **Graph-augmented retrieval.** Today the Engineering Memory Layer retrieves text chunks. Building a
   graph over code, services, deployments and documents would let the Knowledge desk answer relational
   questions ("which service owns this table, and who changed it last?") rather than similarity
   questions. This is the natural successor to the current RAG design.
6. **Learning from decisions.** Every approval and rejection is already recorded in the audit log.
   Those labels can train a ranking of recommendations, or calibrate confidence empirically rather
   than by fixed caps.
7. **Adaptive budgets.** Budgets are currently static. A desk that is producing high-confidence
   evidence could be granted more calls, while an unproductive desk is stopped earlier.
8. **Cross-investigation memory.** Past investigations of the same service are strong evidence. Index
   completed reports and let the Knowledge desk retrieve them, closing the loop with the team's own
   incident history.

### Longer term — the product
9. **Multi-tenant SaaS**: sign-up, workspace isolation testing, roles, billing, and hosting.
10. **Alert-triggered investigations**: start automatically from a monitoring alert, so the
    investigation is already underway when the engineer opens the laptop.
11. **Suggested remediation with staged approval**: propose a specific change — a revert, a
    configuration value — and let a human approve it in one click, with rollback.
12. **Confidence-aware escalation**: when confidence is capped low because only one source supports
    the conclusion, automatically propose which connector would resolve the ambiguity.

## 13.3 How to phrase the conclusion

A conclusion that works for this project:

> This work presented EOPS, a supervisor-driven multi-agent platform for software incident
> investigation. Its contribution is a coordination and verification protocol rather than a new
> model: specialised agents investigate a team's own tools in parallel, a shared investigation state
> requires every finding to cite the tool call that produced it, confidence is calibrated in code,
> and all write actions are reserved for human approval. The architecture is implemented and
> operational, with 232 automated tests and measured context-efficiency properties. Published results
> showing that autonomous agents resolve only a small fraction of real incidents support the central
> design choice to build decision support rather than automation. The planned evaluation against
> public benchmarks and injected faults will determine how far this coordination protocol improves
> diagnostic quality and cost in practice.
