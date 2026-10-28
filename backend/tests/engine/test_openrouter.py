import json

import httpx2
import pytest
from openai import AsyncOpenAI

from forgeops.engine.llm.base import LLMNotConfigured, LLMRequest, Message, ToolCall, ToolSchema
from forgeops.engine.llm.openrouter import OpenRouterLLM

BASE = "https://openrouter.ai/api/v1"
MODELS = {"supervisor": "anthropic/claude-sonnet-5", "specialist": "anthropic/claude-haiku-4.5",
          "rca": "anthropic/claude-sonnet-5"}


def _completion(message: dict) -> dict:
    return {"id": "gen-1", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}}


def _llm(message: dict):
    """LLM whose HTTP traffic goes to an in-memory transport; nothing leaves the machine."""
    seen: list = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(200, json=_completion(message))

    client = AsyncOpenAI(api_key="k", base_url=BASE,
                         http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    return OpenRouterLLM(api_key="k", models=MODELS, base_url=BASE, client=client), seen


async def test_sends_model_system_tools_and_forced_choice():
    llm, seen = _llm({"role": "assistant", "content": None, "tool_calls": [
        {"id": "c1", "type": "function",
         "function": {"name": "submit_plan", "arguments": '{"summary": "s"}'}}]})
    reply = await llm.complete(LLMRequest(
        purpose="plan", model_role="supervisor", system="SYS",
        messages=[Message(role="user", content="hi")],
        tools=[ToolSchema(name="submit_plan", description="d", parameters={"type": "object"})],
        tool_choice="submit_plan"))
    request = seen[-1]
    body = json.loads(request.content)
    assert str(request.url) == f"{BASE}/chat/completions"
    assert body["model"] == "anthropic/claude-sonnet-5"
    assert body["messages"][0] == {"role": "system", "content": "SYS"}
    assert body["tool_choice"] == {"type": "function", "function": {"name": "submit_plan"}}
    assert request.headers["authorization"] == "Bearer k"
    assert reply.tool_calls[0].name == "submit_plan"
    assert reply.tool_calls[0].arguments == {"summary": "s"}
    assert (reply.input_tokens, reply.output_tokens) == (11, 7)


async def test_round_trips_tool_messages():
    llm, seen = _llm({"role": "assistant", "content": "done"})
    await llm.complete(LLMRequest(purpose="specialist:code", model_role="specialist", system="S",
        messages=[Message(role="user", content="go"),
                  Message(role="assistant", tool_calls=[ToolCall(id="c1", name="t", arguments={"a": 1})]),
                  Message(role="tool", tool_call_id="c1", content="result")]))
    msgs = json.loads(seen[-1].content)["messages"]
    assert msgs[2]["tool_calls"][0]["function"] == {"name": "t", "arguments": '{"a": 1}'}
    assert msgs[3] == {"role": "tool", "tool_call_id": "c1", "content": "result"}


async def test_invalid_tool_json_is_preserved_for_repair():
    llm, _ = _llm({"role": "assistant", "content": None, "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "x", "arguments": "{not json"}}]})
    reply = await llm.complete(LLMRequest(purpose="p", model_role="rca", system="S", messages=[]))
    assert reply.tool_calls[0].arguments == {"__invalid_json__": "{not json"}


def test_missing_key_is_a_clear_error():
    from forgeops.config import Settings
    for key in (None, ""):
        s = Settings(_env_file=None, database_url="postgresql+asyncpg://u:p@h/d", forgeops_secret_key="k",
                     forgeops_admin_email="a@b.c", forgeops_admin_password="x", openrouter_api_key=key)
        with pytest.raises(LLMNotConfigured, match="OPENROUTER_API_KEY"):
            OpenRouterLLM.from_settings(s)


async def test_empty_answers_are_retried_then_reported_with_the_provider_message():
    responses = [
        {"id": "g", "object": "chat.completion", "created": 0, "model": "m", "choices": []},
        {"id": "g", "object": "chat.completion", "created": 0, "model": "m", "choices": [],
         "error": {"message": "Provider overloaded", "code": 502}},
        _completion({"role": "assistant", "content": "finally"}),
    ]

    def handler(request):
        return httpx2.Response(200, json=responses.pop(0))

    client = AsyncOpenAI(api_key="k", base_url=BASE,
                         http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    llm = OpenRouterLLM(api_key="k", models=MODELS, base_url=BASE, client=client, retry_delay=0)
    reply = await llm.complete(LLMRequest(purpose="rca", model_role="rca", system="S", messages=[]))
    assert reply.text == "finally" and responses == []


async def test_persistent_empty_answers_fail_with_the_reason():
    from forgeops.engine.llm.base import LLMError

    def handler(request):
        return httpx2.Response(200, json={"id": "g", "object": "chat.completion", "created": 0, "model": "m",
                                          "choices": [], "error": {"message": "Rate limit exceeded: free tier"}})

    client = AsyncOpenAI(api_key="k", base_url=BASE,
                         http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    llm = OpenRouterLLM(api_key="k", models=MODELS, base_url=BASE, client=client, retry_delay=0)
    with pytest.raises(LLMError, match="Rate limit exceeded: free tier"):
        await llm.complete(LLMRequest(purpose="rca", model_role="rca", system="S", messages=[]))


async def test_usage_including_cached_input_tokens_is_reported():
    body = _completion({"role": "assistant", "content": "hello"})
    body["usage"]["prompt_tokens_details"] = {"cached_tokens": 8}
    client = AsyncOpenAI(api_key="k", base_url=BASE, http_client=httpx2.AsyncClient(
        transport=httpx2.MockTransport(lambda request: httpx2.Response(200, json=body))))
    llm = OpenRouterLLM(api_key="k", models=MODELS, base_url=BASE, client=client)

    reply = await llm.complete(LLMRequest(purpose="plan", model_role="supervisor", system="SYS",
                                          messages=[Message(role="user", content="hi")]))
    assert (reply.input_tokens, reply.output_tokens, reply.cached_tokens) == (11, 7, 8)


async def test_prompt_cache_marks_the_stable_system_prefix():
    seen: list = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(200, json=_completion({"role": "assistant", "content": "ok"}))

    client = AsyncOpenAI(api_key="k", base_url=BASE,
                         http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    llm = OpenRouterLLM(api_key="k", models=MODELS, base_url=BASE, client=client, prompt_cache=True)
    await llm.complete(LLMRequest(purpose="plan", model_role="supervisor", system="SYS",
                                  messages=[Message(role="user", content="hi")]))
    body = json.loads(seen[-1].content)
    assert body["messages"][0] == {"role": "system", "content": [
        {"type": "text", "text": "SYS", "cache_control": {"type": "ephemeral"}}]}


def test_each_role_uses_its_own_key_and_shared_roles_share_a_client():
    """Three accounts, one per role: a role's rate limit then belongs to that role alone."""
    llm = OpenRouterLLM(
        api_keys={"supervisor": "k_sup", "specialist": "k_spec", "rca": "k_rca"},
        models=MODELS, base_url=BASE)
    assert llm._clients["supervisor"].api_key == "k_sup"
    assert llm._clients["specialist"].api_key == "k_spec"
    assert llm._clients["rca"].api_key == "k_rca"
    assert len({id(c) for c in llm._clients.values()}) == 3

    one = OpenRouterLLM(api_key="k_all", models=MODELS, base_url=BASE)
    assert {c.api_key for c in one._clients.values()} == {"k_all"}
    assert len({id(c) for c in one._clients.values()}) == 1, "one key, one connection pool"


def test_a_role_without_its_own_key_falls_back_to_the_shared_one():
    llm = OpenRouterLLM(api_key="k_all", api_keys={"rca": "k_rca"}, models=MODELS, base_url=BASE)
    assert llm._clients["rca"].api_key == "k_rca"
    assert llm._clients["supervisor"].api_key == "k_all"
    assert llm._clients["specialist"].api_key == "k_all"


def test_from_settings_reads_a_key_per_role(monkeypatch):
    from forgeops.config import Settings

    settings = Settings(openrouter_api_key_supervisor="k_sup",
                        openrouter_api_key_specialist="k_spec",
                        openrouter_api_key_rca="k_rca")
    assert settings.api_key_for("supervisor") == "k_sup"
    llm = OpenRouterLLM.from_settings(settings)
    assert llm._clients["specialist"].api_key == "k_spec"


def test_from_settings_names_the_roles_that_have_no_key():
    from forgeops.config import Settings

    from forgeops.engine.llm.base import LLMNotConfigured

    settings = Settings(openrouter_api_key=None, openrouter_api_key_rca="k_rca")
    with pytest.raises(LLMNotConfigured) as err:
        OpenRouterLLM.from_settings(settings)
    assert "supervisor" in str(err.value) and "specialist" in str(err.value)
    assert "rca" not in str(err.value).split(".")[0]
