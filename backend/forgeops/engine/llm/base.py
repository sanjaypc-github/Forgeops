"""Provider-neutral chat + tool-calling types used by every agent."""

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

ModelRole = Literal["supervisor", "specialist", "rca"]


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class LLMRequest(BaseModel):
    purpose: str  # e.g. "plan", "specialist:database", "rca" — for logs, cost tracking and tests
    model_role: ModelRole
    system: str
    messages: list[Message]
    tools: list[ToolSchema] = Field(default_factory=list)
    tool_choice: str = "auto"  # "auto", "required", or the name of one tool to force
    max_tokens: int = 4000


class LLMReply(BaseModel):
    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


class LLM(Protocol):
    async def complete(self, request: LLMRequest) -> LLMReply: ...


class LLMError(Exception):
    """The model provider failed or returned something unusable."""


class LLMNotConfigured(LLMError):
    """No usable LLM credentials are configured."""


class StructuredOutputError(LLMError):
    """The model did not produce a valid structured answer after a repair attempt."""
