import pytest
from pydantic import BaseModel

from forgeops.engine.llm.base import LLMReply, Message, StructuredOutputError
from forgeops.engine.llm.structured import ask_structured
from tests.engine.fakes import ScriptedLLM, call


class Answer(BaseModel):
    value: int


async def _ask(llm, check=None):
    return await ask_structured(llm, purpose="plan", model_role="supervisor", system="S",
                                messages=[Message(role="user", content="q")], schema=Answer,
                                tool_name="submit_answer", tool_description="d", check=check)


async def test_forces_the_submit_tool_and_parses():
    llm = ScriptedLLM({"plan": [call("submit_answer", value=3)]})
    assert (await _ask(llm)).value == 3
    req = llm.requests[0]
    assert req.tool_choice == "submit_answer"
    assert req.tools[0].name == "submit_answer"
    assert req.tools[0].parameters["properties"]["value"]["type"] == "integer"


async def test_repairs_once_after_validation_error():
    llm = ScriptedLLM({"plan": [call("submit_answer", value="nope"), call("submit_answer", value=5)]})
    assert (await _ask(llm)).value == 5
    repair = llm.requests[1].messages
    assert repair[-2].role == "assistant" and repair[-1].role == "tool"
    assert "invalid" in repair[-1].content.lower()


async def test_check_callback_triggers_repair():
    llm = ScriptedLLM({"plan": [call("submit_answer", value=-1), call("submit_answer", value=2)]})
    result = await _ask(llm, check=lambda a: "value must be positive" if a.value < 0 else None)
    assert result.value == 2
    assert "value must be positive" in llm.requests[1].messages[-1].content


async def test_gives_up_after_one_repair():
    llm = ScriptedLLM({"plan": [call("submit_answer", value="a"), call("submit_answer", value="b")]})
    with pytest.raises(StructuredOutputError):
        await _ask(llm)


async def test_text_only_reply_counts_as_invalid():
    llm = ScriptedLLM({"plan": [LLMReply(text="I think 3"), call("submit_answer", value=3)]})
    assert (await _ask(llm)).value == 3
