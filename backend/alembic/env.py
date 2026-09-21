import asyncio
from logging.config import fileConfig

from alembic import context

from forgeops.config import get_settings
from forgeops.db.models import Base
from forgeops.db.session import create_engine, ensure_schema

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()
SCHEMA = settings.database_schema


def _include_object(obj, name, type_, reflected, compare_to) -> bool:
    # Alembic's own version table lives in SCHEMA too; it is not part of the models.
    return not (type_ == "table" and name == "alembic_version")


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        version_table_schema=SCHEMA,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    # Every connection resolves unqualified tables in SCHEMA (never Supabase's public schema).
    engine = create_engine(settings.database_url, SCHEMA)
    await ensure_schema(engine, SCHEMA)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
