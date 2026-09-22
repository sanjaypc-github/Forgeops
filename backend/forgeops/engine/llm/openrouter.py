"""OpenRouter chat completions through the OpenAI SDK (OpenAI-compatible API)."""

import asyncio
import json
from collections.abc import Mapping
from typing import Any

import openai
from openai import AsyncOpenAI

from forgeops.config import MODEL_ROLES, Settings
from forgeops.engine.llm.base import (
    LLMError, LLMNotConfigured, LLMReply, LLMRequest, Message, ToolCall,
)


EMPTY_ANSWER_ATTEMPTS = 3


def _to_openai(message: Message) -> dict[str, Any]:
    if message.role == "tool":
        return {"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content}
    if message.role == "assistant" and message.tool_calls:
        return {
            "role": "assistant",
            "content": message.content or None,
            "tool_calls": [
                {"id": c.id, "type": "function",
                 "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                for c in message.tool_calls
            ],
        }
    return {"role": message.role, "content": message.content}


def _tool_choice(choice: str) -> Any:
    if choice in ("auto", "required", "none"):
        return choice
    return {"type": "function", "function": {"name": choice}}


def _parse_arguments(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {"__invalid_json__": raw}
    return value if isinstance(value, dict) else {"__invalid_json__": raw}


class OpenRouterLLM:
    def __init__(
        self,
        *,
        api_key: str,
        models: Mapping[str, str],
        base_url: str,
        timeout: float = 120,
        client: AsyncOpenAI | None = None,
        retry_delay: float = 2.0,
    ) -> None:
        self._models = dict(models)
        self._retry_delay = retry_delay
        self._client = client or AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=2,
            default_headers={"X-Title": "ForgeOps"},
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "OpenRouterLLM":
        key = settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else ""
        if not key.strip():
            raise LLMNotConfigured("OPENROUTER_API_KEY is not set in .env")
        return cls(
            api_key=key.strip(),
            models={role: settings.model_for(role) for role in MODEL_ROLES},
            base_url=settings.openrouter_base_url,
        )

    async def complete(self, request: LLMRequest) -> LLMReply:
        params: dict[str, Any] = {
            "model": self._models[request.model_role],
            "messages": [{"role": "system", "content": request.system}]
            + [_to_openai(m) for m in request.messages],
            "max_tokens": request.max_tokens,
        }
        if request.tools:
            params["tools"] = [
                {"type": "function",
                 "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
                for t in request.tools
            ]
            params["tool_choice"] = _tool_choice(request.tool_choice)
        response = None
        problem = ""
        # Busy (especially free) providers sometimes answer with no choices; retry those briefly.
        for attempt in range(EMPTY_ANSWER_ATTEMPTS):
            try:
                response = await self._client.chat.completions.create(**params)
            except openai.APIError as exc:
                raise LLMError(f"OpenRouter request failed ({type(exc).__name__}): {exc.message}") from exc
            if response.choices:
                break
            error = (getattr(response, "model_extra", None) or {}).get("error") or {}
            problem = str(error.get("message", "")) if isinstance(error, dict) else str(error)
            if attempt + 1 < EMPTY_ANSWER_ATTEMPTS:
                await asyncio.sleep(self._retry_delay * (attempt + 1))
        if response is None or not response.choices:
            raise LLMError("OpenRouter returned no answer" + (f": {problem}" if problem else
                           " (the model provider may be overloaded; try again or use another model)"))
        message = response.choices[0].message
        usage = response.usage
        return LLMReply(
            text=message.content or "",
            tool_calls=[
                ToolCall(id=c.id, name=c.function.name, arguments=_parse_arguments(c.function.arguments))
                for c in (message.tool_calls or [])
            ],
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )
