"""Token accounting for every model call: which desk spent it, on what, and what was cached.

ForgeOps cannot tune what it cannot see, so every call through `MeteredLLM` is measured, attributed
to a desk and emitted as an event. The totals are stored with the investigation.
"""

import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from pydantic import BaseModel, Field

from forgeops.engine.llm.base import LLM, LLMRequest, LLMReply
from forgeops.events.models import EventIn, EventType

log = structlog.get_logger()
Emit = Callable[[EventIn], Awaitable[Any]]

# purposes that are not "<purpose>:<agent>"
_AGENT_BY_PURPOSE = {"plan": "supervisor", "review": "supervisor", "rca": "rca"}


def agent_for_purpose(purpose: str) -> str:
    """"specialist:database" -> "database"; "plan" -> "supervisor"."""
    if ":" in purpose:
        return purpose.split(":", 1)[1]
    return _AGENT_BY_PURPOSE.get(purpose, purpose)


class AgentUsage(BaseModel):
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0  # part of input_tokens the provider served from its prompt cache
    saved_tokens: int = 0  # input tokens not sent, because older tool output was compacted
    failed_calls: int = 0


class RunUsage(AgentUsage):
    by_agent: dict[str, AgentUsage] = Field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class UsageMeter:
    """Collects usage for one investigation."""

    def __init__(self, emit: Emit | None = None) -> None:
        self.usage = RunUsage()
        self._emit = emit

    def attach(self, emit: Emit) -> None:
        """Start publishing usage events (the run's event stream is created after the meter)."""
        self._emit = emit

    def _bucket(self, agent: str) -> AgentUsage:
        return self.usage.by_agent.setdefault(agent, AgentUsage())

    def _add(self, agent: str, **fields: int) -> AgentUsage:
        bucket = self._bucket(agent)
        for name, value in fields.items():
            setattr(bucket, name, getattr(bucket, name) + value)
            setattr(self.usage, name, getattr(self.usage, name) + value)
        return bucket

    def record_saved(self, agent: str, tokens: int) -> None:
        """Input tokens a desk did not have to send, because its older tool output was compacted."""
        if tokens > 0:
            self._add(agent, saved_tokens=tokens)

    async def record(self, request: LLMRequest, reply: LLMReply | None, duration_ms: int) -> None:
        agent = agent_for_purpose(request.purpose)
        if reply is None:
            self._add(agent, calls=1, failed_calls=1)
        else:
            self._add(agent, calls=1, input_tokens=reply.input_tokens,
                      output_tokens=reply.output_tokens, cached_tokens=reply.cached_tokens)
        bucket = self._bucket(agent)
        log.info("llm.call", purpose=request.purpose, agent=agent, ok=reply is not None,
                 input_tokens=getattr(reply, "input_tokens", 0),
                 output_tokens=getattr(reply, "output_tokens", 0),
                 cached_tokens=getattr(reply, "cached_tokens", 0), duration_ms=duration_ms)
        if self._emit is not None:
            await self._emit(EventIn(type=EventType.llm_usage, agent=agent, data={
                "purpose": request.purpose, "ok": reply is not None, "duration_ms": duration_ms,
                "input_tokens": getattr(reply, "input_tokens", 0),
                "output_tokens": getattr(reply, "output_tokens", 0),
                "cached_tokens": getattr(reply, "cached_tokens", 0),
                "agent_input_tokens": bucket.input_tokens, "agent_output_tokens": bucket.output_tokens,
                "run_input_tokens": self.usage.input_tokens,
                "run_output_tokens": self.usage.output_tokens,
                "run_saved_tokens": self.usage.saved_tokens,
                "run_calls": self.usage.calls,
            }))

    def snapshot(self) -> dict[str, Any]:
        return self.usage.model_dump()


_COUNTERS = ("calls", "input_tokens", "output_tokens", "cached_tokens", "saved_tokens", "failed_calls")


def merge_usage(previous: dict[str, Any] | None, latest: dict[str, Any]) -> dict[str, Any]:
    """Add a resumed run's usage to what the investigation already spent."""
    if not previous:
        return latest
    merged = dict(previous)
    for name in _COUNTERS:
        merged[name] = previous.get(name, 0) + latest.get(name, 0)
    agents = dict(previous.get("by_agent") or {})
    for agent, spent in (latest.get("by_agent") or {}).items():
        before = agents.get(agent, {})
        agents[agent] = {name: before.get(name, 0) + spent.get(name, 0) for name in _COUNTERS}
    merged["by_agent"] = agents
    return merged


class MeteredLLM:
    """Wraps any LLM so every call is timed, counted and attributed to a desk."""

    def __init__(self, inner: LLM, meter: UsageMeter) -> None:
        self._inner = inner
        self._meter = meter

    async def complete(self, request: LLMRequest) -> LLMReply:
        started = time.perf_counter()
        try:
            reply = await self._inner.complete(request)
        except Exception:
            await self._meter.record(request, None, int((time.perf_counter() - started) * 1000))
            raise
        await self._meter.record(request, reply, int((time.perf_counter() - started) * 1000))
        return reply
