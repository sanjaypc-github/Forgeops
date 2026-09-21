from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

SessionFactory = async_sessionmaker[AsyncSession]


def create_engine(url: str, schema: str, **kwargs) -> AsyncEngine:
    """Engine whose connections resolve every table in `schema`.

    ForgeOps keeps its tables out of `public` because Supabase exposes `public`
    through its Data API.
    """
    return create_async_engine(
        url,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": schema}},
        **kwargs,
    )


def create_engine_and_factory(url: str, schema: str) -> tuple[AsyncEngine, SessionFactory]:
    engine = create_engine(url, schema)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def ensure_schema(engine: AsyncEngine, schema: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
