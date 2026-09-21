from sqlalchemy import text

from forgeops.db.models import Base
from tests.conftest import TEST_SCHEMA

FORGEOPS_TABLES = sorted(t.name for t in Base.metadata.sorted_tables)


async def _tables_in(session, schema: str) -> list[str]:
    rows = await session.execute(
        text(
            "select table_name from information_schema.tables "
            "where table_schema = :schema order by table_name"
        ),
        {"schema": schema},
    )
    return list(rows.scalars())


async def test_tables_live_in_the_private_schema_not_public(session_factory):
    async with session_factory() as session:
        private = await _tables_in(session, TEST_SCHEMA)
        public = await _tables_in(session, "public")
    assert set(FORGEOPS_TABLES) <= set(private)
    assert not set(FORGEOPS_TABLES) & set(public)


async def test_connections_use_the_private_schema(session_factory):
    async with session_factory() as session:
        search_path = (await session.execute(text("show search_path"))).scalar_one()
    assert search_path == TEST_SCHEMA
