"""List what a connected MCP server really offers.

    uv run python -m forgeops.devtools.mcp_tools                 # every connection
    uv run python -m forgeops.devtools.mcp_tools con_abc123      # one connection

ForgeOps never guesses a third-party tool name: upstream servers rename tools between versions (the
GitHub server consolidated its names, Supabase renamed `get_logs` to `query_logs`). Use this against
a live account, then pin the names in `connectors/definitions.py` and `tests/connectors/test_catalog.py`
with the date they were verified.
"""

import argparse
import asyncio
import sys

from sqlalchemy import select

from forgeops.config import get_settings
from forgeops.connectors.definitions import CATALOG
from forgeops.connectors.factory import build_connector
from forgeops.db.models import Connection
from forgeops.db.session import create_engine_and_factory
from forgeops.knowledge.index import default_embedder
from forgeops.security.crypto import SecretBox


async def run(connection_id: str | None) -> int:
    settings = get_settings()
    _engine, session_factory = create_engine_and_factory(settings.database_url, settings.database_schema)
    secret_box = SecretBox(settings.forgeops_secret_key.get_secret_value())

    async with session_factory() as session:
        query = select(Connection).order_by(Connection.created_at)
        if connection_id:
            query = query.where(Connection.id == connection_id)
        rows = list(await session.scalars(query))

    if not rows:
        print("No connections found. Connect a tool on the Connectors page first.")
        return 1

    embedder = default_embedder()
    for row in rows:
        definition = CATALOG.get(row.type)
        print(f"\n=== {row.name}  ({row.type}, {row.id}, status={row.status}) ===")
        if definition is None:
            print("  unknown connector type")
            continue
        try:
            connector = build_connector(row, secret_box, settings, embedder, session_factory)
        except Exception as exc:  # noqa: BLE001 - this is a diagnostic tool
            print(f"  could not build: {type(exc).__name__}: {exc}")
            continue

        allowlisted = {m.upstream for m in definition.tools}
        try:
            offered = await connector._offered() if hasattr(connector, "_offered") else {}
            if offered:
                print(f"  server offers {len(offered)} tools:")
                for name in sorted(offered):
                    mark = "pinned  " if name in allowlisted else "NEW     "
                    description = (getattr(offered[name], "description", "") or "").split("\n")[0]
                    print(f"    {mark}{name:40s} {description[:70]}")
                missing = sorted(allowlisted - set(offered))
                if missing:
                    print("  allowlisted but NOT offered (fix these in definitions.py):")
                    for name in missing:
                        print(f"    MISSING {name}")
            else:
                specs = await connector.list_tools()
                print(f"  {len(specs)} tools available to agents:")
                for spec in specs:
                    print(f"    {spec.name:40s} [{spec.capability.value}/{spec.permission}]")
            health = await connector.health_check()
            print(f"  health: {'ok' if health.ok else 'FAILED'} — {health.detail}")
        except Exception as exc:  # noqa: BLE001
            print(f"  failed to list tools: {type(exc).__name__}: {exc}")
        finally:
            await connector.aclose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="List the tools a connected MCP server offers")
    parser.add_argument("connection_id", nargs="?", help="only this connection (default: all)")
    args = parser.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    raise SystemExit(asyncio.run(run(args.connection_id)))


if __name__ == "__main__":
    main()
