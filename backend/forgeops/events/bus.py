"""Persisted, ordered investigation events with in-process live fan-out.

Single-process by design for the MVP: subscribers live in this process's memory.
"""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import exists, func, select

from forgeops.db.models import Event
from forgeops.db.session import SessionFactory
from forgeops.events.models import TERMINAL_EVENTS, EventIn, EventOut


def _to_out(row: Event) -> EventOut:
    return EventOut(
        seq=row.seq,
        investigation_id=row.investigation_id,
        type=row.type,
        agent=row.agent,
        ts=row.ts,
        data=row.data,
    )


class EventBus:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._subscribers: dict[str, set[asyncio.Queue[EventOut]]] = defaultdict(set)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def emit(self, workspace_id: str, investigation_id: str, event: EventIn) -> EventOut:
        async with self._locks[investigation_id]:
            async with self._session_factory() as session:
                last = await session.scalar(
                    select(func.max(Event.seq)).where(Event.investigation_id == investigation_id)
                )
                row = Event(
                    investigation_id=investigation_id,
                    workspace_id=workspace_id,
                    seq=(last or 0) + 1,
                    type=event.type.value,
                    agent=event.agent,
                    data=event.data,
                )
                session.add(row)
                await session.commit()
                out = _to_out(row)
        for queue in list(self._subscribers[investigation_id]):
            queue.put_nowait(out)
        return out

    async def history(self, investigation_id: str, after_seq: int = 0) -> list[EventOut]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(Event)
                .where(Event.investigation_id == investigation_id, Event.seq > after_seq)
                .order_by(Event.seq)
            )
            return [_to_out(row) for row in rows]

    async def is_terminal(self, investigation_id: str) -> bool:
        async with self._session_factory() as session:
            return bool(
                await session.scalar(
                    select(
                        exists().where(
                            Event.investigation_id == investigation_id,
                            Event.type.in_([t.value for t in TERMINAL_EVENTS]),
                        )
                    )
                )
            )

    @asynccontextmanager
    async def subscribe(self, investigation_id: str) -> AsyncIterator[asyncio.Queue[EventOut]]:
        queue: asyncio.Queue[EventOut] = asyncio.Queue()
        self._subscribers[investigation_id].add(queue)
        try:
            yield queue
        finally:
            self._subscribers[investigation_id].discard(queue)
            if not self._subscribers[investigation_id]:
                self._subscribers.pop(investigation_id, None)

    async def stream(self, investigation_id: str, after_seq: int = 0) -> AsyncIterator[EventOut]:
        # Subscribe before reading history so nothing emitted in between is lost;
        # duplicates are dropped by sequence number.
        async with self.subscribe(investigation_id) as queue:
            last = after_seq
            for event in await self.history(investigation_id, after_seq):
                yield event
                last = event.seq
                if event.type in TERMINAL_EVENTS:
                    return
            if await self.is_terminal(investigation_id):
                return
            while True:
                event = await queue.get()
                if event.seq <= last:
                    continue
                yield event
                last = event.seq
                if event.type in TERMINAL_EVENTS:
                    return
