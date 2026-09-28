"""A stand-in for the model, for building and demonstrating ForgeOps without a provider key.

It is **not** a model and never pretends to be one. It drives the real graph against the real
connectors: desks call their actual read tools and the real tool output becomes the evidence. Only
the reasoning is missing, so every answer it produces is labelled, and the label travels all the way
into the report, so nobody can mistake a demo run for an investigation.

Enable with `FORGEOPS_LLM=offline`. It refuses to start when `FORGEOPS_ENV=production`.
"""

import json
from typing import Any

import structlog

from forgeops.engine.llm.base import LLMNotConfigured, LLMReply, LLMRequest, ToolCall

log = structlog.get_logger()

LABEL = "OFFLINE MODE (no language model connected)"
NOTE = ("This run used ForgeOps' offline stand-in: the desks called their real tools, but nothing "
        "analysed the results. Connect a model and run again for a real root cause.")
SUBMIT_TOOLS = ("submit_plan", "submit_review", "submit_findings", "submit_rca")


def _call(name: str, **arguments: Any) -> LLMReply:
    return LLMReply(tool_calls=[ToolCall(id=f"offline_{name}", name=name, arguments=arguments)],
                    input_tokens=0, output_tokens=0)


AVAILABLE_HEADING = "Desks with connected tools"
UNAVAILABLE_HEADING = "Desks without connected tools"


def _desks(request: LLMRequest) -> list[str]:
    """Only the desks listed as connected; assigning any other one is rejected by the contract."""
    desks: list[str] = []
    listening = False
    for line in request.system.splitlines():
        stripped = line.strip()
        if stripped.startswith(AVAILABLE_HEADING):
            listening = True
            continue
        if stripped.startswith(UNAVAILABLE_HEADING):
            break
        if listening and stripped.startswith("- ") and ":" in stripped:
            name = stripped[2:].split(":", 1)[0].strip()
            if name.isidentifier() and name not in desks:
                desks.append(name)
    return desks


def _evidence_ids(request: LLMRequest) -> list[str]:
    text = " ".join(m.content for m in request.messages)
    return [token.strip(".,;|") for token in text.split() if token.startswith("ev_")]


def _call_ids(request: LLMRequest) -> list[str]:
    ids: list[str] = []
    for message in request.messages:
        for part in message.content.split('call_id="')[1:]:
            ids.append(part.split('"')[0])
    return ids


def _first_read_tool(request: LLMRequest) -> str | None:
    for tool in request.tools:
        if tool.name not in SUBMIT_TOOLS and tool.name != "ask_agent":
            return tool.name
    return None


def _arguments_for(request: LLMRequest, tool_name: str) -> dict[str, Any]:
    """Only what the tool marks required; the connection fills in owner, repo and the rest."""
    schema = next((t.parameters for t in request.tools if t.name == tool_name), {}) or {}
    properties = schema.get("properties") or {}
    arguments: dict[str, Any] = {}
    for key in schema.get("required") or []:
        spec = properties.get(key) or {}
        if spec.get("enum"):
            arguments[key] = spec["enum"][0]
        elif spec.get("type") == "integer" or spec.get("type") == "number":
            arguments[key] = 1
        elif spec.get("type") == "boolean":
            arguments[key] = False
        else:
            arguments[key] = "recent"
    return arguments


class OfflineLLM:
    """Deterministic, labelled replies that keep the investigation moving without a provider."""

    @classmethod
    def from_settings(cls, settings) -> "OfflineLLM":
        if settings.forgeops_env == "production":
            raise LLMNotConfigured(
                "FORGEOPS_LLM=offline is a development stand-in and refuses to run in production. "
                "Set OPENROUTER_API_KEY and FORGEOPS_LLM=openrouter.")
        log.warning("llm.offline_mode", detail="no model connected; runs are labelled as demos")
        return cls()

    async def complete(self, request: LLMRequest) -> LLMReply:
        purpose = request.purpose.split(":")[0]
        if purpose == "plan":
            return self._plan(request)
        if purpose == "review":
            return _call("submit_review", sufficient=True,
                         reason=f"{LABEL}: no model reviewed this evidence.", follow_up_tasks=[])
        if purpose == "rca":
            return self._rca(request)
        if purpose in ("specialist", "answer"):
            return self._specialist(request)
        return LLMReply(text=f"{LABEL}. {NOTE}")

    def _plan(self, request: LLMRequest) -> LLMReply:
        desks = _desks(request)
        return _call(
            "submit_plan", summary=f"{LABEL}: every connected desk collects what its tools can read.",
            affected_service=None, window_start=None, window_end=None,
            hypotheses=["Not a hypothesis: no model is connected to form one."], not_relevant=[],
            tasks=[{"agent": desk, "objective": f"Collect what your tools report ({LABEL})."}
                   for desk in desks])

    def _specialist(self, request: LLMRequest) -> LLMReply:
        """First turn: call one real tool. Second turn: report exactly what came back."""
        made = _call_ids(request)
        if not made:
            tool = _first_read_tool(request)
            if tool is None:
                return _call("submit_findings", summary=f"{LABEL}: this desk has no tools.", findings=[])
            return _call(tool, **_arguments_for(request, tool))
        excerpt = request.messages[-1].content
        if len(excerpt) > 400:
            excerpt = excerpt[:400] + "…"
        return _call("submit_findings", summary=f"{LABEL}: raw tool output, not analysis.", findings=[{
            "finding": f"{LABEL}. The tool returned: {json.dumps(excerpt)[1:-1]}",
            "failure_point": None, "artifacts": [], "severity": "info", "confidence": 0.0,
            "limitations": NOTE, "tool_call_ids": made[-1:]}])

    def _rca(self, request: LLMRequest) -> LLMReply:
        return _call(
            "submit_rca", summary=f"{LABEL}. {NOTE}", failure_point="unknown (no model connected)",
            category="unknown", confidence=0.0, timeline=[],
            supporting_evidence=_evidence_ids(request)[:3], contradicting_evidence=[],
            alternative_hypotheses=[], missing_information=[NOTE], recommendations=[])
