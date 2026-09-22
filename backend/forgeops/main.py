import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forgeops.api import agents, auth, chat, connections, health, investigations
from forgeops.config import Settings, get_settings
from forgeops.connectors.factory import build_registry_for_workspace
from forgeops.db.session import create_engine_and_factory
from forgeops.engine.checkpoint import open_checkpointer
from forgeops.engine.llm.openrouter import OpenRouterLLM
from forgeops.engine.runner import InvestigationRunner
from forgeops.events.bus import EventBus
from forgeops.knowledge.index import default_embedder
from forgeops.logging import configure_logging
from forgeops.security.crypto import SecretBox
from forgeops.security.rate_limit import LoginLimiter
from forgeops.services.bootstrap import ensure_admin

log = structlog.get_logger()


async def startup(app: FastAPI, settings: Settings) -> None:
    configure_logging(settings.is_production)
    engine, session_factory = create_engine_and_factory(
        settings.database_url, settings.database_schema
    )
    state = app.state
    state.settings = settings
    state.engine = engine
    state.session_factory = session_factory
    state.event_bus = EventBus(session_factory)
    state.login_limiter = LoginLimiter()
    state.secret_box = SecretBox(settings.forgeops_secret_key.get_secret_value())
    state.embedder = default_embedder()  # model downloads on first use
    state.chat_tasks = set()
    async with session_factory() as session:
        _, workspace = await ensure_admin(session, settings)

    # Engine. Factories are looked up on app.state at call time so tests can replace them.
    state.llm_factory = lambda: OpenRouterLLM.from_settings(state.settings)

    async def registry_factory(workspace_id: str):
        return await build_registry_for_workspace(
            state.session_factory, workspace_id, state.secret_box, state.settings, state.embedder)

    state.registry_factory = registry_factory
    state.checkpointer, state.checkpoint_pool = await open_checkpointer(settings)
    state.runner = InvestigationRunner(
        session_factory=session_factory, bus=state.event_bus, checkpointer=state.checkpointer,
        llm_factory=lambda: state.llm_factory(),
        registry_factory=lambda workspace_id: state.registry_factory(workspace_id),
        budgets=settings.budgets(),
    )
    recovered = await state.runner.recover_on_startup()
    log.info("forgeops.started", workspace_id=workspace.id, env=settings.forgeops_env,
             recovered_investigations=recovered)


async def shutdown(app: FastAPI) -> None:
    state = app.state
    await state.runner.shutdown()
    for task in list(state.chat_tasks):
        task.cancel()
    await asyncio.gather(*state.chat_tasks, return_exceptions=True)
    await state.checkpoint_pool.close()
    await state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await startup(app, settings)
        yield
        await shutdown(app)

    app = FastAPI(title="ForgeOps API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (health, auth, investigations, chat, connections, agents):
        app.include_router(module.router, prefix="/api")
    return app
