"""The desks: who each agent is and which connected tools power it (drives the idle office)."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select

from forgeops.api.deps import CurrentUser, current_user
from forgeops.capabilities.routing import agent_for_capability
from forgeops.connectors.definitions import CATALOG
from forgeops.db.models import Connection
from forgeops.engine.models import SPECIALISTS, AgentId, Capability
from forgeops.engine.roster import PROFILES

router = APIRouter(tags=["agents"])


class DeskConnector(BaseModel):
    id: str
    type: str
    name: str


class DeskOut(BaseModel):
    id: AgentId
    title: str
    area: str
    specialist: bool
    connected: bool
    capabilities: list[Capability]
    connectors: list[DeskConnector]


def _capabilities(connection_type: str) -> set[Capability]:
    definition = CATALOG.get(connection_type)
    if definition is None:
        return set()
    if definition.type == "knowledge":
        return {Capability.knowledge}
    return {m.capability for m in definition.tools}


@router.get("/agents", response_model=list[DeskOut])
async def list_agents(request: Request, user: CurrentUser = Depends(current_user)) -> list[DeskOut]:
    async with request.app.state.session_factory() as session:
        rows = list(await session.scalars(
            select(Connection).where(Connection.workspace_id == user.workspace_id,
                                     Connection.status == "connected").order_by(Connection.created_at)))
    caps: dict[AgentId, set[Capability]] = {a: set() for a in AgentId}
    connectors: dict[AgentId, list[DeskConnector]] = {a: [] for a in AgentId}
    for row in rows:
        for capability in _capabilities(row.type):
            agent = agent_for_capability(capability)
            caps[agent].add(capability)
            if all(c.id != row.id for c in connectors[agent]):
                connectors[agent].append(DeskConnector(id=row.id, type=row.type, name=row.name))
    order = list(Capability)
    return [
        DeskOut(id=agent, title=PROFILES[agent].title, area=PROFILES[agent].area,
                specialist=agent in SPECIALISTS, connected=bool(caps[agent]),
                capabilities=sorted(caps[agent], key=order.index), connectors=connectors[agent])
        for agent in AgentId
    ]
