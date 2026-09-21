from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from forgeops.api.deps import CurrentUser, current_user, require_csrf
from forgeops.db.models import AuditLog, ChatMessage, Investigation
from forgeops.engine.models import Decision
from forgeops.events.bus import EventBus
from forgeops.events.models import EventIn, EventType

router = APIRouter(prefix="/investigations", tags=["investigations"])

DETAIL_KEYS = ("plan", "evidence", "rca", "questions", "decision", "action_results", "errors", "warnings")


class InvestigationCreate(BaseModel):
    description: str = Field(min_length=3, max_length=4000)
    service_id: str | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None


class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str
    status: str
    source: str
    service_id: str | None
    window_start: datetime | None
    window_end: datetime | None
    created_at: datetime


class InvestigationDetailOut(InvestigationOut):
    details: dict[str, Any] | None = None


class DecisionIn(BaseModel):
    kind: Literal["approve", "reject", "investigate_more"]
    approved_recommendation_ids: list[str] = Field(default_factory=list)
    note: str | None = Field(default=None, max_length=2000)


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    text: str
    created_at: datetime


async def get_owned_investigation(request: Request, user: CurrentUser, investigation_id: str) -> Investigation:
    async with request.app.state.session_factory() as session:
        inv = await session.scalar(
            select(Investigation).where(
                Investigation.id == investigation_id,
                Investigation.workspace_id == user.workspace_id,
            )
        )
    if inv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Investigation not found")
    return inv


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


@router.post("", status_code=status.HTTP_201_CREATED, response_model=InvestigationOut)
async def create_investigation(
    body: InvestigationCreate, request: Request, user: CurrentUser = Depends(require_csrf)
) -> Investigation:
    state = request.app.state
    async with state.session_factory() as session:
        inv = Investigation(
            workspace_id=user.workspace_id,
            description=body.description.strip(),
            service_id=body.service_id,
            source="web",
            status="queued",
            created_by=user.user_id,
            window_start=body.window_start,
            window_end=body.window_end,
        )
        session.add(inv)
        await session.commit()
    bus: EventBus = state.event_bus
    await bus.emit(
        user.workspace_id,
        inv.id,
        EventIn(type=EventType.investigation_started, data={"description": inv.description}),
    )
    await state.runner.start(inv.id)
    inv.status = "running"
    return inv


@router.get("", response_model=list[InvestigationOut])
async def list_investigations(
    request: Request, user: CurrentUser = Depends(current_user)
) -> list[Investigation]:
    async with request.app.state.session_factory() as session:
        rows = await session.scalars(
            select(Investigation)
            .where(Investigation.workspace_id == user.workspace_id)
            .order_by(Investigation.created_at.desc())
            .limit(50)
        )
        return list(rows)


@router.get("/{investigation_id}", response_model=InvestigationDetailOut)
async def get_investigation(
    investigation_id: str, request: Request, user: CurrentUser = Depends(current_user)
) -> InvestigationDetailOut:
    inv = await get_owned_investigation(request, user, investigation_id)
    snapshot = await request.app.state.runner.snapshot(inv.id)
    details = {k: _jsonable(snapshot.get(k)) for k in DETAIL_KEYS} if snapshot else None
    return InvestigationDetailOut(**InvestigationOut.model_validate(inv).model_dump(), details=details)


@router.post("/{investigation_id}/decision")
async def decide(
    investigation_id: str, body: DecisionIn, request: Request, user: CurrentUser = Depends(require_csrf)
) -> JSONResponse:
    state = request.app.state
    inv = await get_owned_investigation(request, user, investigation_id)
    if inv.status != "awaiting_approval":
        raise HTTPException(status.HTTP_409_CONFLICT, "This investigation is not waiting for a decision")
    snapshot = await state.runner.snapshot(inv.id) or {}
    rca = snapshot.get("rca")
    known = {r.id for r in rca.recommendations} if rca else set()
    unknown = sorted(set(body.approved_recommendation_ids) - known)
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown recommendations: {', '.join(unknown)}")

    decision = Decision(kind=body.kind, approved_recommendation_ids=body.approved_recommendation_ids,
                        note=body.note, decided_by=user.user_id, channel="web")
    async with state.session_factory() as session:
        session.add(AuditLog(workspace_id=user.workspace_id, actor=user.email, channel="web",
                             action=f"investigation.{body.kind}", target=inv.id,
                             detail={"approved": body.approved_recommendation_ids, "note": body.note}))
        await session.commit()
    await state.runner.resume(inv.id, decision)
    return JSONResponse({"investigation_id": inv.id, "status": "accepted"}, status_code=202)


@router.get("/{investigation_id}/report")
async def report(investigation_id: str, request: Request, user: CurrentUser = Depends(current_user)):
    inv = await get_owned_investigation(request, user, investigation_id)
    snapshot = await request.app.state.runner.snapshot(inv.id) or {}
    markdown = snapshot.get("report_markdown")
    if not markdown:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The report is not ready yet")
    return PlainTextResponse(markdown, media_type="text/markdown; charset=utf-8")


@router.get("/{investigation_id}/chat", response_model=list[ChatMessageOut])
async def chat_history(
    investigation_id: str, request: Request, user: CurrentUser = Depends(current_user)
) -> list[ChatMessage]:
    inv = await get_owned_investigation(request, user, investigation_id)
    async with request.app.state.session_factory() as session:
        rows = await session.scalars(
            select(ChatMessage).where(ChatMessage.investigation_id == inv.id).order_by(ChatMessage.created_at)
        )
        return list(rows)


@router.get("/{investigation_id}/events")
async def stream_events(
    investigation_id: str,
    request: Request,
    after: int = 0,
    user: CurrentUser = Depends(current_user),
) -> EventSourceResponse:
    inv = await get_owned_investigation(request, user, investigation_id)
    last_event_id = request.headers.get("last-event-id", "")
    after_seq = int(last_event_id) if last_event_id.isdigit() else after
    bus: EventBus = request.app.state.event_bus

    async def messages():
        async for event in bus.stream(inv.id, after_seq):
            yield {"id": str(event.seq), "data": event.model_dump_json()}

    return EventSourceResponse(messages(), ping=15)
