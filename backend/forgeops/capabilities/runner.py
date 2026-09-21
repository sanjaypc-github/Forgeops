"""Every tool call an agent makes goes through here: policy, timeout, retry, trimming, events."""

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from forgeops.capabilities.models import ToolResult, ToolTransientError
from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.engine.budgets import Budgets
from forgeops.engine.models import AgentId, ToolCallRecord
from forgeops.events.models import EventIn, EventType

Emit = Callable[[EventIn], Awaitable[Any]]
RETRY_DELAYS = (0.25, 0.5)


def _cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _summary(arguments: dict[str, Any]) -> str:
    return _cut(json.dumps(arguments, separators=(",", ":"), default=str), 160)


class ToolRunner:
    def __init__(self, registry: CapabilityRegistry, emit: Emit, budgets: Budgets):
        self._registry = registry
        self._emit = emit
        self._budgets = budgets

    async def _attempt(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                async with asyncio.timeout(self._budgets.tool_timeout_seconds):
                    return await self._registry.call(tool_name, arguments)
            except TimeoutError:
                return ToolResult(ok=False, error=f"timed out after {self._budgets.tool_timeout_seconds:g} s")
            except ToolTransientError as exc:
                if attempt == len(RETRY_DELAYS):
                    return ToolResult(ok=False, error=f"{exc} (after {attempt + 1} attempts)")
                await asyncio.sleep(RETRY_DELAYS[attempt])
            except Exception as exc:  # noqa: BLE001 - reported to the agent as a failed call
                return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}")
        raise AssertionError("unreachable")

    def _truncate(self, result: ToolResult) -> ToolResult:
        limit = self._budgets.tool_output_chars
        if len(result.content) <= limit:
            return result
        dropped = len(result.content) - limit
        return result.model_copy(update={
            "content": result.content[:limit] + f"\n…[truncated {dropped} characters]",
            "truncated": True,
        })

    async def run(
        self, *, agent: AgentId, tool_name: str, arguments: dict[str, Any], allowed: set[str]
    ) -> tuple[ToolResult, ToolCallRecord]:
        call_id = f"tc_{uuid4().hex[:12]}"
        known = self._registry.has_tool(tool_name)
        spec = self._registry.spec(tool_name) if known else None
        connector_type = spec.connector_type if spec else "unknown"
        connection_id = spec.connection_id if spec else "unknown"

        await self._emit(EventIn(type=EventType.tool_called, agent=agent.value, data={
            "call_id": call_id, "tool": tool_name, "connector_type": connector_type,
            "summary": _summary(arguments),
        }))
        started = time.perf_counter()
        if tool_name not in allowed or not known:
            result = ToolResult(ok=False, error=f"{tool_name} is not available to this agent")
        else:
            result = self._truncate(await self._attempt(tool_name, arguments))
        result = result.model_copy(update={"duration_ms": int((time.perf_counter() - started) * 1000)})

        first_line = (result.content.strip().splitlines() or [""])[0] if result.ok else (result.error or "")
        await self._emit(EventIn(type=EventType.tool_completed, agent=agent.value, data={
            "call_id": call_id, "tool": tool_name, "ok": result.ok, "duration_ms": result.duration_ms,
            "truncated": result.truncated, "summary": _cut(first_line, 160),
        }))
        record = ToolCallRecord(
            id=call_id, agent=agent, tool=tool_name, connector_type=connector_type,
            connection_id=connection_id, args_summary=_summary(arguments), ok=result.ok,
            duration_ms=result.duration_ms, truncated=result.truncated,
            result_excerpt=_cut(result.content, 500), error=result.error,
        )
        return result, record
