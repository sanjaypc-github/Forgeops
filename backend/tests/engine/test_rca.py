from forgeops.engine.models import RCA, AgentId, Capability, Evidence, Incident, Plan
from forgeops.engine.rca import apply_confidence_caps, run_rca
from tests.engine.fakes import ScriptedLLM, call


def ev(i, ctype):
    return Evidence(id=f"ev_{i}", agent=AgentId.code, capability=Capability.code, connection_id="c",
                    connector_type=ctype, finding=f"f{i}", failure_point=None, artifacts=[],
                    severity="high", confidence=0.9, limitations=None, tool_call_ids=["tc_1"])


def rca(conf, support, contra=()):
    return RCA(summary="s", failure_point="fp", category="code_change", confidence=conf, timeline=[],
               supporting_evidence=list(support), contradicting_evidence=list(contra),
               alternative_hypotheses=[], missing_information=[], recommendations=[])


def test_caps():
    evidence = [ev(1, "github"), ev(2, "supabase"), ev(3, "github")]
    assert apply_confidence_caps(rca(0.9, []), evidence).confidence == 0.2
    assert apply_confidence_caps(rca(0.9, ["ev_1", "ev_3"]), evidence).confidence == 0.6
    assert apply_confidence_caps(rca(0.9, ["ev_1", "ev_2"]), evidence).confidence == 0.9
    assert apply_confidence_caps(rca(0.9, ["ev_1", "ev_2"], ["ev_3"]), evidence).confidence == 0.8
    assert apply_confidence_caps(rca(0.05, [], ["ev_3"]), evidence).confidence == 0.0


ARGS = dict(summary="Pool too small after deploy", failure_point="config/db.ts:4",
            category="config_change", confidence=0.85, timeline=[], contradicting_evidence=[],
            alternative_hypotheses=[], missing_information=[],
            recommendations=[{"title": "Restore pool", "description": "set 20",
                              "action": "github_issue", "parameters": {"title": "t", "body": "b"},
                              "requires_approval": False}])


async def test_rca_rejects_unknown_evidence_ids_and_numbers_recommendations():
    llm = ScriptedLLM({"rca": [call("submit_rca", supporting_evidence=["ev_9"], **ARGS),
                               call("submit_rca", supporting_evidence=["ev_1", "ev_2"], **ARGS)]})
    result = await run_rca(llm, Incident(text="slow", source="chat"), Plan(summary="p"),
                           [ev(1, "github"), ev(2, "supabase")], [], [], ["Sentry not connected"])
    assert "ev_9" in llm.requests[1].messages[-1].content
    first_message = llm.requests[0].messages[0].content
    assert "- ev_1 | code | github" in first_message and "Sentry not connected" in first_message
    rec = result.recommendations[0]
    assert rec.id == "rec_1" and rec.requires_approval is True  # never trusted from the model
    assert result.confidence == 0.85
