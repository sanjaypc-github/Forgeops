"""One specialist desk working a task: think, call read tools, ask colleagues, submit cited findings."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.capabilities.runner import ToolRunner
from forgeops.engine import prompts
from forgeops.engine.budgets import Budgets
from forgeops.engine.llm.base import LLM, LLMRequest, Message, ToolCall, ToolSchema
from forgeops.engine.models import (
    AgentId, AgentQuestion, AgentTask, Artifact, Capability, Evidence, Incident, Severity,
    ToolCallRecord,
)
from forgeops.engine.roster import PROFILES
from forgeops.events.models import EventIn, EventType

if TYPE_CHECKING:
    from forgeops.engine.questions import QuestionBroker

Emit = Callable[[EventIn], Awaitable[Any]]
SUBMIT = "submit_findings"
ASK = "ask_agent"
NUDGE = "Use one of your tools or call submit_findings."
MAX_NUDGES = 2
FORCED_SUBMIT_SECONDS = 15


class FindingDraft(BaseModel):
    finding: str
    failure_point: str | None = None
    capability: Capability | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: str | None = None
    tool_call_ids: list[str] = Field(min_length=1)


class FindingsSubmission(BaseModel):
    summary: str
    findings: list[FindingDraft] = Field(default_factory=list)


class SpecialistResult(BaseModel):
    evidence: list[Evidence] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    questions: list[AgentQuestion] = Field(default_factory=list)
    summary: str = ""
    error: str | None = None


def llm_tool_name(name: str) -> str:
    """Model APIs only accept [a-zA-Z0-9_-] in tool names."""
    return name.replace(".", "__")


def _wrap(call_id: str, tool: str, ok: bool, body: str) -> str:
    return f'<tool_output tool="{tool}" call_id="{call_id}" ok="{str(ok).lower()}">\n{body}\n</tool_output>'


class SpecialistLoop:
    def __init__(
        self,
        *,
        llm: LLM,
        agent: AgentId,
        registry: CapabilityRegistry,
        tool_runner: ToolRunner,
        emit: Emit,
        budgets: Budgets,
        broker: "QuestionBroker | None",
        max_tool_calls: int,
        seconds: float,
        colleagues: list[AgentId],
        purpose: str = "specialist",
        announce: bool = True,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.llm = llm
        self.agent = agent
        self.registry = registry
        self.tool_runner = tool_runner
        self.emit = emit
        self.budgets = budgets
        self.broker = broker
        self.max_tool_calls = max_tool_calls
        self.seconds = seconds
        self.colleagues = [c for c in colleagues if c != agent] if broker else []
        self.purpose = f"{purpose}:{agent.value}"
        self.announce = announce
        self.now = now

        self.tools = registry.tools_for(agent)
        self._by_llm_name = {llm_tool_name(t.name): t.name for t in self.tools}
        self._by_llm_name.update({t.name: t.name for t in self.tools})
        self._messages: list[Message] = []
        self._records: list[ToolCallRecord] = []
        self._questions: list[AgentQuestion] = []
        self._borrowed_records: list[ToolCallRecord] = []
        self._borrowed_evidence: list[Evidence] = []

    # ----- prompt and tool schemas -------------------------------------------------------------
    def _system(self) -> str:
        profile = PROFILES[self.agent]
        colleagues = "\n".join(f"- {c.value}: {PROFILES[c].title} ({PROFILES[c].area})"
                               for c in self.colleagues) or "- none (answer from your own tools only)"
        budget = f"at most {self.max_tool_calls} tool calls and {int(self.seconds)} seconds"
        return prompts.system("specialist", now=self.now().isoformat(timespec="seconds"),
                              agent_title=profile.title, area=profile.area, focus=profile.focus,
                              colleagues=colleagues, budget=budget)

    def _task_message(self, task: AgentTask, incident: Incident, plan_summary: str) -> str:
        lines = [f"Objective: {task.objective}"]
        if task.hints:
            lines.append("Hints: " + "; ".join(task.hints))
        lines += [f"Problem reported: {incident.text}", f"Investigation plan: {plan_summary}"]
        if incident.window_start or incident.window_end:
            lines.append(f"Time window (UTC): {incident.window_start or '?'} to {incident.window_end or 'now'}")
        if incident.service_hint:
            lines.append(f"Service: {incident.service_hint}")
        if incident.notes:
            lines.append("Notes from the user: " + " | ".join(incident.notes))
        if not self.tools:
            lines.append("You have no tools connected; submit an empty findings list explaining that.")
        return "\n".join(lines)

    def _schemas(self) -> list[ToolSchema]:
        schemas = [ToolSchema(name=llm_tool_name(t.name), description=t.description,
                              parameters=t.input_schema) for t in self.tools]
        if self.colleagues:
            schemas.append(ToolSchema(
                name=ASK,
                description="Ask another desk one precise question that needs its tools. "
                            "Returns its evidence-backed answer.",
                parameters={"type": "object", "properties": {
                    "agent": {"type": "string", "enum": [c.value for c in self.colleagues]},
                    "question": {"type": "string"}}, "required": ["agent", "question"]},
            ))
        schemas.append(ToolSchema(
            name=SUBMIT, description="Submit your findings and finish this task.",
            parameters=FindingsSubmission.model_json_schema(),
        ))
        return schemas

    # ----- findings validation -----------------------------------------------------------------
    def _accept(self, call: ToolCall) -> tuple[SpecialistResult | None, str]:
        try:
            submission = FindingsSubmission.model_validate(call.arguments)
        except ValidationError as exc:
            return None, "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        records = {r.id: r for r in self._records + self._borrowed_records if r.ok}
        bad = sorted({i for f in submission.findings for i in f.tool_call_ids if i not in records})
        if bad:
            valid = ", ".join(sorted(records)) or "none (you made no successful tool calls)"
            return None, (f"tool_call_ids {', '.join(bad)} are not results of successful tool calls. "
                          f"Valid ids: {valid}")
        evidence = list(self._borrowed_evidence)
        for draft in submission.findings:
            first = records[draft.tool_call_ids[0]]
            capability = draft.capability or (
                self.registry.spec(first.tool).capability if self.registry.has_tool(first.tool)
                else Capability.knowledge)
            evidence.append(Evidence(
                id=f"ev_{uuid4().hex[:10]}", agent=self.agent, capability=capability,
                connection_id=first.connection_id, connector_type=first.connector_type,
                finding=draft.finding, failure_point=draft.failure_point, artifacts=draft.artifacts,
                severity=draft.severity, confidence=draft.confidence, limitations=draft.limitations,
                tool_call_ids=draft.tool_call_ids,
            ))
        return SpecialistResult(evidence=evidence, tool_calls=list(self._records),
                                questions=list(self._questions), summary=submission.summary), ""

    # ----- tool execution ----------------------------------------------------------------------
    async def _handle(self, call: ToolCall, tool_count: int) -> tuple[str, int]:
        if call.name == ASK and self.broker is not None:
            try:
                target = AgentId(str(call.arguments.get("agent", "")))
            except ValueError:
                return f"Unknown agent {call.arguments.get('agent')!r}.", tool_count
            text, question, answered = await self.broker.ask(self.agent, target,
                                                             str(call.arguments.get("question", "")))
            self._questions.append(question)
            if answered is not None:
                self._borrowed_records += [r for r in answered.tool_calls if r.ok]
                self._borrowed_evidence += answered.evidence
            return text, tool_count

        real = self._by_llm_name.get(call.name)
        if real is None:
            return f"Unknown tool {call.name}. Use one of your listed tools.", tool_count
        if tool_count >= self.max_tool_calls:
            return "Tool budget reached; call submit_findings now with what you have.", tool_count
        result, record = await self.tool_runner.run(agent=self.agent, tool_name=real,
                                                    arguments=call.arguments, allowed=set(self._by_llm_name.values()))
        self._records.append(record)
        body = result.content if result.ok else f"ERROR: {result.error}"
        return _wrap(record.id, real, result.ok, body), tool_count + 1

    async def _loop(self) -> SpecialistResult:
        tool_count = nudges = repairs = 0
        schemas = self._schemas()
        while True:
            force = tool_count >= self.max_tool_calls or nudges >= MAX_NUDGES or repairs > 0
            reply = await self.llm.complete(LLMRequest(
                purpose=self.purpose, model_role="specialist", system=self._system(),
                messages=self._messages, tools=schemas, tool_choice=SUBMIT if force else "auto"))
            if not reply.tool_calls:
                self._messages += [Message(role="assistant", content=reply.text),
                                   Message(role="user", content=NUDGE)]
                nudges += 1
                continue
            self._messages.append(Message(role="assistant", content=reply.text, tool_calls=reply.tool_calls))
            for call in reply.tool_calls:
                if call.name == SUBMIT:
                    result, problem = self._accept(call)
                    if result is not None:
                        return result
                    if repairs >= 1:
                        raise ValueError(f"findings rejected twice: {problem}")
                    repairs += 1
                    content = f"Your submit_findings was rejected: {problem}. Call submit_findings again."
                else:
                    content, tool_count = await self._handle(call, tool_count)
                self._messages.append(Message(role="tool", tool_call_id=call.id, content=content))

    async def _forced_submit(self) -> SpecialistResult:
        self._messages.append(Message(role="user", content="Time budget reached. Call submit_findings now."))
        try:
            async with asyncio.timeout(FORCED_SUBMIT_SECONDS):
                reply = await self.llm.complete(LLMRequest(
                    purpose=self.purpose, model_role="specialist", system=self._system(),
                    messages=self._messages, tools=self._schemas(), tool_choice=SUBMIT))
            submitted = next((c for c in reply.tool_calls if c.name == SUBMIT), None)
            if submitted is not None:
                result, _ = self._accept(submitted)
                if result is not None:
                    return result
        except Exception:  # noqa: BLE001 - reported as an exhausted budget below
            pass
        return SpecialistResult(tool_calls=list(self._records), questions=list(self._questions),
                                error="time budget exhausted")

    # ----- public ------------------------------------------------------------------------------
    async def run(self, task: AgentTask, incident: Incident, plan_summary: str) -> SpecialistResult:
        self._messages = [Message(role="user", content=self._task_message(task, incident, plan_summary))]
        if self.announce:
            await self.emit(EventIn(type=EventType.agent_started, agent=self.agent.value,
                                    data={"objective": task.objective}))
        try:
            async with asyncio.timeout(self.seconds):
                result = await self._loop()
        except TimeoutError:
            result = await self._forced_submit()
        except Exception as exc:  # noqa: BLE001 - one desk failing must not stop the investigation
            result = SpecialistResult(tool_calls=list(self._records), questions=list(self._questions),
                                      error=f"{type(exc).__name__}: {exc}")

        own = [e for e in result.evidence if e.agent == self.agent]
        for evidence in own:
            await self.emit(EventIn(type=EventType.evidence_added, agent=self.agent.value, data={
                "evidence_id": evidence.id, "finding": evidence.finding, "severity": evidence.severity,
                "confidence": evidence.confidence, "failure_point": evidence.failure_point,
                "connector_type": evidence.connector_type}))
        if result.error and not own:
            await self.emit(EventIn(type=EventType.agent_failed, agent=self.agent.value,
                                    data={"error": result.error}))
        elif self.announce:
            await self.emit(EventIn(type=EventType.agent_completed, agent=self.agent.value,
                                    data={"findings": len(own), "summary": result.summary}))
        return result
