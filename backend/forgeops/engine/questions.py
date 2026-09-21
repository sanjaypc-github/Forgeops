"""Agent-to-agent questions: bounded, cached, evented (the office animates the walk)."""

from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from forgeops.engine.budgets import Budgets
from forgeops.engine.models import SPECIALISTS, AgentId, AgentQuestion
from forgeops.engine.specialist import SpecialistResult
from forgeops.events.models import EventIn, EventType

Answer = Callable[[AgentId, AgentId, str], Awaitable[SpecialistResult]]
Emit = Callable[[EventIn], Awaitable[Any]]


def _normalise(question: str) -> str:
    return " ".join(question.lower().split())


def _answer_text(result: SpecialistResult) -> str:
    lines = [result.summary or "No summary."]
    for ev in result.evidence:
        where = f" (failure point: {ev.failure_point})" if ev.failure_point else ""
        lines.append(f"- {ev.id}: {ev.finding}{where} [cite tool_call_ids {', '.join(ev.tool_call_ids)}]")
    return "\n".join(lines)


class QuestionBroker:
    def __init__(self, *, answer: Answer, available: set[AgentId], emit: Emit, budgets: Budgets):
        self._answer = answer
        self._available = available
        self._emit = emit
        self._budgets = budgets
        self._per_agent: Counter[AgentId] = Counter()
        self._total = 0
        self._cache: dict[tuple[AgentId, str], str] = {}

    def _refusal(self, from_agent: AgentId, to_agent: AgentId) -> str | None:
        if to_agent == from_agent:
            return "an agent cannot ask itself"
        if to_agent not in SPECIALISTS:
            return f"{to_agent.value} is not a specialist desk"
        if to_agent not in self._available:
            return f"no connector for the {to_agent.value} desk"
        if self._per_agent[from_agent] >= self._budgets.questions_per_agent:
            return "question limit reached for this agent"
        if self._total >= self._budgets.questions_total:
            return "question limit reached for this investigation"
        return None

    async def ask(
        self, from_agent: AgentId, to_agent: AgentId, question: str
    ) -> tuple[str, AgentQuestion, SpecialistResult | None]:
        qid = f"q_{uuid4().hex[:10]}"
        key = (to_agent, _normalise(question))
        if key in self._cache:
            text = self._cache[key]
            return text, AgentQuestion(id=qid, from_agent=from_agent, to_agent=to_agent, question=question,
                                       answer=text, status="answered", reason="cached"), None

        base = {"from": from_agent.value, "to": to_agent.value, "question_id": qid, "question": question}
        reason = self._refusal(from_agent, to_agent)
        if reason:
            await self._emit(EventIn(type=EventType.agent_question_failed, agent=from_agent.value,
                                     data=base | {"reason": reason}))
            return (f"Question not sent: {reason}.",
                    AgentQuestion(id=qid, from_agent=from_agent, to_agent=to_agent, question=question,
                                  status="refused", reason=reason), None)

        self._per_agent[from_agent] += 1
        self._total += 1
        await self._emit(EventIn(type=EventType.agent_question, agent=from_agent.value, data=base))
        try:
            result = await self._answer(from_agent, to_agent, question)
        except Exception as exc:  # noqa: BLE001 - the asker continues without the answer
            reason = f"{type(exc).__name__}: {exc}"
            await self._emit(EventIn(type=EventType.agent_question_failed, agent=to_agent.value,
                                     data=base | {"reason": reason}))
            return (f"The {to_agent.value} desk could not answer: {reason}",
                    AgentQuestion(id=qid, from_agent=from_agent, to_agent=to_agent, question=question,
                                  status="failed", reason=reason), None)

        text = _answer_text(result)
        self._cache[key] = text
        await self._emit(EventIn(type=EventType.agent_answer, agent=to_agent.value,
                                 data=base | {"answer": text[:300]}))
        return text, AgentQuestion(id=qid, from_agent=from_agent, to_agent=to_agent, question=question,
                                   answer=text, status="answered"), result
