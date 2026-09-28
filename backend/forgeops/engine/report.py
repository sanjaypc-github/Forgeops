"""Deterministic Markdown report built from the investigation state (no LLM involved)."""

from collections.abc import Mapping
from typing import Any


def _cell(text: str | None) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _run_cost(usage: Any, saved_chars: int) -> list[str]:
    """What the investigation cost, per desk, so the owner can see where the tokens went."""
    out = ["", "## Run cost", "",
           f"**{usage.calls} model calls · {usage.input_tokens:,} in · {usage.output_tokens:,} out"
           f" · {usage.total_tokens:,} tokens total**", ""]
    if usage.cached_tokens or usage.saved_tokens or saved_chars:
        savings = []
        if usage.cached_tokens:
            savings.append(f"{usage.cached_tokens:,} input tokens served from the provider's cache")
        if usage.saved_tokens or saved_chars:
            savings.append(f"about {max(usage.saved_tokens, saved_chars // 4):,} input tokens saved by "
                           "compacting older tool output")
        out += ["Savings: " + "; ".join(savings) + ".", ""]
    if usage.by_agent:
        out += ["| Desk | Calls | Input | Output |", "|---|---|---|---|"]
        for agent, spent in sorted(usage.by_agent.items(), key=lambda kv: -kv[1].input_tokens):
            out.append(f"| {agent} | {spent.calls} | {spent.input_tokens:,} | {spent.output_tokens:,} |")
    return out


def render_report(state: Mapping[str, Any], usage: Any = None) -> str:
    incident = state["incident"]
    rca = state.get("rca")
    plan = state.get("plan")
    evidence = state.get("evidence") or []
    decision = state.get("decision")
    results = {r.recommendation_id: r for r in state.get("action_results") or []}

    out = [f"# Investigation report — {state['investigation_id']}", "",
           f"**Problem reported:** {incident.text}", ""]
    if plan:
        out += [f"**Plan:** {plan.summary}", ""]

    out.append("## Root cause")
    if rca:
        out += [rca.summary, "",
                f"- **Failure point:** `{rca.failure_point}`",
                f"- **Category:** {rca.category.replace('_', ' ')}",
                f"- **Confidence:** {round(rca.confidence * 100)}%",
                f"- **Supporting evidence:** {', '.join(rca.supporting_evidence) or 'none'}"]
        if rca.contradicting_evidence:
            out.append(f"- **Contradicting evidence:** {', '.join(rca.contradicting_evidence)}")
        if rca.alternative_hypotheses:
            out.append(f"- **Other explanations considered:** {'; '.join(rca.alternative_hypotheses)}")
        if rca.timeline:
            out += ["", "## Timeline", ""]
            out += [f"- {item.ts.isoformat() if item.ts else 'time unknown'} — {item.description}"
                    + (f" ({', '.join(item.evidence_ids)})" if item.evidence_ids else "")
                    for item in rca.timeline]
    else:
        out.append("No root cause was determined.")

    out += ["", "## Evidence", ""]
    if evidence:
        out += ["| Id | Desk | Source | Finding | Failure point | Confidence | Link |",
                "|---|---|---|---|---|---|---|"]
        for e in evidence:
            first = e.artifacts[0] if e.artifacts else None
            link = (first.url or first.ref) if first else ""
            out.append(f"| {e.id} | {e.agent.value} | {e.connector_type} | {_cell(e.finding)} | "
                       f"{_cell(e.failure_point)} | {round(e.confidence * 100)}% | {_cell(link)} |")
    else:
        out.append("No evidence was collected.")

    questions = state.get("questions") or []
    if questions:
        out += ["", "## Questions between desks", ""]
        out += [f"- **{q.from_agent.value} → {q.to_agent.value}:** {q.question} — "
                f"{_cell((q.answer or q.reason or q.status)[:300])}" for q in questions]

    missing = rca.missing_information if rca else []
    out += ["", "## What could not be checked", ""]
    out += [f"- {m}" for m in missing] or ["- Nothing reported."]

    if rca and rca.recommendations:
        out += ["", "## Recommendations", ""]
        for rec in rca.recommendations:
            line = f"- **{rec.title}** ({rec.id}): {rec.description}"
            if rec.action != "none":
                approved = bool(decision and decision.kind == "approve"
                                and rec.id in decision.approved_recommendation_ids)
                line += f" — action `{rec.action}`: {'approved' if approved else 'not approved'}"
                if rec.id in results:
                    r = results[rec.id]
                    line += f", {r.status}" + (f" ({r.url})" if r.url else f" ({r.detail})")
            out.append(line)

    errors = state.get("errors") or []
    if errors:
        out += ["", "## Errors during the investigation", ""]
        out += [f"- {e.agent.value}: {e.message}" for e in errors]

    if usage is not None and usage.calls:
        out += _run_cost(usage, state.get("context_saved_chars") or 0)

    if decision:
        out += ["", f"_Decision: {decision.kind.replace('_', ' ')} via {decision.channel}"
                + (f" — {decision.note}" if decision.note else "") + "_"]
    return "\n".join(out) + "\n"
