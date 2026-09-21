from forgeops.capabilities.models import ToolResult, ToolSpec
from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.engine.models import AgentId, Capability
from tests.engine.fakes import FakeConnector


def spec(name, cap, perm="read", conn="con_sb", ctype="supabase"):
    return ToolSpec(name=name, description=name, capability=cap, permission=perm,
                    input_schema={"type": "object"}, connection_id=conn, connector_type=ctype)


class Broken(FakeConnector):
    async def list_tools(self):
        raise RuntimeError("token rejected")


async def test_one_connector_serves_several_agents_read_only():
    sb = FakeConnector("con_sb", "supabase", [
        spec("supabase.slow_queries", Capability.database),
        spec("supabase.get_logs", Capability.logs),
        spec("supabase.list_functions", Capability.backend)], {})
    gh = FakeConnector("con_gh", "github", [
        spec("github.list_commits", Capability.code, conn="con_gh", ctype="github"),
        spec("github.create_issue", Capability.write, "write", conn="con_gh", ctype="github")], {})
    reg = await CapabilityRegistry.build([sb, gh])

    assert [t.name for t in reg.tools_for(AgentId.database)] == ["supabase.slow_queries"]
    assert [t.name for t in reg.tools_for(AgentId.observability)] == ["supabase.get_logs"]
    assert [t.name for t in reg.tools_for(AgentId.backend_services)] == ["supabase.list_functions"]
    assert [t.name for t in reg.tools_for(AgentId.code)] == ["github.list_commits"]
    assert [t.name for t in reg.tools_for(AgentId.action)] == ["github.create_issue"]
    for agent in (AgentId.code, AgentId.database, AgentId.observability):
        assert all(t.permission == "read" for t in reg.tools_for(agent))
    assert reg.tools_for(AgentId.frontend_hosting) == []
    assert reg.connected_agents() == {
        AgentId.code: [Capability.code], AgentId.backend_services: [Capability.backend],
        AgentId.database: [Capability.database], AgentId.observability: [Capability.logs]}


async def test_broken_connector_becomes_a_warning():
    ok = FakeConnector("con_kv", "knowledge", [
        spec("knowledge.search", Capability.knowledge, conn="con_kv", ctype="knowledge")], {})
    reg = await CapabilityRegistry.build([ok, Broken("con_x", "sentry", [], {})])
    assert list(reg.connected_agents()) == [AgentId.knowledge]
    assert reg.warnings == ["sentry (con_x) unavailable: token rejected"]


async def test_call_dispatches_to_owning_connector():
    sb = FakeConnector("con_sb", "supabase", [spec("supabase.get_logs", Capability.logs)],
                       {"supabase.get_logs": ToolResult(ok=True, content="3 errors")})
    reg = await CapabilityRegistry.build([sb])
    assert (await reg.call("supabase.get_logs", {})).content == "3 errors"


async def test_aclose_closes_every_connector():
    a = FakeConnector("con_a", "x", [], {})
    b = Broken("con_b", "y", [], {})
    reg = await CapabilityRegistry.build([a, b])
    await reg.aclose()
    assert a.closed and b.closed
