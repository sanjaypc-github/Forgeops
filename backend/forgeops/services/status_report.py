"""Build the answer to a platform question from ForgeOps' own database.

No model call, no connector call: the connections table and the catalog already hold the answer.
"""

from sqlalchemy import select

from forgeops.capabilities.routing import agent_for_capability
from forgeops.connectors.definitions import CATALOG
from forgeops.db.models import Connection
from forgeops.engine.models import SPECIALISTS, AgentId, Capability
from forgeops.engine.roster import PROFILES
from forgeops.engine.triage import ConnectionStatus, DeskStatus, render_status

# Config keys that say what a connection points at, in the order we prefer to show them.
_TARGET_KEYS = ("repository", "project_ref", "account_id", "vault_path", "workspace")


def _capabilities(connection_type: str) -> set[Capability]:
    definition = CATALOG.get(connection_type)
    if definition is None:
        return set()
    if definition.type == "knowledge":
        return {Capability.knowledge}
    return {m.capability for m in definition.tools}


def _abilities(connection_type: str) -> int:
    definition = CATALOG.get(connection_type)
    if definition is None:
        return 0
    return len([m for m in definition.tools if m.permission == "read"]) or 1


async def status_answer(session_factory, workspace_id: str) -> str:
    async with session_factory() as session:
        rows = list(await session.scalars(
            select(Connection).where(Connection.workspace_id == workspace_id)
            .order_by(Connection.created_at)))

    connections: list[ConnectionStatus] = []
    by_desk: dict[AgentId, list[str]] = {agent: [] for agent in AgentId}
    abilities: dict[AgentId, int] = {agent: 0 for agent in AgentId}

    for row in rows:
        definition = CATALOG.get(row.type)
        target = next((str(row.config[k]) for k in _TARGET_KEYS if row.config.get(k)), "")
        ok = row.status == "connected"
        connections.append(ConnectionStatus(
            name=row.name, type_title=definition.display_name if definition else row.type,
            ok=ok, detail=("" if ok else (row.last_error or "not connected")), target=target))
        if not ok:
            continue
        for capability in _capabilities(row.type):
            desk = agent_for_capability(capability)
            if row.name not in by_desk[desk]:
                by_desk[desk].append(row.name)
            abilities[desk] = max(abilities[desk], _abilities(row.type))

    desks = [
        DeskStatus(title=PROFILES[agent].title, connected=bool(by_desk[agent]),
                   abilities=abilities[agent], connectors=by_desk[agent])
        for agent in SPECIALISTS
    ]
    return render_status(connections, desks)
