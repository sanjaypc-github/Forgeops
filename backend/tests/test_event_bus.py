import asyncio

from sqlalchemy import select

from forgeops.db.models import Investigation, Workspace
from forgeops.events.models import EventIn, EventType


async def _workspace_id(session_factory) -> str:
    async with session_factory() as session:
        return (await session.scalars(select(Workspace))).one().id


async def _investigation(session_factory, workspace_id: str) -> str:
    async with session_factory() as session:
        inv = Investigation(workspace_id=workspace_id, description="checkout slow")
        session.add(inv)
        await session.commit()
        return inv.id


async def test_emit_assigns_increasing_seq(app, session_factory):
    bus = app.state.event_bus
    ws = await _workspace_id(session_factory)
    inv = await _investigation(session_factory, ws)
    a = await bus.emit(ws, inv, EventIn(type=EventType.investigation_started))
    b = await bus.emit(ws, inv, EventIn(type=EventType.agent_started, agent="code"))
    assert (a.seq, b.seq) == (1, 2)
    assert b.agent == "code"


async def test_concurrent_emits_get_unique_seq(app, session_factory):
    bus = app.state.event_bus
    ws = await _workspace_id(session_factory)
    inv = await _investigation(session_factory, ws)
    results = await asyncio.gather(
        *(bus.emit(ws, inv, EventIn(type=EventType.tool_called, data={"i": i})) for i in range(10))
    )
    assert sorted(e.seq for e in results) == list(range(1, 11))


async def test_history_after_seq(app, session_factory):
    bus = app.state.event_bus
    ws = await _workspace_id(session_factory)
    inv = await _investigation(session_factory, ws)
    for _ in range(3):
        await bus.emit(ws, inv, EventIn(type=EventType.tool_called))
    assert [e.seq for e in await bus.history(inv, after_seq=1)] == [2, 3]


async def test_stream_replays_then_goes_live_then_stops_at_terminal(app, session_factory):
    bus = app.state.event_bus
    ws = await _workspace_id(session_factory)
    inv = await _investigation(session_factory, ws)
    await bus.emit(ws, inv, EventIn(type=EventType.investigation_started))

    received: list[str] = []

    async def consume():
        async for event in bus.stream(inv, after_seq=0):
            received.append(event.type)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await bus.emit(ws, inv, EventIn(type=EventType.agent_started, agent="code"))
    await bus.emit(ws, inv, EventIn(type=EventType.investigation_completed))
    await asyncio.wait_for(task, timeout=2)
    assert received == ["investigation_started", "agent_started", "investigation_completed"]


async def test_stream_of_finished_investigation_ends_immediately(app, session_factory):
    bus = app.state.event_bus
    ws = await _workspace_id(session_factory)
    inv = await _investigation(session_factory, ws)
    await bus.emit(ws, inv, EventIn(type=EventType.investigation_failed))

    async def drain(after: int) -> list[int]:
        return [e.seq async for e in bus.stream(inv, after_seq=after)]

    assert await asyncio.wait_for(drain(0), timeout=2) == [1]
    assert await asyncio.wait_for(drain(1), timeout=2) == []
