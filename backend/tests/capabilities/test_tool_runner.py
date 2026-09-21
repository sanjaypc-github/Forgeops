from dataclasses import replace

from forgeops.capabilities.models import ToolResult, ToolSpec, ToolTransientError
from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.capabilities.runner import ToolRunner
from forgeops.engine.budgets import Budgets
from forgeops.engine.models import AgentId, Capability
from tests.engine.fakes import FakeConnector, collect_events

LOGS = ToolSpec(name="supabase.get_logs", description="d", capability=Capability.logs,
                permission="read", input_schema={"type": "object"}, connection_id="con_sb",
                connector_type="supabase")


async def _runner(response, budgets=Budgets(), delay=0.0):
    conn = FakeConnector("con_sb", "supabase", [LOGS], {"supabase.get_logs": response}, delay=delay)
    reg = await CapabilityRegistry.build([conn])
    events, emit = collect_events()
    return ToolRunner(reg, emit, budgets), events, conn


async def test_success_emits_events_and_records_provenance():
    runner, events, _ = await _runner(ToolResult(ok=True, content="line1\nline2"))
    result, record = await runner.run(agent=AgentId.observability, tool_name="supabase.get_logs",
                                      arguments={"service": "api"}, allowed={"supabase.get_logs"})
    assert result.ok and record.ok and record.id.startswith("tc_")
    assert record.connector_type == "supabase" and record.connection_id == "con_sb"
    assert [e.type for e in events] == ["tool_called", "tool_completed"]
    assert events[0].agent == "observability"
    assert events[0].data["tool"] == "supabase.get_logs"
    assert events[1].data["ok"] is True and events[1].data["call_id"] == record.id


async def test_disallowed_tool_is_refused_without_calling():
    runner, events, conn = await _runner(ToolResult(ok=True, content="x"))
    result, record = await runner.run(agent=AgentId.code, tool_name="supabase.get_logs",
                                      arguments={}, allowed=set())
    assert not result.ok and "not available to this agent" in result.error
    assert conn.calls == [] and not record.ok


async def test_transient_errors_are_retried_then_reported():
    runner, events, conn = await _runner(ToolTransientError("429 rate limited"))
    result, record = await runner.run(agent=AgentId.observability, tool_name="supabase.get_logs",
                                      arguments={}, allowed={"supabase.get_logs"})
    assert len(conn.calls) == 3 and not result.ok and "429" in result.error


async def test_timeout_is_a_failed_result():
    runner, _, _ = await _runner(ToolResult(ok=True, content="late"),
                                 budgets=replace(Budgets(), tool_timeout_seconds=0.05), delay=0.5)
    result, _ = await runner.run(agent=AgentId.observability, tool_name="supabase.get_logs",
                                 arguments={}, allowed={"supabase.get_logs"})
    assert not result.ok and "timed out" in result.error


async def test_large_output_is_truncated_and_marked():
    runner, events, _ = await _runner(ToolResult(ok=True, content="x" * 20000),
                                      budgets=replace(Budgets(), tool_output_chars=1000))
    result, record = await runner.run(agent=AgentId.observability, tool_name="supabase.get_logs",
                                      arguments={}, allowed={"supabase.get_logs"})
    assert result.truncated and record.truncated and len(result.content) < 1200
    assert "truncated" in result.content
