"""Root-cause analysis over all collected evidence, with confidence capped by code."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from forgeops.engine import prompts
from forgeops.engine.llm.base import LLM, Message
from forgeops.engine.llm.structured import ask_structured
from forgeops.engine.models import (
    RCA, AgentError, AgentQuestion, Evidence, Incident, Plan, RcaCategory, Recommendation, TimelineItem,
)
from forgeops.engine.supervisor import incident_text, evidence_lines


class RecommendationDraft(BaseModel):
    title: str
    description: str
    action: Literal["none", "github_issue"] = "none"
    parameters: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False


class RcaDraft(BaseModel):
    summary: str
    failure_point: str
    category: RcaCategory
    confidence: float = Field(ge=0.0, le=1.0)
    timeline: list[TimelineItem] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    alternative_hypotheses: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommendations: list[RecommendationDraft] = Field(default_factory=list)


def apply_confidence_caps(rca: RCA, evidence: list[Evidence]) -> RCA:
    by_id = {e.id: e for e in evidence}
    confidence = rca.confidence
    supporting = [by_id[i] for i in rca.supporting_evidence if i in by_id]
    if not supporting:
        confidence = min(confidence, 0.2)
    elif len({e.connector_type for e in supporting}) == 1:
        confidence = min(confidence, 0.6)
    if any(i in by_id for i in rca.contradicting_evidence):
        confidence = max(0.0, confidence - 0.1)
    return rca.model_copy(update={"confidence": round(confidence, 2)})


async def run_rca(
    llm: LLM, incident: Incident, plan: Plan, evidence: list[Evidence], questions: list[AgentQuestion],
    errors: list[AgentError], missing: list[str], now: datetime | None = None,
) -> RCA:
    known = {e.id for e in evidence}

    def check(draft: RcaDraft) -> str | None:
        cited = set(draft.supporting_evidence) | set(draft.contradicting_evidence) | {
            i for item in draft.timeline for i in item.evidence_ids}
        unknown = sorted(cited - known)
        if unknown:
            return (f"evidence ids {', '.join(unknown)} do not exist. "
                    f"Use only: {', '.join(sorted(known)) or 'none'}")
        return None

    answered = [q for q in questions if q.status == "answered"]
    content = "\n\n".join([
        "Evidence:\n" + evidence_lines(evidence),
        incident_text(incident),
        f"Plan: {plan.summary}\nHypotheses: {'; '.join(plan.hypotheses) or 'n/a'}",
        "Questions between desks:\n" + ("\n".join(
            f"- {q.from_agent.value} asked {q.to_agent.value}: {q.question} -> {(q.answer or '')[:300]}"
            for q in answered) or "none"),
        "Errors during the investigation:\n" + ("\n".join(f"- {e.agent.value}: {e.message}" for e in errors)
                                                or "none"),
        "Areas that could not be checked:\n" + ("\n".join(f"- {m}" for m in missing) or "none"),
    ])
    draft = await ask_structured(
        llm, purpose="rca", model_role="rca",
        system=prompts.system("rca", now=(now.isoformat(timespec="seconds") if now else "unknown")),
        messages=[Message(role="user", content=content)], schema=RcaDraft, tool_name="submit_rca",
        tool_description="Submit the root-cause analysis.", check=check, max_tokens=6000,
    )
    recommendations = [
        Recommendation(id=f"rec_{n}", title=r.title, description=r.description, action=r.action,
                       parameters=r.parameters, requires_approval=r.action != "none")
        for n, r in enumerate(draft.recommendations, start=1)
    ]
    missing_all = list(dict.fromkeys([*draft.missing_information, *missing]))
    rca = RCA(**draft.model_dump(exclude={"recommendations", "missing_information"}),
              missing_information=missing_all, recommendations=recommendations)
    return apply_confidence_caps(rca, evidence)
