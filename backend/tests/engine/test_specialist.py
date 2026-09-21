from forgeops.capabilities.models import ToolResult, ToolSpec
from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.capabilities.runner import ToolRunner
from forgeops.engine.budgets import Budgets
from forgeops.engine.llm.base import LLMReply
from forgeops.engine.models import AgentId, AgentTask, Capability, Incident
from forgeops.engine.questions import QuestionBroker
from forgeops.engine.specialist import SpecialistLoop, SpecialistResult
from tests.engine.fakes import FakeConnector, ScriptedLLM, call, collect_events

SLOW = ToolSpec(name="supabase.slow_queries", description="Slow queries", capability=Capability.database,
                permission="read", input_schema={"type": "object", "properties": {}},
                connection_id="con_sb", connector_type="supabase")
TASK = AgentTask(agent=AgentId.database, objective="Find slow queries in the last hour")
INCIDENT = Incident(text="checkout is slow", source="chat")


async def _loop(script, max_calls=8, broker=None, colleagues=()):
    conn = FakeConnector("con_sb", "supabase", [SLOW], {
        "supabase.slow_queries": ToolResult(ok=True, content="orders_by_user 4200 ms (seq scan)")})
    reg = await CapabilityRegistry.build([conn])
    events, emit = collect_events()
    llm = ScriptedLLM(script)
    loop = SpecialistLoop(llm=llm, agent=AgentId.database, registry=reg,
                          tool_runner=ToolRunner(reg, emit, Budgets()), emit=emit, budgets=Budgets(),
                          broker=broker, max_tool_calls=max_calls, seconds=30,
                          colleagues=list(colleagues))
    return loop, llm, events, conn


def _call_id(message) -> str:
    return message.content.split('call_id="')[1].split('"')[0]


def _finding(tool_call_ids, **kw):
    return {"finding": "orders_by_user does a sequential scan", "failure_point": "orders_by_user query",
            "artifacts": [{"type": "query_stats", "ref": "orders_by_user", "excerpt": "4200 ms"}],
            "severity": "high", "confidence": 0.8, "tool_call_ids": tool_call_ids} | kw


async def test_tool_then_cited_findings():
    def submit(req):
        tool_msg = req.messages[-1]
        assert "orders_by_user 4200 ms" in tool_msg.content and "<tool_output" in tool_msg.content
        return call("submit_findings", summary="slow query found", findings=[_finding([_call_id(tool_msg)])])

    loop, llm, events, conn = await _loop({"specialist:database": [call("supabase__slow_queries"), submit]})
    result = await loop.run(TASK, INCIDENT, "plan")
    assert result.error is None and len(result.evidence) == 1
    ev = result.evidence[0]
    assert ev.agent == AgentId.database and ev.connector_type == "supabase"
    assert ev.capability == Capability.database and ev.id.startswith("ev_")
    assert ev.tool_call_ids == [result.tool_calls[0].id]
    assert conn.calls == [("supabase.slow_queries", {})]
    assert [e.type for e in events] == ["agent_started", "tool_called", "tool_completed",
                                        "evidence_added", "agent_completed"]
    # model-facing tool names cannot contain dots
    assert {t.name for t in llm.requests[0].tools} == {"supabase__slow_queries", "submit_findings"}
    assert llm.requests[0].model_role == "specialist"
    assert "Find slow queries" in llm.requests[0].messages[0].content


async def test_uncited_findings_are_repaired():
    def good(req):
        tool_output = next(m for m in req.messages if m.role == "tool" and "<tool_output" in m.content)
        return call("submit_findings", summary="s", findings=[_finding([_call_id(tool_output)])])

    loop, llm, _, _ = await _loop({"specialist:database": [
        call("supabase__slow_queries"),
        call("submit_findings", summary="s", findings=[_finding(["tc_made_up"])]),
        good]})
    result = await loop.run(TASK, INCIDENT, "plan")
    assert len(result.evidence) == 1
    assert "tc_made_up" in llm.requests[2].messages[-1].content


async def test_budget_forces_submission():
    loop, llm, _, _ = await _loop({"specialist:database": [
        call("supabase__slow_queries"), call("supabase__slow_queries"),
        call("submit_findings", summary="budget used", findings=[])]}, max_calls=2)
    result = await loop.run(TASK, INCIDENT, "plan")
    assert llm.requests[2].tool_choice == "submit_findings"
    assert result.summary == "budget used" and len(result.tool_calls) == 2


async def test_text_reply_gets_nudged():
    loop, llm, _, _ = await _loop({"specialist:database": [
        LLMReply(text="Let me think"), call("submit_findings", summary="none", findings=[])]})
    await loop.run(TASK, INCIDENT, "plan")
    assert "Use one of your tools or call submit_findings" in llm.requests[1].messages[-1].content


async def test_llm_crash_is_agent_failed():
    def boom(req):
        raise RuntimeError("provider down")
    loop, _, events, _ = await _loop({"specialist:database": [boom]})
    result = await loop.run(TASK, INCIDENT, "plan")
    assert result.error and "provider down" in result.error
    assert events[-1].type == "agent_failed"


async def test_ask_agent_routes_through_broker_and_answer_is_citable():
    from forgeops.engine.models import Evidence, ToolCallRecord

    record = ToolCallRecord(id="tc_colleague", agent=AgentId.code, tool="github.list_commits",
                            connector_type="github", connection_id="con_gh", args_summary="{}",
                            ok=True, duration_ms=5, truncated=False, result_excerpt="a1b2", error=None)
    colleague_ev = Evidence(id="ev_colleague", agent=AgentId.code, capability=Capability.code,
                            connection_id="con_gh", connector_type="github", finding="a1b2 changed pool",
                            severity="high", confidence=0.9, tool_call_ids=["tc_colleague"])

    async def answer(from_agent, to_agent, question):
        return SpecialistResult(evidence=[colleague_ev], tool_calls=[record], questions=[],
                                summary="Commit a1b2 lowered the pool at 13:58 UTC")

    events, emit = collect_events()
    broker = QuestionBroker(answer=answer, available={AgentId.code, AgentId.database}, emit=emit,
                            budgets=Budgets())

    def submit(req):
        assert "Commit a1b2 lowered the pool" in req.messages[-1].content
        return call("submit_findings", summary="pool change", findings=[
            _finding(["tc_colleague"], finding="Pool lowered by a1b2")])

    loop, llm, _, _ = await _loop({"specialist:database": [
        call("ask_agent", agent="code", question="What changed in the DB config at 13:55?"), submit]},
        broker=broker, colleagues=[AgentId.code])
    result = await loop.run(TASK, INCIDENT, "plan")
    assert result.error is None
    assert [q.status for q in result.questions] == ["answered"]
    assert {e.id for e in result.evidence} >= {"ev_colleague"}
    assert "ask_agent" in {t.name for t in llm.requests[0].tools}
    assert llm.requests[0].tools[-2].parameters["properties"]["agent"]["enum"] == ["code"]
