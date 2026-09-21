"""A connector backed by an MCP server, exposing only the tools its definition allowlists."""

import asyncio
import os
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from forgeops.capabilities.models import HealthStatus, ToolResult, ToolSpec, ToolTransientError
from forgeops.connectors.definitions import ConnectorDefinition

# Only what child processes need to start on Windows/Unix; never the full parent environment.
_PASSTHROUGH_ENV = ("PATH", "SYSTEMROOT", "PATHEXT", "TEMP", "TMP", "USERPROFILE", "APPDATA",
                    "LOCALAPPDATA", "HOME", "LANG")
CALL_TIMEOUT_SECONDS = 30
START_TIMEOUT_SECONDS = 30


def _fill(template: str, values: dict[str, Any]) -> str:
    return template.format_map(values)


class McpConnector:
    def __init__(self, definition: ConnectorDefinition, connection_id: str,
                 config: dict[str, Any], secrets: dict[str, Any]) -> None:
        self.definition = definition
        self.connection_id = connection_id
        self.connector_type = definition.type
        self._values = {**config, **secrets}
        self._by_name = {m.name: m for m in definition.tools}
        self._by_upstream = {m.upstream: m for m in definition.tools}
        self._session: ClientSession | None = None
        self._owner: asyncio.Task | None = None
        self._ready: asyncio.Future | None = None
        self._closing = asyncio.Event()
        self._lock = asyncio.Lock()

    # The MCP client's context managers must be entered and exited in the same task,
    # so a dedicated owner task holds the session for the connector's lifetime.
    async def _own_session(self) -> None:
        try:
            async with AsyncExitStack() as stack:
                read, write = await stack.enter_async_context(stdio_client(self._server_params()))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                self._session = session
                self._ready.set_result(session)
                await self._closing.wait()
        except BaseException as exc:  # noqa: BLE001 - reported to whoever awaits readiness
            if not self._ready.done():
                self._ready.set_exception(exc if isinstance(exc, Exception) else RuntimeError(str(exc)))
            if not isinstance(exc, Exception):
                raise
        finally:
            self._session = None

    def _server_params(self) -> StdioServerParameters:
        if self.definition.transport == "http":
            raise NotImplementedError("HTTP MCP transport arrives with the first remote connector (M3)")
        if self.definition.transport != "stdio" or not self.definition.command:
            raise ValueError(f"{self.definition.type} is not an MCP stdio connector")
        command = [_fill(part, self._values) for part in self.definition.command]
        env = {k: os.environ[k] for k in _PASSTHROUGH_ENV if k in os.environ}
        env.update({k: _fill(v, self._values) for k, v in self.definition.env.items()})
        return StdioServerParameters(command=command[0], args=command[1:], env=env)

    async def _get_session(self) -> ClientSession:
        async with self._lock:
            if self._owner is None:
                self._ready = asyncio.get_running_loop().create_future()
                self._owner = asyncio.create_task(self._own_session(), name=f"mcp:{self.connection_id}")
        try:
            async with asyncio.timeout(START_TIMEOUT_SECONDS):
                return await asyncio.shield(self._ready)
        except TimeoutError as exc:
            raise ToolTransientError(f"{self.connector_type} MCP server did not start in time") from exc

    async def list_tools(self) -> list[ToolSpec]:
        session = await self._get_session()
        specs: list[ToolSpec] = []
        cursor = None
        while True:
            page = await session.list_tools(params={"cursor": cursor} if cursor else None)
            for tool in page.tools:
                mapping = self._by_upstream.get(tool.name)
                if mapping is None:
                    continue  # not allowlisted: never exposed to agents
                specs.append(ToolSpec(
                    name=mapping.name,
                    description=tool.description or mapping.name,
                    capability=mapping.capability,
                    permission=mapping.permission,
                    input_schema=tool.input_schema or {"type": "object", "properties": {}},
                    connection_id=self.connection_id,
                    connector_type=self.connector_type,
                ))
            cursor = getattr(page, "next_cursor", None)
            if not cursor:
                return specs

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        mapping = self._by_name.get(tool_name)
        if mapping is None:
            return ToolResult(ok=False, error=f"{tool_name} is not an allowed tool for {self.connector_type}")
        session = await self._get_session()
        try:
            result = await session.call_tool(mapping.upstream, arguments,
                                             read_timeout_seconds=CALL_TIMEOUT_SECONDS)
        except TimeoutError as exc:
            raise ToolTransientError(f"{tool_name} timed out") from exc
        text = "\n".join(getattr(block, "text", "") for block in (result.content or [])
                         if getattr(block, "text", None)).strip()
        if getattr(result, "is_error", False):
            return ToolResult(ok=False, error=text or f"{tool_name} failed")
        return ToolResult(ok=True, content=text, data=getattr(result, "structured_content", None))

    async def health_check(self) -> HealthStatus:
        try:
            tools = await self.list_tools()
        except Exception as exc:  # noqa: BLE001
            return HealthStatus(ok=False, detail=f"Could not start or reach the MCP server: {exc}")
        return HealthStatus(ok=True, detail=f"{len(tools)} tools available")

    async def aclose(self) -> None:
        self._closing.set()
        if self._owner is not None:
            try:
                await asyncio.wait_for(self._owner, timeout=10)
            except (TimeoutError, Exception):  # noqa: BLE001
                self._owner.cancel()
            self._owner = None
