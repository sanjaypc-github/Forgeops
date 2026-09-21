import operator

import pytest
from pydantic import ValidationError

from forgeops.engine.models import (
    SPECIALISTS, AgentId, AgentTask, Artifact, Capability, Evidence, Recommendation,
)
from forgeops.engine.state import InvestigationState


def test_agent_ids_and_capabilities_are_exact():
    assert [a.value for a in AgentId] == [
        "supervisor", "code", "frontend_hosting", "backend_services", "database",
        "observability", "knowledge", "rca", "action"]
    assert [c.value for c in Capability] == [
        "code", "hosting", "backend", "content", "database", "errors", "logs", "metrics",
        "knowledge", "write"]
    assert AgentId.supervisor not in SPECIALISTS and len(SPECIALISTS) == 6


def test_tasks_only_for_specialists():
    AgentTask(agent=AgentId.database, objective="check slow queries")
    with pytest.raises(ValidationError):
        AgentTask(agent=AgentId.rca, objective="x")


def _evidence(**kw):
    base = dict(id="ev_1", agent=AgentId.code, capability=Capability.code, connection_id="con_1",
                connector_type="github", finding="Pool size lowered", failure_point="config/db.ts:4",
                artifacts=[], severity="high", confidence=0.8, limitations=None,
                tool_call_ids=["tc_1"])
    return Evidence(**(base | kw))


def test_evidence_requires_a_tool_call_and_valid_confidence():
    _evidence()
    with pytest.raises(ValidationError):
        _evidence(tool_call_ids=[])
    with pytest.raises(ValidationError):
        _evidence(confidence=1.5)


def test_artifact_excerpt_is_truncated():
    a = Artifact(type="log_lines", ref="q", excerpt="x" * 5000)
    assert len(a.excerpt) <= 2000


def test_write_recommendations_require_approval():
    Recommendation(id="r1", title="t", description="d", action="none", parameters={},
                   requires_approval=False)
    with pytest.raises(ValidationError):
        Recommendation(id="r2", title="t", description="d", action="github_issue",
                       parameters={}, requires_approval=False)


def test_parallel_lists_use_add_reducer():
    hints = InvestigationState.__annotations__
    for key in ("evidence", "tool_calls", "questions", "errors", "warnings", "action_results"):
        assert hints[key].__metadata__[0] is operator.add
