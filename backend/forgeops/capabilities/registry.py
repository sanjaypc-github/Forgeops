"""Which agent may use which tool, for one investigation's set of connections."""

from typing import Any

import structlog

from forgeops.capabilities.models import Connector, ToolResult, ToolSpec
from forgeops.capabilities.routing import agent_for_capability
from forgeops.engine.models import SPECIALISTS, AgentId, Capability

log = structlog.get_logger()


class CapabilityRegistry:
    def __init__(self, connectors: list[Connector], tools: list[ToolSpec], warnings: list[str]):
        self._connectors = connectors
        self._tools = {t.name: t for t in tools}
        self._owner = {t.name: c for c in connectors for t in tools if t.connection_id == c.connection_id}
        self.warnings = warnings
        self.service_map = ""  # what the connections point at, for the Supervisor's plan

    @classmethod
    async def build(cls, connectors: list[Connector], warnings: list[str] | None = None) -> "CapabilityRegistry":
        tools: list[ToolSpec] = []
        warnings = list(warnings or [])
        for connector in connectors:
            try:
                tools.extend(await connector.list_tools())
            except Exception as exc:  # noqa: BLE001 - a broken connector must not stop the others
                warnings.append(
                    f"{connector.connector_type} ({connector.connection_id}) unavailable: {exc}"
                )
                log.warning("connector.unavailable", connection_id=connector.connection_id, error=str(exc))
        return cls(connectors, tools, warnings)

    def tools_for(self, agent: AgentId) -> list[ToolSpec]:
        """Read tools for investigating agents; write tools only for the Action agent."""
        permission = "write" if agent == AgentId.action else "read"
        return [
            t for t in self._tools.values()
            if t.permission == permission and agent_for_capability(t.capability) == agent
        ]

    def connected_agents(self) -> dict[AgentId, list[Capability]]:
        connected: dict[AgentId, list[Capability]] = {}
        for agent in SPECIALISTS:
            caps = sorted({t.capability for t in self.tools_for(agent)}, key=list(Capability).index)
            if caps:
                connected[agent] = caps
        return connected

    def spec(self, name: str) -> ToolSpec:
        return self._tools[name]

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    async def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        return await self._owner[name].call(name, arguments)

    async def aclose(self) -> None:
        for connector in self._connectors:
            try:
                await connector.aclose()
            except Exception as exc:  # noqa: BLE001
                log.warning("connector.close_failed", connection_id=connector.connection_id, error=str(exc))
