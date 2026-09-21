"""Minimal stdio MCP server for connector tests (test-only data)."""

import os

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

server = MCPServer("forgeops-test")


@server.tool()
def recent_commits(limit: int = 2) -> str:
    """List recent commits."""
    commits = ["a1b2c3 lower DB pool to 5", "d4e5f6 add banner"]
    return "\n".join(commits[:limit])


@server.tool()
def failing_tool() -> str:
    """Always fails."""
    raise ToolError("upstream exploded")


@server.tool()
def token_seen() -> str:
    """Reports whether the token env var reached the server (never its value)."""
    return "token present" if os.environ.get("TEST_TOKEN") == "t0k" else "token missing"


@server.tool()
def delete_repository(name: str) -> str:
    """Destructive tool that ForgeOps must never expose."""
    return f"deleted {name}"


if __name__ == "__main__":
    server.run("stdio")
