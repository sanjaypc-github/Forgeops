"""The investigation as a LangGraph: plan -> specialists (parallel) -> review -> rca -> approval -> action -> report."""

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.capabilities.runner import ToolRunner
from forgeops.engine.budgets import Budgets
from forgeops.engine.llm.base import LLM
from forgeops.engine.models import (
    ActionResult, AgentError, AgentId, AgentTask, Decision, Incident, ToolCallRecord,
)
from forgeops.engine.questions import QuestionBroker
from forgeops.engine.rca import run_rca
from forgeops.engine.report import render_report
from forgeops.engine.roster import PROFILES
from forgeops.engine.specialist import SpecialistLoop, SpecialistResult
from forgeops.engine.state import InvestigationState, SpecialistInput
from forgeops.engine.supervisor import plan_investigation, review_evidence
from forgeops.events.models import EventIn, EventType

ISSUE_TOOL = "github.create_issue"
_URL = re.compile(r"https?://\S+")


@dataclass
class RunDeps:
    llm: LLM
    registry: CapabilityRegistry
    tool_runner: ToolRunner
    emit: Callable[[EventIn], Awaitable[Any]]
    budgets: Budgets
    now: Callable[[], datetime]
    service_map: str
    notes: Callable[[], Awaitable[list[str]]]


def build_graph(deps: RunDeps, checkpointer):
    emit = deps.emit
    connected = deps.registry.connected_agents()
    context: dict[str, Any] = {"incident": None, "plan_summary": ""}

    def make_loop(agent: AgentId, *, broker, max_calls: int, seconds: float, purpose: str,
                  announce: bool) -> SpecialistLoop:
        return SpecialistLoop(llm=deps.llm, agent=agent, registry=deps.registry,
                              tool_runner=deps.tool_runner, emit=emit, budgets=deps.budgets,
                              broker=broker, max_tool_calls=max_calls, seconds=seconds,
                              colleagues=list(connected), purpose=purpose, announce=announce, now=deps.now)

    async def answer(from_agent: AgentId, to_agent: AgentId, question: str) -> SpecialistResult:
        task = AgentTask(agent=to_agent, objective=f"Answer this question from the "
                         f"{PROFILES[from_agent].title} desk using your tools: {question}")
        loop = make_loop(to_agent, broker=None, max_calls=deps.budgets.answer_tool_calls,
                         seconds=deps.budgets.answer_seconds, purpose="answer", announce=False)
        return await loop.run(task, context["incident"], context["plan_summary"])

    broker = QuestionBroker(answer=answer, available=set(connected), emit=emit, budgets=deps.budgets)

    # ----- nodes -------------------------------------------------------------------------------
    async def plan_node(state: InvestigationState) -> dict:
        await emit(EventIn(type=EventType.supervisor_started, agent=AgentId.supervisor.value,
                           data={"round": state["followup_rounds"]}))
        plan = await plan_investigation(deps.llm, state["incident"], connected, deps.service_map, deps.now())
        await emit(EventIn(type=EventType.plan_created, agent=AgentId.supervisor.value, data={
            "summary": plan.summary, "hypotheses": plan.hypotheses,
            "tasks": [{"agent": t.agent.value, "objective": t.objective} for t in plan.tasks],
            "window_start": plan.window_start.isoformat() if plan.window_start else None,
            "window_end": plan.window_end.isoformat() if plan.window_end else None}))
        for skipped in plan.skipped:
            await emit(EventIn(type=EventType.agent_skipped, agent=skipped.agent.value,
                               data={"reason": skipped.reason}))
        new_warnings = [w for w in deps.registry.warnings if w not in state.get("warnings", [])]
        return {"plan": plan, "pending_tasks": plan.tasks, "warnings": new_warnings,
                "capabilities": {a.value: [c.value for c in caps] for a, caps in connected.items()}}

    def to_specialists(state: InvestigationState) -> list[Send] | str:
        tasks = state["pending_tasks"]
        if not tasks:
            return "report"
        summary = state["plan"].summary if state["plan"] else ""
        return [Send("specialist", SpecialistInput(task=t, incident=state["incident"], plan_summary=summary))
                for t in tasks]

    async def specialist_node(payload: SpecialistInput) -> dict:
        context["incident"], context["plan_summary"] = payload["incident"], payload["plan_summary"]
        agent = payload["task"].agent
        loop = make_loop(agent, broker=broker, max_calls=deps.budgets.specialist_tool_calls,
                         seconds=deps.budgets.specialist_seconds, purpose="specialist", announce=True)
        result = await loop.run(payload["task"], payload["incident"], payload["plan_summary"])
        return {
            "evidence": result.evidence, "tool_calls": result.tool_calls, "questions": result.questions,
            "errors": [AgentError(agent=agent, message=result.error)] if result.error else [],
        }

    async def review_node(state: InvestigationState) -> dict:
        if state["review_rounds"] >= deps.budgets.review_rounds:
            await emit(EventIn(type=EventType.review_completed, agent=AgentId.supervisor.value,
                               data={"sufficient": True, "reason": "review limit reached", "follow_ups": []}))
            return {"pending_tasks": []}
        review = await review_evidence(deps.llm, state["incident"], state["plan"], state["evidence"],
                                       await deps.notes(), connected, deps.now())
        await emit(EventIn(type=EventType.review_completed, agent=AgentId.supervisor.value, data={
            "sufficient": review.sufficient, "reason": review.reason,
            "follow_ups": [{"agent": t.agent.value, "objective": t.objective} for t in review.follow_up_tasks]}))
        if review.sufficient:
            return {"pending_tasks": []}
        return {"pending_tasks": review.follow_up_tasks, "review_rounds": state["review_rounds"] + 1}

    def after_review(state: InvestigationState) -> list[Send] | str:
        if not state["pending_tasks"]:
            return "rca"
        return to_specialists(state)

    async def rca_node(state: InvestigationState) -> dict:
        await emit(EventIn(type=EventType.rca_started, agent=AgentId.rca.value, data={}))
        plan = state["plan"]
        missing = [f"{PROFILES[s.agent].title}: no connector" for s in plan.skipped if s.reason == "no connector"]
        missing += state.get("warnings", [])
        rca = await run_rca(deps.llm, state["incident"], plan, state["evidence"], state["questions"],
                            state["errors"], missing, deps.now())
        await emit(EventIn(type=EventType.rca_completed, agent=AgentId.rca.value, data={
            "summary": rca.summary, "failure_point": rca.failure_point, "category": rca.category,
            "confidence": rca.confidence, "supporting_evidence": rca.supporting_evidence}))
        await emit(EventIn(type=EventType.approval_requested, agent=AgentId.supervisor.value, data={
            "recommendations": [r.model_dump(mode="json") for r in rca.recommendations]}))
        return {"rca": rca}

    async def approval_node(state: InvestigationState) -> dict:
        raw = interrupt({"recommendations": [r.model_dump(mode="json") for r in state["rca"].recommendations]})
        decision = Decision.model_validate(raw)
        if decision.kind == "investigate_more" and state["followup_rounds"] >= deps.budgets.followup_rounds:
            limit_note = "further investigation limit reached"
            decision = decision.model_copy(update={
                "kind": "reject", "note": f"{decision.note} ({limit_note})" if decision.note else limit_note})
        granted = decision.kind == "approve"
        await emit(EventIn(type=EventType.approval_granted if granted else EventType.approval_rejected,
                           agent=AgentId.supervisor.value, data={
                               "kind": decision.kind, "note": decision.note, "decided_by": decision.decided_by,
                               "approved_recommendation_ids": decision.approved_recommendation_ids}))
        update: dict[str, Any] = {"decision": decision}
        if decision.kind == "investigate_more":
            incident: Incident = state["incident"]
            notes = [*incident.notes, decision.note] if decision.note else incident.notes
            update |= {"incident": incident.model_copy(update={"notes": notes}),
                       "followup_rounds": state["followup_rounds"] + 1, "review_rounds": 0}
        return update

    def after_approval(state: InvestigationState) -> str:
        decision: Decision = state["decision"]
        if decision.kind == "approve" and decision.approved_recommendation_ids:
            return "action"
        if decision.kind == "investigate_more":
            return "plan"
        return "report"

    async def action_node(state: InvestigationState) -> dict:
        decision: Decision = state["decision"]
        results: list[ActionResult] = []
        records: list[ToolCallRecord] = []
        for rec in state["rca"].recommendations:
            if rec.id not in decision.approved_recommendation_ids or rec.action == "none":
                continue
            await emit(EventIn(type=EventType.action_started, agent=AgentId.action.value,
                               data={"recommendation_id": rec.id, "action": rec.action}))
            if rec.action == "github_issue" and deps.registry.has_tool(ISSUE_TOOL):
                result, record = await deps.tool_runner.run(
                    agent=AgentId.action, tool_name=ISSUE_TOOL, arguments=rec.parameters, allowed={ISSUE_TOOL})
                records.append(record)
                url = next(iter(_URL.findall(result.content)), None) if result.ok else None
                outcome = ActionResult(recommendation_id=rec.id, status="done" if result.ok else "failed",
                                       detail=(result.content if result.ok else result.error or "failed")[:500],
                                       url=url.rstrip(").,") if url else None)
            else:
                outcome = ActionResult(recommendation_id=rec.id, status="unavailable",
                                       detail="GitHub connector with write access is not connected")
            results.append(outcome)
            await emit(EventIn(type=EventType.action_completed, agent=AgentId.action.value, data={
                "recommendation_id": rec.id, "status": outcome.status, "url": outcome.url,
                "detail": outcome.detail[:200]}))
        return {"action_results": results, "tool_calls": records}

    async def report_node(state: InvestigationState) -> dict:
        markdown = render_report(state)
        decision = state.get("decision")
        status = "rejected" if decision and decision.kind == "reject" else "completed"
        await emit(EventIn(type=EventType.report_ready, agent=AgentId.supervisor.value, data={}))
        await emit(EventIn(type=EventType.investigation_completed, agent=AgentId.supervisor.value,
                           data={"status": status}))
        return {"report_markdown": markdown}

    # ----- wiring ------------------------------------------------------------------------------
    graph = StateGraph(InvestigationState)
    graph.add_node("plan", plan_node)
    graph.add_node("specialist", specialist_node)
    graph.add_node("review", review_node)
    graph.add_node("rca", rca_node)
    graph.add_node("approval", approval_node)
    graph.add_node("action", action_node)
    graph.add_node("report", report_node)
    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", to_specialists, ["specialist", "report"])
    graph.add_edge("specialist", "review")
    graph.add_conditional_edges("review", after_review, ["specialist", "rca"])
    graph.add_edge("rca", "approval")
    graph.add_conditional_edges("approval", after_approval, ["action", "report", "plan"])
    graph.add_edge("action", "report")
    graph.add_edge("report", END)
    return graph.compile(checkpointer=checkpointer)
