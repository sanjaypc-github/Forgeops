from typing import Any, Literal, Protocol

from pydantic import BaseModel, model_validator

from forgeops.engine.models import Capability


class ToolSpec(BaseModel):
    name: str  # ForgeOps name, e.g. "supabase.get_logs"
    description: str
    capability: Capability
    permission: Literal["read", "write"]
    input_schema: dict[str, Any]
    connection_id: str
    connector_type: str

    @model_validator(mode="after")
    def _write_iff_write_capability(self) -> "ToolSpec":
        if (self.permission == "write") != (self.capability == Capability.write):
            raise ValueError("write permission must match the 'write' capability")
        return self


class ToolResult(BaseModel):
    ok: bool
    content: str = ""
    data: Any = None
    error: str | None = None
    truncated: bool = False
    duration_ms: int = 0


class HealthStatus(BaseModel):
    ok: bool
    detail: str


class ToolTransientError(Exception):
    """A retryable connector failure (timeout, rate limit, 5xx)."""


class Connector(Protocol):
    connection_id: str
    connector_type: str

    async def health_check(self) -> HealthStatus: ...

    async def list_tools(self) -> list[ToolSpec]: ...

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult: ...

    async def aclose(self) -> None: ...
