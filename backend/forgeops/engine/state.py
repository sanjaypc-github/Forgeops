"""LangGraph state. Lists written by parallel agents merge through `operator.add`."""

import operator
from typing import Annotated, TypedDict

from forgeops.engine.models import (
    RCA, ActionResult, AgentError, AgentQuestion, AgentTask, Decision, Evidence, Incident, Plan,
    ToolCallRecord,
)


class InvestigationState(TypedDict):
    workspace_id: str
    investigation_id: str
    incident: Incident
    capabilities: dict[str, list[str]]
    plan: Plan | None
    pending_tasks: list[AgentTask]
    evidence: Annotated[list[Evidence], operator.add]
    tool_calls: Annotated[list[ToolCallRecord], operator.add]
    questions: Annotated[list[AgentQuestion], operator.add]
    errors: Annotated[list[AgentError], operator.add]
    warnings: Annotated[list[str], operator.add]
    review_rounds: int
    followup_rounds: int
    rca: RCA | None
    decision: Decision | None
    action_results: Annotated[list[ActionResult], operator.add]
    report_markdown: str | None


class SpecialistInput(TypedDict):
    task: AgentTask
    incident: Incident
    plan_summary: str
