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
        assert health.ok and "3 read tools available" in health.detail
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


# ─── M3: defaults, fixed arguments, writes, health, HTTP ─────────────────────────────────────────
import json
import socket
import subprocess
import time

import pytest


def _echo_definition(**extra):
    return ConnectorDefinition(**({
        "type": "testgit", "display_name": "Test Git", "description": "test", "agents": [AgentId.code],
        "status": "available", "transport": "stdio", "command": [sys.executable, str(SERVER)],
        "env": {"TEST_TOKEN": "{token}"},
        "config_fields": [ConfigField(key="repository", label="Repository"),
                          ConfigField(key="token", label="Token", secret=True)],
        "tools": [
            ToolMapping(upstream="echo_args", name="testgit.echo", capability=Capability.code, permission="read",
                        defaults={"owner": "{owner}", "repo": "{repo}"}),
            ToolMapping(upstream="echo_args", name="testgit.create_issue", capability=Capability.write,
                        permission="write", defaults={"owner": "{owner}", "repo": "{repo}"},
                        fixed={"method": "create"}),
            ToolMapping(upstream="does_not_exist", name="testgit.missing", capability=Capability.code,
                        permission="read"),
        ],
    } | extra))


async def test_connection_defaults_are_filled_and_fixed_arguments_win():
    conn = McpConnector(_echo_definition(), "con_t", config={"repository": "acme/shop", "allow_writes": True},
                        secrets={"token": "t0k"})
    try:
        read = json.loads((await conn.call("testgit.echo", {"title": "x"})).content)
        assert read == {"owner": "acme", "repo": "shop", "method": "", "title": "x"}
        override = json.loads((await conn.call("testgit.echo", {"owner": "other"})).content)
        assert override["owner"] == "other"  # defaults can be overridden by the agent
        write = json.loads((await conn.call("testgit.create_issue", {"title": "Bug", "method": "delete"})).content)
        assert write == {"owner": "acme", "repo": "shop", "method": "create", "title": "Bug"}  # fixed wins
    finally:
        await conn.aclose()


async def test_write_tools_only_exist_when_the_connection_allows_writes():
    read_only = McpConnector(_echo_definition(), "con_t", config={"repository": "acme/shop"}, secrets={"token": "t0k"})
    writable = McpConnector(_echo_definition(), "con_t", config={"repository": "acme/shop", "allow_writes": True},
                            secrets={"token": "t0k"})
    try:
        assert "testgit.create_issue" not in {t.name for t in await read_only.list_tools()}
        refused = await read_only.call("testgit.create_issue", {"title": "x"})
        assert not refused.ok and "writes are not enabled" in refused.error
        tools = {t.name: t for t in await writable.list_tools()}
        assert tools["testgit.create_issue"].permission == "write"
        assert tools["testgit.create_issue"].capability == Capability.write
    finally:
        await read_only.aclose()
        await writable.aclose()


async def test_health_check_reports_allowlisted_tools_the_server_lacks():
    conn = McpConnector(_echo_definition(), "con_t", config={"repository": "acme/shop"}, secrets={"token": "t0k"})
    try:
        health = await conn.health_check()
        assert health.ok and "testgit.missing" in health.detail
    finally:
        await conn.aclose()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def http_server():
    port = _free_port()
    proc = subprocess.Popen([sys.executable, str(SERVER), "--http", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while time.time() < deadline:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                break
        time.sleep(0.2)
    yield f"http://127.0.0.1:{port}/mcp"
    proc.terminate()
    proc.wait(timeout=10)


async def test_http_transport_sends_auth_and_read_only_headers(http_server):
    definition = ConnectorDefinition(
        type="testhttp", display_name="Test HTTP", description="test", agents=[AgentId.code],
        status="available", transport="http", url=http_server,
        headers={"Authorization": "Bearer {token}", "X-MCP-Readonly": "true"},
        write_headers={"Authorization": "Bearer {token}"},
        config_fields=[ConfigField(key="token", label="Token", secret=True)],
        tools=[ToolMapping(upstream="request_headers", name="testhttp.headers", capability=Capability.code,
                           permission="read"),
               ToolMapping(upstream="request_headers", name="testhttp.headers_write",
                           capability=Capability.write, permission="write")],
    )
    conn = McpConnector(definition, "con_h", config={"allow_writes": True}, secrets={"token": "t0k"})
    try:
        assert [t.name for t in await conn.list_tools() if t.permission == "read"] == ["testhttp.headers"]
        read = json.loads((await conn.call("testhttp.headers", {})).content)
        assert read == {"auth": True, "readonly": "true"}
        write = json.loads((await conn.call("testhttp.headers_write", {})).content)
        assert write == {"auth": True, "readonly": None}  # the write session is a separate, non-read-only session
    finally:
        await conn.aclose()
