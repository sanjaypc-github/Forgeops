import pytest

from forgeops.engine.llm.base import LLMError, LLMReply, LLMRequest, Message
from forgeops.engine.llm.metering import MeteredLLM, UsageMeter, agent_for_purpose, merge_usage
from tests.engine.fakes import collect_events


def _request(purpose: str) -> LLMRequest:
    return LLMRequest(purpose=purpose, model_role="specialist", system="s",
                      messages=[Message(role="user", content="hi")])


class _Stub:
    def __init__(self, replies):
        self._replies = list(replies)

    async def complete(self, request):
        reply = self._replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_purpose_maps_to_the_desk_that_spent_it():
    assert agent_for_purpose("specialist:database") == "database"
    assert agent_for_purpose("answer:code") == "code"
    assert agent_for_purpose("plan") == "supervisor"
    assert agent_for_purpose("review") == "supervisor"
    assert agent_for_purpose("rca") == "rca"


async def test_every_call_is_counted_per_desk_and_emitted():
    events, emit = collect_events()
    meter = UsageMeter(emit)
    llm = MeteredLLM(_Stub([
        LLMReply(text="a", input_tokens=1200, output_tokens=80, cached_tokens=900),
        LLMReply(text="b", input_tokens=300, output_tokens=20),
    ]), meter)

    await llm.complete(_request("specialist:database"))
    await llm.complete(_request("rca"))

    usage = meter.usage
    assert (usage.calls, usage.input_tokens, usage.output_tokens, usage.cached_tokens) == (2, 1500, 100, 900)
    assert usage.by_agent["database"].input_tokens == 1200
    assert usage.by_agent["rca"].output_tokens == 20
    assert [e.type for e in events] == ["llm_usage", "llm_usage"]
    first = events[0]
    assert first.agent == "database" and first.data["purpose"] == "specialist:database"
    assert first.data["input_tokens"] == 1200 and first.data["cached_tokens"] == 900
    assert events[1].data["run_input_tokens"] == 1500 and events[1].data["run_calls"] == 2


async def test_a_failed_call_is_still_counted_and_the_error_is_raised():
    events, emit = collect_events()
    meter = UsageMeter(emit)
    llm = MeteredLLM(_Stub([LLMError("provider down")]), meter)

    with pytest.raises(LLMError):
        await llm.complete(_request("plan"))

    assert meter.usage.calls == 1 and meter.usage.failed_calls == 1
    assert meter.usage.by_agent["supervisor"].failed_calls == 1
    assert events[0].data["ok"] is False


async def test_compaction_savings_are_recorded():
    meter = UsageMeter()
    meter.record_saved("code", 4000)
    meter.record_saved("code", 1000)
    assert meter.usage.saved_tokens == 5000 and meter.usage.by_agent["code"].saved_tokens == 5000


def test_resuming_an_investigation_adds_to_what_it_already_spent():
    first = {"calls": 2, "input_tokens": 100, "output_tokens": 10, "cached_tokens": 0, "saved_tokens": 0,
             "failed_calls": 0, "by_agent": {"code": {"calls": 2, "input_tokens": 100, "output_tokens": 10,
                                                      "cached_tokens": 0, "saved_tokens": 0, "failed_calls": 0}}}
    second = {"calls": 1, "input_tokens": 50, "output_tokens": 5, "cached_tokens": 0, "saved_tokens": 0,
              "failed_calls": 0, "by_agent": {"rca": {"calls": 1, "input_tokens": 50, "output_tokens": 5,
                                                      "cached_tokens": 0, "saved_tokens": 0, "failed_calls": 0}}}
    merged = merge_usage(first, second)
    assert merged["calls"] == 3 and merged["input_tokens"] == 150
    assert set(merged["by_agent"]) == {"code", "rca"}
    assert merge_usage(None, second) == second
