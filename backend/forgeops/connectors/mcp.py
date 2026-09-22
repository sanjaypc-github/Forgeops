"""A connector backed by an MCP server, exposing only the tools its definition allowlists.

Investigations use a read session (read-only headers or flags). Write tools exist only when the
connection opts in to writes; they run on a separate session that is opened only when an approved
action calls one.
"""

import asyncio
import os
import shutil
from contextlib import AsyncExitStack
from typing import Any, Literal

import httpx2
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from forgeops.capabilities.models import HealthStatus, ToolResult, ToolSpec, ToolTransientError
from forgeops.connectors.definitions import ConnectorDefinition, ToolMapping

# Only what child processes need to start on Windows/Unix; never the full parent environment.
_PASSTHROUGH_ENV = ("PATH", "SYSTEMROOT", "PATHEXT", "TEMP", "TMP", "USERPROFILE", "APPDATA",
                    "LOCALAPPDATA", "HOME", "LANG", "ProgramFiles", "ProgramData", "NODE_OPTIONS")
CALL_TIMEOUT_SECONDS = 30
START_TIMEOUT_SECONDS = 90  # npx may download the server on first use

Mode = Literal["read", "write"]


class _TemplateValues(dict):
    """format_map that reports a missing connection value clearly."""

    def __missing__(self, key: str) -> str:
        raise KeyError(f"connection value '{key}' is required by this connector")


def connection_values(config: dict[str, Any], secrets: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {**config, **secrets}
    repository = str(values.get("repository", "")).strip().strip("/")
    if repository.count("/") == 1:
        values.setdefault("owner", repository.split("/")[0])
        values.setdefault("repo", repository.split("/")[1])
    return values


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class _Session:
    """One MCP client session owned by a dedicated task (the SDK's context managers must enter and
    exit in the same task, while ForgeOps opens and closes connectors from different tasks)."""

    def __init__(self, open_transport, name: str) -> None:
        self._open_transport = open_transport
        self._name = name
        self._task: asyncio.Task | None = None
        self._ready: asyncio.Future | None = None
        self._closing = asyncio.Event()
        self._lock = asyncio.Lock()

    async def _own(self) -> None:
        try:
            async with AsyncExitStack() as stack:
                read, write = await self._open_transport(stack)
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                self._ready.set_result(session)
                await self._closing.wait()
        except BaseException as exc:  # noqa: BLE001 - surfaced to whoever awaits readiness
            if not self._ready.done():
                self._ready.set_exception(exc if isinstance(exc, Exception) else RuntimeError(str(exc)))
            if not isinstance(exc, Exception):
                raise

    async def get(self) -> ClientSession:
        async with self._lock:
            if self._task is None:
                self._ready = asyncio.get_running_loop().create_future()
                self._task = asyncio.create_task(self._own(), name=self._name)
        try:
            async with asyncio.timeout(START_TIMEOUT_SECONDS):
                return await asyncio.shield(self._ready)
        except TimeoutError as exc:
            raise ToolTransientError("the MCP server did not start in time") from exc

    async def close(self) -> None:
        self._closing.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=10)
            except (TimeoutError, Exception):  # noqa: BLE001
                self._task.cancel()
            self._task = None


class McpConnector:
    def __init__(self, definition: ConnectorDefinition, connection_id: str,
                 config: dict[str, Any], secrets: dict[str, Any]) -> None:
        self.definition = definition
        self.connection_id = connection_id
        self.connector_type = definition.type
        self._values = _TemplateValues(connection_values(config, secrets))
        self._writes = _truthy(config.get("allow_writes", False))
        self._by_name = {m.name: m for m in definition.tools}
        self._sessions: dict[Mode, _Session] = {}

    # ----- transports --------------------------------------------------------------------------
    def _fill(self, template: str) -> str:
        return template.format_map(self._values)

    def _stdio_params(self) -> StdioServerParameters:
        if not self.definition.command:
            raise ValueError(f"{self.definition.type} has no command")
        command = [self._fill(part) for part in self.definition.command]
        env = {k: os.environ[k] for k in _PASSTHROUGH_ENV if k in os.environ}
        env.update({k: self._fill(v) for k, v in self.definition.env.items()})
        # On Windows "npx" is npx.cmd, which subprocesses only find by its full name.
        executable = shutil.which(command[0]) or command[0]
        return StdioServerParameters(command=executable, args=command[1:], env=env)

    def _transport(self, mode: Mode):
        definition = self.definition

        async def open_stdio(stack: AsyncExitStack):
            return await stack.enter_async_context(stdio_client(self._stdio_params()))

        async def open_http(stack: AsyncExitStack):
            headers = definition.write_headers if mode == "write" else definition.headers
            client = await stack.enter_async_context(httpx2.AsyncClient(
                headers={k: self._fill(v) for k, v in headers.items()},
                timeout=httpx2.Timeout(CALL_TIMEOUT_SECONDS, read=300)))
            streams = await stack.enter_async_context(
                streamable_http_client(self._fill(definition.url or ""), http_client=client))
            return streams[0], streams[1]

        if definition.transport == "http":
            return open_http
        if definition.transport == "stdio":
            # a separate process per mode; the definition's command sets the server's own flags
            return open_stdio
        raise ValueError(f"{definition.type} is not an MCP connector")

    async def _session(self, mode: Mode) -> ClientSession:
        if mode not in self._sessions:
            self._sessions[mode] = _Session(self._transport(mode), f"mcp:{self.connection_id}:{mode}")
        return await self._sessions[mode].get()

    # ----- tools -------------------------------------------------------------------------------
    def _spec(self, mapping: ToolMapping, description: str | None, schema: dict | None) -> ToolSpec:
        schema = dict(schema or {"type": "object", "properties": {}})
        hidden = set(mapping.fixed)
        if hidden and isinstance(schema.get("properties"), dict):
            schema["properties"] = {k: v for k, v in schema["properties"].items() if k not in hidden}
            schema["required"] = [r for r in schema.get("required", []) if r not in hidden]
        # arguments the connection fills in are optional for the agent
        if mapping.defaults and isinstance(schema.get("required"), list):
            schema["required"] = [r for r in schema["required"] if r not in mapping.defaults]
        return ToolSpec(
            name=mapping.name, description=mapping.description or description or mapping.name,
            capability=mapping.capability, permission=mapping.permission, input_schema=schema,
            connection_id=self.connection_id, connector_type=self.connector_type,
        )

    async def _offered(self) -> dict[str, Any]:
        session = await self._session("read")
        offered: dict[str, Any] = {}
        cursor = None
        while True:
            page = await session.list_tools(params={"cursor": cursor} if cursor else None)
            offered.update({t.name: t for t in page.tools})
            cursor = getattr(page, "next_cursor", None)
            if not cursor:
                return offered

    async def list_tools(self) -> list[ToolSpec]:
        offered = await self._offered()
        specs: list[ToolSpec] = []
        for mapping in self.definition.tools:
            if mapping.permission == "write":
                # read-only sessions hide write tools, so they are listed from the allowlist
                if self._writes:
                    specs.append(self._spec(mapping, None, {"type": "object", "properties": {}}))
                continue
            tool = offered.get(mapping.upstream)
            if tool is not None:
                specs.append(self._spec(mapping, tool.description, tool.input_schema))
        return specs

    def _arguments(self, mapping: ToolMapping, arguments: dict[str, Any]) -> dict[str, Any]:
        merged = {k: self._fill(v) for k, v in mapping.defaults.items()}
        merged.update({k: v for k, v in arguments.items() if k not in mapping.fixed})
        merged.update({k: self._fill(v) if isinstance(v, str) else v for k, v in mapping.fixed.items()})
        return merged

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        mapping = self._by_name.get(tool_name)
        if mapping is None:
            return ToolResult(ok=False, error=f"{tool_name} is not an allowed tool for {self.connector_type}")
        if mapping.permission == "write" and not self._writes:
            return ToolResult(ok=False, error=f"writes are not enabled for this {self.definition.display_name} connection")
        try:
            args = self._arguments(mapping, arguments)
        except KeyError as exc:
            return ToolResult(ok=False, error=str(exc.args[0]))
        session = await self._session("write" if mapping.permission == "write" else "read")
        try:
            result = await session.call_tool(mapping.upstream, args, read_timeout_seconds=CALL_TIMEOUT_SECONDS)
        except TimeoutError as exc:
            raise ToolTransientError(f"{tool_name} timed out") from exc
        text = "\n".join(getattr(block, "text", "") for block in (result.content or [])
                         if getattr(block, "text", None)).strip()
        if getattr(result, "is_error", False):
            return ToolResult(ok=False, error=text or f"{tool_name} failed")
        return ToolResult(ok=True, content=text, data=getattr(result, "structured_content", None))

    async def health_check(self) -> HealthStatus:
        try:
            offered = await self._offered()
        except Exception as exc:  # noqa: BLE001
            return HealthStatus(ok=False, detail=f"Could not start or reach the {self.definition.display_name} MCP server: {exc}")
        read = [m for m in self.definition.tools if m.permission == "read"]
        available = [m.name for m in read if m.upstream in offered]
        missing = [m.name for m in read if m.upstream not in offered]
        if not available:
            return HealthStatus(ok=False, detail="Connected, but the server offers none of the tools ForgeOps uses. "
                                                 "Check the token's permissions.")
        detail = f"{len(available)} read tools available"
        if self._writes:
            detail += f"; {sum(m.permission == 'write' for m in self.definition.tools)} write tool(s) enabled for approved actions"
        if missing:
            detail += f"; not offered by the server: {', '.join(missing)}"
        return HealthStatus(ok=True, detail=detail)

    async def aclose(self) -> None:
        for session in list(self._sessions.values()):
            await session.close()
        self._sessions.clear()
