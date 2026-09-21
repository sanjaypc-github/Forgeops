from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EventType(StrEnum):
    investigation_started = "investigation_started"
    supervisor_started = "supervisor_started"
    plan_created = "plan_created"
    agent_skipped = "agent_skipped"
    agent_started = "agent_started"
    tool_called = "tool_called"
    tool_completed = "tool_completed"
    evidence_added = "evidence_added"
    agent_failed = "agent_failed"
    agent_completed = "agent_completed"
    review_completed = "review_completed"
    rca_started = "rca_started"
    rca_completed = "rca_completed"
    approval_requested = "approval_requested"
    approval_granted = "approval_granted"
    approval_rejected = "approval_rejected"
    action_started = "action_started"
    action_completed = "action_completed"
    report_ready = "report_ready"
    investigation_completed = "investigation_completed"
    investigation_failed = "investigation_failed"


TERMINAL_EVENTS = frozenset({EventType.investigation_completed, EventType.investigation_failed})


class EventIn(BaseModel):
    type: EventType
    agent: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class EventOut(BaseModel):
    seq: int
    investigation_id: str
    type: EventType
    agent: str | None
    ts: datetime
    data: dict[str, Any]
