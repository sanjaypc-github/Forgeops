from datetime import UTC, datetime

from forgeops.engine.llm.base import LLMReply
from forgeops.engine.models import AgentId, Capability, Incident, Plan
from forgeops.engine.supervisor import answer_followup, plan_investigation, review_evidence
from tests.engine.fakes import ScriptedLLM, call

NOW = datetime(2026, 9, 21, 10, 0, tzinfo=UTC)
INC = Incident(text="Site very slow since the last deploy", source="chat")
CONNECTED = {AgentId.code: [Capability.code], AgentId.database: [Capability.database]}


def _plan_args(tasks, not_relevant=()):
    return dict(summary="Latency after deploy", affected_service="web", window_start=None,
                window_end=None, hypotheses=["bad deploy"], tasks=tasks,
                not_relevant=list(not_relevant))


async def test_plan_uses_connected_agents_and_skips_the_rest():
    llm = ScriptedLLM({"plan": [call("submit_plan", **_plan_args([
        {"agent": "code", "objective": "diff last deploy"},
        {"agent": "database", "objective": "slow queries last 2h"}]))]})
    plan = await plan_investigation(llm, INC, CONNECTED, "", NOW)
    assert [t.agent for t in plan.tasks] == [AgentId.code, AgentId.database]
    skipped = {s.agent: s.reason for s in plan.skipped}
    assert skipped[AgentId.frontend_hosting] == "no connector"
    assert AgentId.code not in skipped and len(skipped) == 4
    assert "code" in llm.requests[0].system and "Site very slow" in llm.requests[0].messages[0].content
    assert llm.requests[0].model_role == "supervisor"


async def test_connected_but_unused_agent_is_skipped_with_reason():
    llm = ScriptedLLM({"plan": [call("submit_plan", **_plan_args(
        [{"agent": "code", "objective": "diff"}],
        [{"agent": "database", "reason": "frontend-only symptom"}]))]})
    plan = await plan_investigation(llm, INC, CONNECTED, "", NOW)
    skipped = {s.agent: s.reason for s in plan.skipped}
    assert skipped[AgentId.database] == "not relevant: frontend-only symptom"


async def test_plan_rejects_unconnected_agents_via_repair():
    llm = ScriptedLLM({"plan": [
        call("submit_plan", **_plan_args([{"agent": "observability", "objective": "errors"}])),
        call("submit_plan", **_plan_args([{"agent": "code", "objective": "diff"}]))]})
    plan = await plan_investigation(llm, INC, CONNECTED, "", NOW)
    assert [t.agent for t in plan.tasks] == [AgentId.code]
    assert "observability" in llm.requests[1].messages[-1].content


async def test_plan_requires_at_least_one_task():
    llm = ScriptedLLM({"plan": [call("submit_plan", **_plan_args([])),
                                call("submit_plan", **_plan_args([{"agent": "code", "objective": "d"}]))]})
    plan = await plan_investigation(llm, INC, CONNECTED, "", NOW)
    assert len(plan.tasks) == 1 and "at least one" in llm.requests[1].messages[-1].content


async def test_no_connectors_means_no_llm_call():
    llm = ScriptedLLM({})
    plan = await plan_investigation(llm, INC, {}, "", NOW)
    assert plan.tasks == [] and llm.requests == []
    assert len(plan.skipped) == 6 and plan.summary == "No connectors are connected"


async def test_review_limits_follow_ups_to_connected_agents():
    plan = Plan(summary="s")
    llm = ScriptedLLM({"review": [call("submit_review", sufficient=False, reason="need code",
                                       follow_up_tasks=[{"agent": "code", "objective": "check PR"}])]})
    review = await review_evidence(llm, INC, plan, [], [], CONNECTED)
    assert not review.sufficient and review.follow_up_tasks[0].agent == AgentId.code


async def test_followup_answer_is_plain_text():
    llm = ScriptedLLM({"followup": [LLMReply(text="Because ev_1 shows the deploy at 13:58.")]})
    text = await answer_followup(llm, INC, None, [], "why the deploy?")
    assert text.startswith("Because ev_1") and llm.requests[0].tools == []
    assert "why the deploy?" in llm.requests[0].messages[0].content
