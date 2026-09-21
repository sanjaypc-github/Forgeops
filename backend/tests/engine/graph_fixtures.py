"""Shared scripted scenario for graph tests (test-only)."""

from datetime import UTC, datetime

from forgeops.capabilities.models import ToolResult, ToolSpec
from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.capabilities.runner import ToolRunner
from forgeops.engine.budgets import Budgets
from forgeops.engine.graph import RunDeps
from forgeops.engine.models import Capability, Incident
from tests.engine.fakes import FakeConnector, ScriptedLLM, call, collect_events


def spec(name, cap, perm="read", ctype="github"):
    return ToolSpec(name=name, description=name, capability=cap, permission=perm,
                    input_schema={"type": "object", "properties": {}}, connection_id=f"con_{ctype}",
                    connector_type=ctype)


def last_call_id(req) -> str:
    return req.messages[-1].content.split('call_id="')[1].split('"')[0]


def submit_after_tool(finding):
    return lambda req: call("submit_findings", summary=finding, findings=[{
        "finding": finding, "artifacts": [], "severity": "high", "confidence": 0.8,
        "tool_call_ids": [last_call_id(req)]}])


def evidence_ids(req) -> list[str]:
    return [token for token in req.messages[0].content.split() if token.startswith("ev_")]


def script():
    return {
        "plan": [call("submit_plan", summary="deploy suspect", affected_service=None, window_start=None,
                      window_end=None, hypotheses=["config change"], not_relevant=[],
                      tasks=[{"agent": "code", "objective": "diff"},
                             {"agent": "knowledge", "objective": "runbooks"}])],
        "specialist:code": [call("github__list_commits"), submit_after_tool("pool lowered in a1b2")],
        "specialist:knowledge": [call("knowledge__search", query="pool"),
                                 submit_after_tool("runbook says pool >= 20")],
        "review": [call("submit_review", sufficient=True, reason="clear", follow_up_tasks=[])],
        "rca": [lambda req: call("submit_rca", summary="Pool lowered", failure_point="a1b2",
                                 category="config_change", confidence=0.9, timeline=[],
                                 supporting_evidence=evidence_ids(req)[:2],
                                 contradicting_evidence=[], alternative_hypotheses=[],
                                 missing_information=[], recommendations=[{
                                     "title": "Open issue", "description": "restore pool",
                                     "action": "github_issue",
                                     "parameters": {"title": "Restore pool", "body": "..."}}])],
    }


def fake_connectors(with_write=True):
    gh_tools = [spec("github.list_commits", Capability.code)]
    if with_write:
        gh_tools.append(spec("github.create_issue", Capability.write, "write"))
    gh = FakeConnector("con_github", "github", gh_tools, {
        "github.list_commits": ToolResult(ok=True, content="a1b2 lower pool"),
        "github.create_issue": ToolResult(ok=True, content="Created https://github.com/o/r/issues/7")})
    kv = FakeConnector("con_knowledge", "knowledge",
                       [spec("knowledge.search", Capability.knowledge, ctype="knowledge")],
                       {"knowledge.search": ToolResult(ok=True, content="runbook: pool >= 20")})
    return gh, kv


async def make_deps(script_map, with_write=True):
    gh, kv = fake_connectors(with_write)
    registry = await CapabilityRegistry.build([gh, kv])
    events, emit = collect_events()
    llm = ScriptedLLM(script_map)

    async def notes():
        return []

    deps = RunDeps(llm=llm, registry=registry, tool_runner=ToolRunner(registry, emit, Budgets()),
                   emit=emit, budgets=Budgets(), now=lambda: datetime(2026, 9, 21, tzinfo=UTC),
                   service_map="", notes=notes)
    return deps, events, llm, gh


def initial_state(investigation_id="inv_1"):
    return {"workspace_id": "ws_1", "investigation_id": investigation_id,
            "incident": Incident(text="checkout slow after deploy", source="chat"),
            "capabilities": {}, "plan": None, "pending_tasks": [], "review_rounds": 0,
            "followup_rounds": 0, "rca": None, "decision": None, "report_markdown": None}
