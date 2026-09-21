"""Runs investigations in the background: start, pause for approval, resume, fail loudly."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from langgraph.types import Command
from sqlalchemy import select, update

from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.capabilities.runner import ToolRunner
from forgeops.db.models import ChatMessage, Investigation
from forgeops.db.session import SessionFactory
from forgeops.engine.budgets import Budgets
from forgeops.engine.graph import RunDeps, build_graph
from forgeops.engine.llm.base import LLM, LLMNotConfigured
from forgeops.engine.models import Decision, Incident
from forgeops.events.bus import EventBus
from forgeops.events.models import EventIn, EventType

log = structlog.get_logger()
RESTART_REASON = "ForgeOps restarted during the investigation"
ACTIVE = ("queued", "running", "acting")


class InvestigationRunner:
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        bus: EventBus,
        checkpointer: Any,
        llm_factory: Callable[[], LLM],
        registry_factory: Callable[[str], Awaitable[CapabilityRegistry]],
        budgets: Budgets = Budgets(),
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._sf = session_factory
        self._bus = bus
        self._checkpointer = checkpointer
        self._llm_factory = llm_factory
        self._registry_factory = registry_factory
        self._budgets = budgets
        self._now = now
        self._tasks: dict[str, asyncio.Task] = {}

    # ----- helpers -----------------------------------------------------------------------------
    async def _load(self, investigation_id: str) -> Investigation:
        async with self._sf() as session:
            inv = await session.get(Investigation, investigation_id)
        if inv is None:
            raise LookupError(f"investigation {investigation_id} not found")
        return inv

    async def _set_status(self, investigation_id: str, status: str) -> None:
        async with self._sf() as session:
            await session.execute(update(Investigation).where(Investigation.id == investigation_id)
                                  .values(status=status, updated_at=self._now()))
            await session.commit()

    async def _user_notes(self, investigation_id: str) -> list[str]:
        async with self._sf() as session:
            rows = await session.scalars(select(ChatMessage.text).where(
                ChatMessage.investigation_id == investigation_id, ChatMessage.role == "user"
            ).order_by(ChatMessage.created_at))
            messages = list(rows)
        return messages[1:]  # the first user message is the incident itself

    @staticmethod
    def _config(investigation_id: str) -> dict:
        return {"configurable": {"thread_id": investigation_id}, "recursion_limit": 80}

    def _spawn(self, investigation_id: str, coro: Awaitable[None]) -> None:
        task = asyncio.create_task(coro, name=f"investigation:{investigation_id}")
        self._tasks[investigation_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(investigation_id, None)
                               if self._tasks.get(investigation_id) is task else None)

    # ----- the run -----------------------------------------------------------------------------
    async def _run(self, investigation_id: str, decision: Decision | None) -> None:
        inv = await self._load(investigation_id)

        async def emit(event: EventIn):
            return await self._bus.emit(inv.workspace_id, inv.id, event)

        registry: CapabilityRegistry | None = None
        try:
            llm = self._llm_factory()
            registry = await self._registry_factory(inv.workspace_id)

            async def notes() -> list[str]:
                return await self._user_notes(inv.id)

            deps = RunDeps(llm=llm, registry=registry, tool_runner=ToolRunner(registry, emit, self._budgets),
                           emit=emit, budgets=self._budgets, now=self._now, service_map="", notes=notes)
            graph = build_graph(deps, self._checkpointer)
            config = self._config(inv.id)
            async with asyncio.timeout(self._budgets.run_seconds):
                if decision is None:
                    await graph.ainvoke(self._initial_state(inv), config)
                else:
                    await graph.ainvoke(Command(resume=decision.model_dump(mode="json")), config)
            snapshot = await graph.aget_state(config)
            if snapshot.next:
                status = "awaiting_approval"
            else:
                final = snapshot.values.get("decision")
                status = "rejected" if final is not None and final.kind == "reject" else "completed"
            await self._set_status(inv.id, status)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - every failure is surfaced to the user
            if isinstance(exc, LLMNotConfigured):
                reason = str(exc)
            elif isinstance(exc, TimeoutError):
                reason = f"The investigation exceeded its {int(self._budgets.run_seconds)} s time budget"
            else:
                reason = f"{type(exc).__name__}: {exc}"
            log.error("investigation.failed", investigation_id=inv.id, reason=reason)
            await self._set_status(inv.id, "failed")
            await emit(EventIn(type=EventType.investigation_failed, data={"reason": reason}))
        finally:
            if registry is not None:
                await registry.aclose()

    @staticmethod
    def _initial_state(inv: Investigation) -> dict:
        return {
            "workspace_id": inv.workspace_id, "investigation_id": inv.id,
            "incident": Incident(text=inv.description, source="chat" if inv.source == "chat" else "web",
                                 window_start=inv.window_start, window_end=inv.window_end),
            "capabilities": {}, "plan": None, "pending_tasks": [], "review_rounds": 0,
            "followup_rounds": 0, "rca": None, "decision": None, "report_markdown": None,
        }

    # ----- public ------------------------------------------------------------------------------
    async def start(self, investigation_id: str) -> None:
        await self._set_status(investigation_id, "running")
        self._spawn(investigation_id, self._run(investigation_id, None))

    async def resume(self, investigation_id: str, decision: Decision) -> None:
        await self._set_status(investigation_id, "acting" if decision.kind == "approve" else "running")
        self._spawn(investigation_id, self._run(investigation_id, decision))

    async def snapshot(self, investigation_id: str) -> dict | None:
        saved = await self._checkpointer.aget_tuple(self._config(investigation_id))
        return dict(saved.checkpoint.get("channel_values", {})) if saved else None

    async def wait(self, investigation_id: str) -> None:
        task = self._tasks.get(investigation_id)
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)

    async def recover_on_startup(self) -> int:
        async with self._sf() as session:
            rows = list(await session.scalars(select(Investigation).where(Investigation.status.in_(ACTIVE))))
            for inv in rows:
                inv.status = "failed"
            await session.commit()
        for inv in rows:
            await self._bus.emit(inv.workspace_id, inv.id, EventIn(
                type=EventType.investigation_failed, data={"reason": RESTART_REASON}))
        return len(rows)

    async def shutdown(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
