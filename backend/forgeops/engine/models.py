"""Contracts shared by the engine, the API and the UI event stream."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class AgentId(StrEnum):
    supervisor = "supervisor"
    code = "code"
    frontend_hosting = "frontend_hosting"
    backend_services = "backend_services"
    database = "database"
    observability = "observability"
    knowledge = "knowledge"
    rca = "rca"
    action = "action"


SPECIALISTS: tuple[AgentId, ...] = (
    AgentId.code,
    AgentId.frontend_hosting,
    AgentId.backend_services,
    AgentId.database,
    AgentId.observability,
    AgentId.knowledge,
)


class Capability(StrEnum):
    code = "code"
    hosting = "hosting"
    backend = "backend"
    content = "content"
    database = "database"
    errors = "errors"
    logs = "logs"
    metrics = "metrics"
    knowledge = "knowledge"
    write = "write"


Severity = Literal["info", "low", "medium", "high", "critical"]
ArtifactType = Literal[
    "commit", "pull_request", "diff", "deployment", "build_log", "workflow_run",
    "error_issue", "error_event", "log_lines", "metric", "query_stats", "db_advisor",
    "content_change", "config", "doc_chunk",
]
RcaCategory = Literal[
    "code_change", "config_change", "deployment", "content_change", "database",
    "dependency", "infrastructure", "traffic", "unknown",
]

EXCERPT_LIMIT = 2000


class Incident(BaseModel):
    text: str
    source: Literal["chat", "web"]
    service_hint: str | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    notes: list[str] = Field(default_factory=list)


class AgentTask(BaseModel):
    agent: AgentId
    objective: str
    hints: list[str] = Field(default_factory=list)

    @field_validator("agent")
    @classmethod
    def _specialist_only(cls, agent: AgentId) -> AgentId:
        if agent not in SPECIALISTS:
            raise ValueError(f"tasks can only be assigned to specialists, not {agent.value}")
        return agent


class SkippedAgent(BaseModel):
    agent: AgentId
    reason: str


class Plan(BaseModel):
    summary: str
    affected_service: str | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    hypotheses: list[str] = Field(default_factory=list)
    tasks: list[AgentTask] = Field(default_factory=list)
    skipped: list[SkippedAgent] = Field(default_factory=list)


class Artifact(BaseModel):
    type: ArtifactType
    ref: str
    url: str | None = None
    timestamp: datetime | None = None
    excerpt: str | None = None

    @field_validator("excerpt")
    @classmethod
    def _truncate(cls, value: str | None) -> str | None:
        if value is not None and len(value) > EXCERPT_LIMIT:
            return value[: EXCERPT_LIMIT - 14] + " …[truncated]"
        return value


class ToolCallRecord(BaseModel):
    id: str
    agent: AgentId
    tool: str
    connector_type: str
    connection_id: str
    args_summary: str
    ok: bool
    duration_ms: int
    truncated: bool
    result_excerpt: str
    error: str | None = None


class Evidence(BaseModel):
    id: str
    agent: AgentId
    capability: Capability
    connection_id: str
    connector_type: str
    finding: str
    failure_point: str | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: str | None = None
    tool_call_ids: list[str] = Field(min_length=1)


class AgentQuestion(BaseModel):
    id: str
    from_agent: AgentId
    to_agent: AgentId
    question: str
    answer: str | None = None
    status: Literal["answered", "failed", "refused"]
    reason: str | None = None


class AgentError(BaseModel):
    agent: AgentId
    message: str


class TimelineItem(BaseModel):
    ts: datetime | None = None
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    id: str
    title: str
    description: str
    action: Literal["none", "github_issue"]
    parameters: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool

    @model_validator(mode="after")
    def _writes_need_approval(self) -> "Recommendation":
        if self.action != "none" and not self.requires_approval:
            raise ValueError("recommendations that write to external systems require approval")
        return self


class RCA(BaseModel):
    summary: str
    failure_point: str
    category: RcaCategory
    confidence: float = Field(ge=0.0, le=1.0)
    timeline: list[TimelineItem] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    alternative_hypotheses: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)


class Decision(BaseModel):
    kind: Literal["approve", "reject", "investigate_more"]
    approved_recommendation_ids: list[str] = Field(default_factory=list)
    note: str | None = None
    decided_by: str
    channel: Literal["web", "chat"]


class ActionResult(BaseModel):
    recommendation_id: str
    status: Literal["done", "failed", "unavailable"]
    detail: str
    url: str | None = None
