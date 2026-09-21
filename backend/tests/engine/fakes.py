"""Test-only doubles. Never imported by runtime code."""

import asyncio
import hashlib
import itertools
import math
import re
from collections.abc import Callable

from forgeops.engine.llm.base import LLMReply, LLMRequest, ToolCall

_ids = itertools.count(1)


def call(name: str, **arguments) -> LLMReply:
    """A reply containing one tool call."""
    return LLMReply(tool_calls=[ToolCall(id=f"call_{next(_ids)}", name=name, arguments=arguments)])


Scripted = LLMReply | Callable[[LLMRequest], LLMReply]


class ScriptedLLM:
    """Replies from per-purpose queues; purpose "specialist:code" also matches key "specialist"."""

    def __init__(self, script: dict[str, list[Scripted]]):
        self._script = {key: list(replies) for key, replies in script.items()}
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMReply:
        self.requests.append(request)
        key = request.purpose if request.purpose in self._script else request.purpose.split(":")[0]
        queue = self._script.get(key)
        if not queue:
            raise AssertionError(f"ScriptedLLM has no reply left for purpose {request.purpose!r}")
        reply = queue.pop(0)
        await asyncio.sleep(0)
        return reply(request) if callable(reply) else reply


class HashEmbedder:
    """Deterministic bag-of-words embedding so tests never download a model."""

    def __init__(self, dims: int = 64):
        self.dims = dims

    def __call__(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vec = [0.0] * self.dims
            for token in re.findall(r"\w+", text.lower()):
                vec[int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dims] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class FakeConnector:
    """In-memory connector with fixed tool specs and scripted responses."""

    def __init__(self, connection_id, connector_type, tools, responses, delay: float = 0.0):
        self.connection_id = connection_id
        self.connector_type = connector_type
        self._tools = list(tools)
        self._responses = dict(responses)
        self._delay = delay
        self.calls: list[tuple[str, dict]] = []
        self.closed = False

    async def health_check(self):
        from forgeops.capabilities.models import HealthStatus
        return HealthStatus(ok=True, detail=f"{len(self._tools)} tools")

    async def list_tools(self):
        return list(self._tools)

    async def call(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        if self._delay:
            await asyncio.sleep(self._delay)
        response = self._responses[tool_name]
        if isinstance(response, Exception):
            raise response
        return response(arguments) if callable(response) else response

    async def aclose(self):
        self.closed = True


def collect_events():
    """Returns (events, emit) where emit appends EventIn objects to events."""
    events = []

    async def emit(event):
        events.append(event)
        return event

    return events, emit
