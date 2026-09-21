"""The Supervisor: plans the investigation, reviews evidence, answers follow-up questions."""

from datetime import datetime

from pydantic import BaseModel, Field

from forgeops.engine import prompts
from forgeops.engine.llm.base import LLM, LLMRequest, Message
from forgeops.engine.llm.structured import ask_structured
from forgeops.engine.models import (
    RCA, SPECIALISTS, AgentId, AgentTask, Capability, Evidence, Incident, Plan, SkippedAgent,
)
from forgeops.engine.roster import PROFILES

MAX_FOLLOW_UPS = 3


class TaskDraft(BaseModel):
    agent: AgentId
    objective: str
    hints: list[str] = Field(default_factory=list)


class NotRelevant(BaseModel):
    agent: AgentId
    reason: str


class PlanDraft(BaseModel):
    summary: str
    affected_service: str | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    hypotheses: list[str] = Field(default_factory=list)
    tasks: list[TaskDraft] = Field(default_factory=list)
    not_relevant: list[NotRelevant] = Field(default_factory=list)


class ReviewDraft(BaseModel):
    sufficient: bool
    reason: str
    follow_up_tasks: list[TaskDraft] = Field(default_factory=list)


class Review(BaseModel):
    sufficient: bool
    reason: str
    follow_up_tasks: list[AgentTask] = Field(default_factory=list)


def _desk_lines(agents: dict[AgentId, list[Capability]] | list[AgentId]) -> str:
    if not agents:
        return "- none"
    if isinstance(agents, dict):
        return "\n".join(
            f"- {a.value}: {PROFILES[a].title}. {PROFILES[a].focus} Capabilities: "
            f"{', '.join(c.value for c in caps)}." for a, caps in agents.items())
    return "\n".join(f"- {a.value}: {PROFILES[a].title}" for a in agents)


def incident_text(incident: Incident) -> str:
    lines = [f"Problem reported ({incident.source}): {incident.text}"]
    if incident.service_hint:
        lines.append(f"Service mentioned: {incident.service_hint}")
    if incident.window_start or incident.window_end:
        lines.append(f"Time window given (UTC): {incident.window_start or '?'} to {incident.window_end or 'now'}")
    if incident.notes:
        lines.append("Additional notes from the user: " + " | ".join(incident.notes))
    return "\n".join(lines)


def _task_problems(tasks: list[TaskDraft], connected: dict[AgentId, list[Capability]]) -> list[str]:
    problems = []
    for task in tasks:
        if task.agent not in SPECIALISTS:
            problems.append(f"{task.agent.value} is not a specialist desk")
        elif task.agent not in connected:
            problems.append(f"{task.agent.value} has no connected tools and cannot be assigned")
    agents = [t.agent for t in tasks]
    if len(agents) != len(set(agents)):
        problems.append("assign at most one task per desk")
    return problems


async def plan_investigation(
    llm: LLM, incident: Incident, connected: dict[AgentId, list[Capability]], service_map: str, now: datetime
) -> Plan:
    if not connected:
        return Plan(summary="No connectors are connected",
                    skipped=[SkippedAgent(agent=a, reason="no connector") for a in SPECIALISTS])

    def check(draft: PlanDraft) -> str | None:
        problems = _task_problems(draft.tasks, connected)
        if not draft.tasks:
            problems.append("assign at least one connected desk")
        return "; ".join(problems) or None

    unavailable = [a for a in SPECIALISTS if a not in connected]
    draft = await ask_structured(
        llm, purpose="plan", model_role="supervisor",
        system=prompts.system("supervisor_plan", now=now.isoformat(timespec="seconds"),
                              available_agents=_desk_lines(connected),
                              unavailable_agents=_desk_lines(unavailable),
                              service_map=service_map.strip() or "(none provided)"),
        messages=[Message(role="user", content=incident_text(incident))],
        schema=PlanDraft, tool_name="submit_plan",
        tool_description="Submit the investigation plan.", check=check,
    )
    reasons = {n.agent: n.reason for n in draft.not_relevant}
    assigned = {t.agent for t in draft.tasks}
    skipped = [
        SkippedAgent(agent=a, reason="no connector" if a not in connected
                     else f"not relevant: {reasons.get(a, 'not selected by the supervisor')}")
        for a in SPECIALISTS if a not in assigned
    ]
    return Plan(
        summary=draft.summary, affected_service=draft.affected_service,
        window_start=draft.window_start or incident.window_start,
        window_end=draft.window_end or incident.window_end, hypotheses=draft.hypotheses,
        tasks=[AgentTask(agent=t.agent, objective=t.objective, hints=t.hints) for t in draft.tasks],
        skipped=skipped,
    )


def evidence_lines(evidence: list[Evidence]) -> str:
    if not evidence:
        return "(no evidence yet)"
    return "\n".join(
        f"- {e.id} | {e.agent.value} | {e.connector_type} | {e.finding} | failure point: "
        f"{e.failure_point or 'n/a'} | confidence {e.confidence:.2f}" for e in evidence)


async def review_evidence(
    llm: LLM, incident: Incident, plan: Plan, evidence: list[Evidence], notes: list[str],
    connected: dict[AgentId, list[Capability]], now: datetime | None = None,
) -> Review:
    def check(draft: ReviewDraft) -> str | None:
        problems = _task_problems(draft.follow_up_tasks, connected)
        if len(draft.follow_up_tasks) > MAX_FOLLOW_UPS:
            problems.append(f"at most {MAX_FOLLOW_UPS} follow-up tasks")
        return "; ".join(problems) or None

    content = "\n\n".join([
        incident_text(incident),
        f"Plan: {plan.summary}\nHypotheses: {'; '.join(plan.hypotheses) or 'n/a'}",
        "Evidence so far:\n" + evidence_lines(evidence),
        "User notes during the investigation: " + (" | ".join(notes) if notes else "none"),
    ])
    draft = await ask_structured(
        llm, purpose="review", model_role="supervisor",
        system=prompts.system("supervisor_review",
                              now=(now.isoformat(timespec="seconds") if now else "unknown"),
                              available_agents=_desk_lines(connected)),
        messages=[Message(role="user", content=content)],
        schema=ReviewDraft, tool_name="submit_review",
        tool_description="Decide whether the evidence is sufficient.", check=check,
    )
    return Review(
        sufficient=draft.sufficient or not draft.follow_up_tasks, reason=draft.reason,
        follow_up_tasks=[AgentTask(agent=t.agent, objective=t.objective, hints=t.hints)
                         for t in draft.follow_up_tasks],
    )


async def answer_followup(
    llm: LLM, incident: Incident, rca: RCA | None, evidence: list[Evidence], question: str,
    now: datetime | None = None,
) -> str:
    rca_text = (f"Root cause: {rca.summary}\nFailure point: {rca.failure_point}\n"
                f"Confidence: {rca.confidence:.2f}\nMissing: {'; '.join(rca.missing_information) or 'none'}"
                if rca else "No root-cause analysis is available yet.")
    content = "\n\n".join([incident_text(incident), rca_text, "Evidence:\n" + evidence_lines(evidence),
                           f"User question: {question}"])
    reply = await llm.complete(LLMRequest(
        purpose="followup", model_role="supervisor",
        system=prompts.system("supervisor_followup",
                              now=(now.isoformat(timespec="seconds") if now else "unknown")),
        messages=[Message(role="user", content=content)], max_tokens=800,
    ))
    return reply.text.strip()
