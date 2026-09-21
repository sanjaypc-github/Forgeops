"""The chat bar: start an investigation, add notes while it runs, ask follow-ups afterwards."""

import asyncio

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from forgeops.api.deps import CurrentUser, require_csrf
from forgeops.api.investigations import get_owned_investigation
from forgeops.db.models import ChatMessage, Investigation
from forgeops.engine.models import AgentId
from forgeops.engine.supervisor import answer_followup
from forgeops.events.models import EventIn, EventType

router = APIRouter(tags=["chat"])
log = structlog.get_logger()

RUNNING = {"queued", "running", "acting"}
ANSWERABLE = {"awaiting_approval", "completed", "rejected"}


class ChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    investigation_id: str | None = None


async def _store_and_emit(request: Request, inv: Investigation, role: str, text: str) -> None:
    state = request.app.state
    async with state.session_factory() as session:
        session.add(ChatMessage(workspace_id=inv.workspace_id, investigation_id=inv.id, role=role, text=text))
        await session.commit()
    await state.event_bus.emit(inv.workspace_id, inv.id, EventIn(
        type=EventType.chat_message, agent=AgentId.supervisor.value if role == "supervisor" else None,
        data={"role": role, "text": text}))


async def _answer(request: Request, inv: Investigation, question: str) -> None:
    state = request.app.state
    try:
        snapshot = await state.runner.snapshot(inv.id) or {}
        text = await answer_followup(state.llm_factory(), snapshot["incident"], snapshot.get("rca"),
                                     snapshot.get("evidence", []), question)
        text = text or "I could not produce an answer from the evidence."
    except Exception as exc:  # noqa: BLE001 - the user sees why there is no answer
        log.error("chat.followup_failed", investigation_id=inv.id, error=str(exc))
        text = f"I could not answer that: {exc}"
    await _store_and_emit(request, inv, "supervisor", text)


@router.post("/chat")
async def chat(body: ChatIn, request: Request, user: CurrentUser = Depends(require_csrf)) -> JSONResponse:
    state = request.app.state
    text = body.text.strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Message is empty")

    if body.investigation_id is None:
        async with state.session_factory() as session:
            inv = Investigation(workspace_id=user.workspace_id, description=text, source="chat",
                                status="queued", created_by=user.user_id)
            session.add(inv)
            await session.commit()
        await state.event_bus.emit(inv.workspace_id, inv.id, EventIn(
            type=EventType.investigation_started, data={"description": text}))
        await _store_and_emit(request, inv, "user", text)
        await state.runner.start(inv.id)
        return JSONResponse({"investigation_id": inv.id, "status": "running"}, status_code=201)

    inv = await get_owned_investigation(request, user, body.investigation_id)
    if inv.status == "failed":
        raise HTTPException(status.HTTP_409_CONFLICT, "This investigation failed; start a new one")
    await _store_and_emit(request, inv, "user", text)
    if inv.status in RUNNING:
        return JSONResponse({"investigation_id": inv.id, "status": "noted"}, status_code=202)
    task = asyncio.create_task(_answer(request, inv, text))
    state.chat_tasks.add(task)
    task.add_done_callback(state.chat_tasks.discard)
    return JSONResponse({"investigation_id": inv.id, "status": "answering"}, status_code=202)
