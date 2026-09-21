from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select

from forgeops.api.deps import CurrentUser, current_user, require_csrf
from forgeops.connectors.definitions import CATALOG, ConfigField
from forgeops.connectors.factory import build_connector
from forgeops.connectors.knowledge import resolve_vault_path
from forgeops.db.models import AuditLog, Connection
from forgeops.engine.models import AgentId

router = APIRouter(tags=["connections"])


class CatalogEntry(BaseModel):
    type: str
    display_name: str
    description: str
    agents: list[AgentId]
    status: str
    config_fields: list[ConfigField]
    docs_url: str | None


class ConnectionCreate(BaseModel):
    type: str
    name: str = Field(min_length=1, max_length=120)
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(default_factory=dict)


class ConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    name: str
    config: dict[str, Any]
    status: str
    last_error: str | None
    created_at: datetime


@router.get("/connectors/catalog", response_model=list[CatalogEntry])
async def catalog(user: CurrentUser = Depends(current_user)) -> list[CatalogEntry]:
    return [CatalogEntry(**d.model_dump(include=set(CatalogEntry.model_fields))) for d in CATALOG.values()]


@router.get("/connections", response_model=list[ConnectionOut])
async def list_connections(request: Request, user: CurrentUser = Depends(current_user)) -> list[Connection]:
    async with request.app.state.session_factory() as session:
        rows = await session.scalars(
            select(Connection).where(Connection.workspace_id == user.workspace_id).order_by(Connection.created_at)
        )
        return list(rows)


def _validate(body: ConnectionCreate, allowed_roots: list[str]) -> None:
    definition = CATALOG.get(body.type)
    if definition is None or definition.status != "available":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Connector {body.type!r} is not available")
    missing = [
        f.label for f in definition.config_fields
        if f.required and not str((body.secrets if f.secret else body.config).get(f.key, "")).strip()
    ]
    if missing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Missing required fields: {', '.join(missing)}")
    if definition.type == "knowledge":
        try:
            resolve_vault_path(str(body.config["vault_path"]), allowed_roots)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.post("/connections", status_code=status.HTTP_201_CREATED, response_model=ConnectionOut)
async def create_connection(
    body: ConnectionCreate, request: Request, user: CurrentUser = Depends(require_csrf)
) -> Connection:
    state = request.app.state
    _validate(body, state.settings.knowledge_vault_roots)
    row = Connection(
        workspace_id=user.workspace_id, type=body.type, name=body.name.strip(), config=body.config,
        secret_encrypted=state.secret_box.encrypt_json(body.secrets) if body.secrets else None,
    )
    connector = build_connector(row, state.secret_box, state.settings, state.embedder)
    try:
        health = await connector.health_check()
    finally:
        await connector.aclose()
    row.status = "connected" if health.ok else "error"
    row.last_error = None if health.ok else health.detail

    async with state.session_factory() as session:
        session.add(row)
        await session.flush()
        session.add(AuditLog(workspace_id=user.workspace_id, actor=user.email, channel="web",
                             action="connection.create", target=row.id,
                             detail={"type": row.type, "status": row.status}))
        await session.commit()
    return row


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str, request: Request, user: CurrentUser = Depends(require_csrf)
) -> Response:
    async with request.app.state.session_factory() as session:
        result = await session.execute(
            delete(Connection).where(Connection.id == connection_id,
                                     Connection.workspace_id == user.workspace_id)
        )
        if result.rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
        session.add(AuditLog(workspace_id=user.workspace_id, actor=user.email, channel="web",
                             action="connection.delete", target=connection_id))
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
