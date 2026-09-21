from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from forgeops.engine.graph import build_graph
from tests.engine.fakes import call
from tests.engine.graph_fixtures import initial_state, make_deps, script

CFG = {"configurable": {"thread_id": "inv_1"}}


def _approve(rec_id):
    return Command(resume={"kind": "approve", "approved_recommendation_ids": [rec_id],
                           "decided_by": "usr_1", "channel": "web"})


async def test_full_run_pauses_for_approval_then_creates_issue():
    deps, events, _, gh = await make_deps(script())
    graph = build_graph(deps, InMemorySaver())
    await graph.ainvoke(initial_state(), CFG)
    state = await graph.aget_state(CFG)
    assert state.next == ("approval",)
    values = state.values
    assert len(values["evidence"]) == 2 and values["rca"].confidence == 0.9
    types = [e.type for e in events]
    assert types.index("plan_created") < types.index("rca_completed") < types.index("approval_requested")
    assert types.count("agent_started") == 2 and types.count("agent_skipped") == 4
    assert ("github.create_issue", {"title": "Restore pool", "body": "..."}) not in gh.calls

    rec_id = values["rca"].recommendations[0].id
    await graph.ainvoke(_approve(rec_id), CFG)
    final = (await graph.aget_state(CFG)).values
    assert final["action_results"][0].status == "done"
    assert final["action_results"][0].url == "https://github.com/o/r/issues/7"
    assert ("github.create_issue", {"title": "Restore pool", "body": "..."}) in gh.calls
    assert "Pool lowered" in final["report_markdown"]
    after = [e.type for e in events]
    assert after.count("approval_requested") == 1
    assert "approval_granted" in after and "action_completed" in after
    assert after[-2:] == ["report_ready", "investigation_completed"]
    assert events[-1].data["status"] == "completed"


async def test_reject_skips_action():
    deps, events, _, gh = await make_deps(script())
    graph = build_graph(deps, InMemorySaver())
    await graph.ainvoke(initial_state(), CFG)
    await graph.ainvoke(Command(resume={"kind": "reject", "decided_by": "usr_1", "channel": "web"}), CFG)
    final = (await graph.aget_state(CFG)).values
    assert final["action_results"] == []
    assert all(name != "github.create_issue" for name, _ in gh.calls)
    assert "approval_rejected" in [e.type for e in events]
    assert events[-1].data["status"] == "rejected"


async def test_missing_write_connector_is_unavailable_not_faked():
    deps, _, _, _ = await make_deps(script(), with_write=False)
    graph = build_graph(deps, InMemorySaver())
    await graph.ainvoke(initial_state(), CFG)
    rec_id = (await graph.aget_state(CFG)).values["rca"].recommendations[0].id
    await graph.ainvoke(_approve(rec_id), CFG)
    result = (await graph.aget_state(CFG)).values["action_results"][0]
    assert result.status == "unavailable"


async def test_investigate_more_replans_with_the_note():
    s = script()
    s["plan"].append(call("submit_plan", summary="check again", hypotheses=[], not_relevant=[],
                          tasks=[{"agent": "code", "objective": "look at redis change"}]))
    s["specialist:code"] += [call("github__list_commits"),
                             lambda req: call("submit_findings", summary="nothing new", findings=[])]
    s["review"].append(call("submit_review", sufficient=True, reason="ok", follow_up_tasks=[]))
    s["rca"].append(s["rca"][0])
    deps, events, llm, _ = await make_deps(s)
    graph = build_graph(deps, InMemorySaver())
    await graph.ainvoke(initial_state(), CFG)
    await graph.ainvoke(Command(resume={"kind": "investigate_more", "note": "we also changed redis",
                                        "decided_by": "usr_1", "channel": "web"}), CFG)
    state = await graph.aget_state(CFG)
    assert state.next == ("approval",)
    replan = [r for r in llm.requests if r.purpose == "plan"][1]
    assert "we also changed redis" in replan.messages[0].content
    assert state.values["followup_rounds"] == 1


async def test_review_follow_up_round_runs_specialists_again():
    s = script()
    s["review"] = [call("submit_review", sufficient=False, reason="need PR",
                        follow_up_tasks=[{"agent": "code", "objective": "which PR merged a1b2"}])]
    s["specialist:code"] += [call("github__list_commits"),
                             lambda req: call("submit_findings", summary="PR #12", findings=[])]
    deps, events, llm, _ = await make_deps(s)
    graph = build_graph(deps, InMemorySaver())
    await graph.ainvoke(initial_state(), CFG)
    assert [r.purpose for r in llm.requests].count("review") == 1  # second review skipped: limit
    assert [e.type for e in events].count("agent_started") == 3
    assert (await graph.aget_state(CFG)).next == ("approval",)


async def test_no_connectors_goes_straight_to_report():
    from forgeops.capabilities.registry import CapabilityRegistry
    from forgeops.capabilities.runner import ToolRunner

    deps, events, llm, _ = await make_deps({})
    empty = await CapabilityRegistry.build([])
    deps = deps.__class__(**{**deps.__dict__, "registry": empty,
                             "tool_runner": ToolRunner(empty, deps.emit, deps.budgets)})
    graph = build_graph(deps, InMemorySaver())
    await graph.ainvoke(initial_state(), CFG)
    final = await graph.aget_state(CFG)
    assert final.next == () and llm.requests == []
    assert "No root cause was determined" in final.values["report_markdown"]
    assert events[-1].type == "investigation_completed"
