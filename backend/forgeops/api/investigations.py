from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from forgeops.api.deps import CurrentUser, current_user, require_csrf
from forgeops.db.models import Investigation
from forgeops.events.bus import EventBus
from forgeops.events.models import EventIn, EventType

router = APIRouter(prefix="/investigations", tags=["investigations"])


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


async def _get_owned(request: Request, user: CurrentUser, investigation_id: str) -> Investigation:
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


@router.post("", status_code=status.HTTP_201_CREATED, response_model=InvestigationOut)
async def create_investigation(
    body: InvestigationCreate, request: Request, user: CurrentUser = Depends(require_csrf)
) -> Investigation:
    async with request.app.state.session_factory() as session:
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
    bus: EventBus = request.app.state.event_bus
    await bus.emit(
        user.workspace_id,
        inv.id,
        EventIn(type=EventType.investigation_started, data={"description": inv.description}),
    )
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


@router.get("/{investigation_id}", response_model=InvestigationOut)
async def get_investigation(
    investigation_id: str, request: Request, user: CurrentUser = Depends(current_user)
) -> Investigation:
    return await _get_owned(request, user, investigation_id)


@router.get("/{investigation_id}/events")
async def stream_events(
    investigation_id: str,
    request: Request,
    after: int = 0,
    user: CurrentUser = Depends(current_user),
) -> EventSourceResponse:
    inv = await _get_owned(request, user, investigation_id)
    last_event_id = request.headers.get("last-event-id", "")
    after_seq = int(last_event_id) if last_event_id.isdigit() else after
    bus: EventBus = request.app.state.event_bus

    async def messages():
        async for event in bus.stream(inv.id, after_seq):
            yield {"id": str(event.seq), "data": event.model_dump_json()}

    return EventSourceResponse(messages(), ping=15)
