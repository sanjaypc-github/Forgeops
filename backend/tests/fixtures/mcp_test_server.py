"""Minimal MCP server for connector tests (test-only data). stdio by default; `--http PORT` for HTTP."""

import json
import os
import sys

from mcp.server.mcpserver import Context, MCPServer
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
def echo_args(owner: str = "", repo: str = "", method: str = "", title: str = "") -> str:
    """Echo the arguments received (to test defaults and fixed arguments)."""
    return json.dumps({"owner": owner, "repo": repo, "method": method, "title": title}, sort_keys=True)


@server.tool()
def request_headers(ctx: Context) -> str:
    """Report the auth and read-only headers seen over HTTP (never the token itself)."""
    request = getattr(ctx.request_context, "request", None)
    headers = getattr(request, "headers", {}) or {}
    return json.dumps({
        "auth": headers.get("authorization") == "Bearer t0k",
        "readonly": headers.get("x-mcp-readonly"),
    }, sort_keys=True)


@server.tool()
def delete_repository(name: str) -> str:
    """Destructive tool that ForgeOps must never expose."""
    return f"deleted {name}"


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--http":
        server.run("streamable-http", port=int(sys.argv[2]))
    else:
        server.run("stdio")
