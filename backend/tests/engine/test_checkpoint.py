from uuid import uuid4

from langgraph.types import Command
from sqlalchemy import text

from forgeops.engine.checkpoint import open_checkpointer, psycopg_conninfo
from forgeops.engine.graph import build_graph
from tests.conftest import TEST_SCHEMA
from tests.engine.graph_fixtures import initial_state, make_deps, script


def test_conninfo_drops_the_asyncpg_driver_and_keeps_encoding():
    info = psycopg_conninfo("postgresql+asyncpg://u:p%40x@h:5432/db")
    assert info == "postgresql://u:p%40x@h:5432/db"


async def test_approval_pause_survives_a_restart(settings, session_factory):
    thread = f"inv_{uuid4().hex}"
    cfg = {"configurable": {"thread_id": thread}}

    deps, events, _, _ = await make_deps(script())
    saver, pool = await open_checkpointer(settings)
    try:
        await build_graph(deps, saver).ainvoke(initial_state(thread), cfg)
    finally:
        await pool.close()

    # "restart": brand-new pool, saver, deps and graph
    deps2, events2, _, _ = await make_deps({})
    saver2, pool2 = await open_checkpointer(settings)
    try:
        graph2 = build_graph(deps2, saver2)
        assert (await graph2.aget_state(cfg)).next == ("approval",)
        await graph2.ainvoke(Command(resume={"kind": "reject", "decided_by": "u", "channel": "web"}), cfg)
        assert events2[-1].type == "investigation_completed"
    finally:
        await pool2.close()

    async with session_factory() as session:
        schemas = (await session.execute(text(
            "select distinct table_schema from information_schema.tables where table_name = 'checkpoints'"
        ))).scalars().all()
    assert TEST_SCHEMA in schemas and "public" not in schemas
