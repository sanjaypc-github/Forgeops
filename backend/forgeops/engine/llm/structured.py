"""Structured answers as forced tool calls, validated by Pydantic, with exactly one repair."""

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from forgeops.engine.llm.base import (
    LLM, LLMReply, LLMRequest, Message, ModelRole, StructuredOutputError, ToolCall, ToolSchema,
)

T = TypeVar("T", bound=BaseModel)


def _validate(
    reply: LLMReply, schema: type[T], tool_name: str, check: Callable[[T], str | None] | None
) -> tuple[T | None, str]:
    submitted = next((c for c in reply.tool_calls if c.name == tool_name), None)
    if submitted is None:
        return None, f"You did not call {tool_name}."
    if "__invalid_json__" in submitted.arguments:
        return None, "The arguments were not valid JSON."
    try:
        value = schema.model_validate(submitted.arguments)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'input'}: {e['msg']}" for e in exc.errors()
        )
        return None, problems
    if check is not None and (problem := check(value)):
        return None, problem
    return value, ""


async def ask_structured(
    llm: LLM,
    *,
    purpose: str,
    model_role: ModelRole,
    system: str,
    messages: list[Message],
    schema: type[T],
    tool_name: str,
    tool_description: str,
    check: Callable[[T], str | None] | None = None,
    max_tokens: int = 4000,
) -> T:
    tool = ToolSchema(name=tool_name, description=tool_description,
                      parameters=schema.model_json_schema())
    conversation = list(messages)
    last_problem = ""
    for attempt in range(2):
        reply = await llm.complete(LLMRequest(
            purpose=purpose, model_role=model_role, system=system, messages=conversation,
            tools=[tool], tool_choice=tool_name, max_tokens=max_tokens,
        ))
        value, last_problem = _validate(reply, schema, tool_name, check)
        if value is not None:
            return value
        if attempt == 1:
            break
        submitted = next((c for c in reply.tool_calls if c.name == tool_name), None)
        call = submitted or ToolCall(id="repair_0", name=tool_name, arguments={})
        conversation += [
            Message(role="assistant", content=reply.text, tool_calls=[call]),
            Message(role="tool", tool_call_id=call.id,
                    content=f"Your submission was invalid: {last_problem}. "
                            f"Call {tool_name} again with corrected arguments."),
        ]
    raise StructuredOutputError(f"{purpose}: no valid {tool_name} after repair ({last_problem})")
