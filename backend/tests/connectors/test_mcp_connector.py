import asyncio
import sys
from pathlib import Path

from forgeops.connectors.definitions import ConfigField, ConnectorDefinition, ToolMapping
from forgeops.connectors.mcp import McpConnector
from forgeops.engine.models import AgentId, Capability

SERVER = Path(__file__).parents[1] / "fixtures" / "mcp_test_server.py"

DEFINITION = ConnectorDefinition(
    type="testgit", display_name="Test Git", description="test", agents=[AgentId.code],
    status="available", transport="stdio", command=[sys.executable, str(SERVER)],
    env={"TEST_TOKEN": "{token}"}, config_fields=[ConfigField(key="token", label="Token", secret=True)],
    tools=[ToolMapping(upstream="recent_commits", name="testgit.recent_commits",
                       capability=Capability.code, permission="read"),
           ToolMapping(upstream="failing_tool", name="testgit.failing_tool",
                       capability=Capability.code, permission="read"),
           ToolMapping(upstream="token_seen", name="testgit.token_seen",
                       capability=Capability.code, permission="read")])


def _connector():
    return McpConnector(DEFINITION, "con_t", config={}, secrets={"token": "t0k"})


async def test_exposes_only_allowlisted_tools_with_forgeops_names():
    conn = _connector()
    try:
        tools = await conn.list_tools()
        assert sorted(t.name for t in tools) == [
            "testgit.failing_tool", "testgit.recent_commits", "testgit.token_seen"]
        commits = next(t for t in tools if t.name == "testgit.recent_commits")
        assert commits.capability == Capability.code and commits.permission == "read"
        assert "limit" in commits.input_schema["properties"]
        assert commits.connection_id == "con_t" and commits.connector_type == "testgit"
    finally:
        await conn.aclose()


async def test_call_returns_text_and_errors():
    conn = _connector()
    try:
        ok = await conn.call("testgit.recent_commits", {"limit": 1})
        assert ok.ok and ok.content == "a1b2c3 lower DB pool to 5"
        bad = await conn.call("testgit.failing_tool", {})
        assert not bad.ok and "upstream exploded" in bad.error
        unknown = await conn.call("testgit.delete_repository", {"name": "x"})
        assert not unknown.ok and "not an allowed tool" in unknown.error
    finally:
        await conn.aclose()


async def test_secrets_reach_the_server_through_env():
    conn = _connector()
    try:
        assert (await conn.call("testgit.token_seen", {})).content == "token present"
    finally:
        await conn.aclose()


async def test_health_check_reports_tool_count():
    conn = _connector()
    try:
        health = await conn.health_check()
        assert health.ok and "3 tools" in health.detail
    finally:
        await conn.aclose()


async def test_can_be_opened_and_closed_from_different_tasks():
    conn = _connector()
    await asyncio.create_task(conn.list_tools())  # opened inside another task
    result = await asyncio.create_task(conn.call("testgit.recent_commits", {"limit": 1}))
    assert result.ok
    await conn.aclose()  # closed from this task


async def test_missing_command_is_a_clear_health_failure():
    broken = DEFINITION.model_copy(update={"command": [sys.executable, "does_not_exist.py"]})
    conn = McpConnector(broken, "con_t", config={}, secrets={"token": "t0k"})
    try:
        health = await conn.health_check()
        assert not health.ok and health.detail
    finally:
        await conn.aclose()
