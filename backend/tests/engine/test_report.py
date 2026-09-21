from forgeops.engine.models import (
    RCA, ActionResult, AgentError, AgentId, AgentQuestion, Artifact, Capability, Decision, Evidence,
    Incident, Plan, Recommendation,
)
from forgeops.engine.report import render_report


def _state():
    evidence = [Evidence(id="ev_1", agent=AgentId.code, capability=Capability.code, connection_id="c",
                         connector_type="github", finding="Commit a1b2 lowered the DB pool to 5",
                         failure_point="config/db.ts:4",
                         artifacts=[Artifact(type="commit", ref="a1b2", url="https://github.com/o/r/commit/a1b2")],
                         severity="high", confidence=0.9, tool_call_ids=["tc_1"])]
    rca = RCA(summary="The deploy lowered the DB pool, so checkout requests queue.",
              failure_point="config/db.ts:4", category="config_change", confidence=0.85,
              supporting_evidence=["ev_1"], missing_information=["No error tracker connected"],
              recommendations=[Recommendation(id="rec_1", title="Restore pool size", description="Set 20",
                                              action="github_issue", parameters={"title": "t"},
                                              requires_approval=True)])
    return {
        "workspace_id": "ws", "investigation_id": "inv_1",
        "incident": Incident(text="Checkout is slow", source="chat"),
        "plan": Plan(summary="Check the deploy"), "evidence": evidence, "rca": rca,
        "questions": [AgentQuestion(id="q_1", from_agent=AgentId.database, to_agent=AgentId.code,
                                    question="What changed?", answer="a1b2", status="answered")],
        "errors": [AgentError(agent=AgentId.observability, message="timeout")],
        "warnings": [], "tool_calls": [],
        "decision": Decision(kind="approve", approved_recommendation_ids=["rec_1"], decided_by="usr_1",
                             channel="web"),
        "action_results": [ActionResult(recommendation_id="rec_1", status="done", detail="created",
                                        url="https://github.com/o/r/issues/7")],
    }


def test_report_contains_the_essentials():
    md = render_report(_state())
    for expected in ["Checkout is slow", "The deploy lowered the DB pool", "config/db.ts:4", "85%",
                     "ev_1", "Commit a1b2 lowered the DB pool to 5", "https://github.com/o/r/commit/a1b2",
                     "What could not be checked", "No error tracker connected", "Restore pool size",
                     "issues/7", "What changed?", "timeout"]:
        assert expected in md, expected


def test_report_without_rca_says_so():
    state = _state() | {"rca": None, "decision": None, "action_results": []}
    assert "No root cause was determined" in render_report(state)
