from dataclasses import replace

from forgeops.engine.budgets import Budgets
from forgeops.engine.models import AgentId
from forgeops.engine.questions import QuestionBroker
from forgeops.engine.specialist import SpecialistResult
from tests.engine.fakes import collect_events


def _broker(budgets=Budgets(), fail=False):
    asked = []

    async def answer(from_agent, to_agent, question):
        asked.append((from_agent, to_agent, question))
        if fail:
            raise RuntimeError("target crashed")
        return SpecialistResult(evidence=[], tool_calls=[], questions=[], summary=f"answer to {question}")

    events, emit = collect_events()
    broker = QuestionBroker(answer=answer, available={AgentId.code, AgentId.database},
                            emit=emit, budgets=budgets)
    return broker, asked, events


async def test_question_is_answered_and_evented():
    broker, asked, events = _broker()
    text, q, _ = await broker.ask(AgentId.database, AgentId.code, "What changed in db config?")
    assert text.startswith("answer to What changed in db config?") and q.status == "answered"
    assert [e.type for e in events] == ["agent_question", "agent_answer"]
    assert events[0].data["from"] == "database" and events[0].data["to"] == "code"
    assert events[0].data["question_id"] == events[1].data["question_id"] == q.id


async def test_refusals():
    broker, asked, events = _broker()
    for to in (AgentId.database, AgentId.rca, AgentId.observability):
        _, q, _ = await broker.ask(AgentId.database, to, "q")
        assert q.status == "refused" and q.reason
    assert asked == [] and {e.type for e in events} == {"agent_question_failed"}


async def test_limits_and_cache():
    broker, asked, _ = _broker(replace(Budgets(), questions_per_agent=1))
    await broker.ask(AgentId.database, AgentId.code, "Same Q ")
    text, q, _ = await broker.ask(AgentId.database, AgentId.code, "same q")
    assert q.status == "answered" and len(asked) == 1  # cached, not counted
    _, q2, _ = await broker.ask(AgentId.database, AgentId.code, "another")
    assert q2.status == "refused" and "limit" in q2.reason


async def test_total_limit():
    broker, asked, _ = _broker(replace(Budgets(), questions_total=1))
    await broker.ask(AgentId.database, AgentId.code, "one")
    _, q, _ = await broker.ask(AgentId.code, AgentId.database, "two")
    assert q.status == "refused" and len(asked) == 1


async def test_failed_answer():
    broker, _, events = _broker(fail=True)
    _, q, _ = await broker.ask(AgentId.database, AgentId.code, "q")
    assert q.status == "failed" and events[-1].type == "agent_question_failed"
