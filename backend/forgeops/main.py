from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from forgeops.api import auth, connections, health, investigations
from forgeops.config import Settings, get_settings
from forgeops.db.session import create_engine_and_factory
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
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.event_bus = EventBus(session_factory)
    app.state.login_limiter = LoginLimiter()
    app.state.secret_box = SecretBox(settings.forgeops_secret_key.get_secret_value())
    app.state.embedder = default_embedder()  # model downloads on first use
    async with session_factory() as session:
        _, workspace = await ensure_admin(session, settings)
    log.info("forgeops.started", workspace_id=workspace.id, env=settings.forgeops_env)


async def shutdown(app: FastAPI) -> None:
    await app.state.engine.dispose()


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
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(investigations.router, prefix="/api")
    app.include_router(connections.router, prefix="/api")
    return app
