"""Durable LangGraph checkpoints in Postgres, inside ForgeOps' private schema."""

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.engine import make_url

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from forgeops.config import Settings
from forgeops.engine import models

# Only ForgeOps' own state types may be loaded from a checkpoint (plus LangGraph's safe built-ins).
STATE_TYPES = (
    models.AgentId, models.Capability, models.Incident, models.AgentTask, models.SkippedAgent, models.Plan,
    models.Artifact, models.ToolCallRecord, models.Evidence, models.AgentQuestion, models.AgentError,
    models.TimelineItem, models.Recommendation, models.RCA, models.Decision, models.ActionResult,
)


def checkpoint_serde() -> JsonPlusSerializer:
    return JsonPlusSerializer(allowed_msgpack_modules=STATE_TYPES)


def psycopg_conninfo(database_url: str) -> str:
    """SQLAlchemy asyncpg URL -> libpq URL (password stays percent-encoded)."""
    return make_url(database_url).set(drivername="postgresql").render_as_string(hide_password=False)


async def open_checkpointer(settings: Settings) -> tuple[AsyncPostgresSaver, AsyncConnectionPool]:
    schema = settings.database_schema

    async def configure(conn: AsyncConnection) -> None:
        # Set per connection (not via startup options) so it also works through Supabase's pooler.
        await conn.execute(f'SET search_path TO "{schema}"')

    pool = AsyncConnectionPool(
        psycopg_conninfo(settings.database_url),
        min_size=1, max_size=10, open=False, configure=configure,
        kwargs={"autocommit": True, "prepare_threshold": None, "row_factory": dict_row},
    )
    await pool.open()
    saver = AsyncPostgresSaver(pool, serde=checkpoint_serde())
    await saver.setup()
    return saver, pool
