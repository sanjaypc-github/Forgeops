import re
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select

from forgeops.api.deps import CurrentUser, current_user, require_csrf
from forgeops.capabilities.routing import agent_for_capability
from forgeops.connectors.definitions import CATALOG, ConfigField
from forgeops.connectors.factory import build_connector
from forgeops.connectors.knowledge import resolve_vault_path
from forgeops.db.models import AuditLog, Connection
from forgeops.engine.models import AgentId, Capability

router = APIRouter(tags=["connections"])


class Ability(BaseModel):
    name: str
    description: str
    capability: Capability
    desk: AgentId
    permission: Literal["read", "write"]


class CatalogEntry(BaseModel):
    type: str
    display_name: str
    description: str
    agents: list[AgentId]
    status: str
    config_fields: list[ConfigField]
    docs_url: str | None
    setup_steps: list[str]
    supports_writes: bool
    abilities: list[Ability]


class TestResult(BaseModel):
    ok: bool
    detail: str


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


class ConnectionCreated(ConnectionOut):
    detail: str  # the health check result, e.g. "15 read tools available"


@router.get("/connectors/catalog", response_model=list[CatalogEntry])
async def catalog(user: CurrentUser = Depends(current_user)) -> list[CatalogEntry]:
    return [
        CatalogEntry(
            **d.model_dump(include=set(CatalogEntry.model_fields) - {"abilities"}),
            abilities=[Ability(name=m.name, description=m.description or m.name, capability=m.capability,
                               desk=agent_for_capability(m.capability), permission=m.permission) for m in d.tools],
        )
        for d in CATALOG.values()
    ]


@router.get("/connections", response_model=list[ConnectionOut])
async def list_connections(request: Request, user: CurrentUser = Depends(current_user)) -> list[Connection]:
    async with request.app.state.session_factory() as session:
        rows = await session.scalars(
            select(Connection).where(Connection.workspace_id == user.workspace_id).order_by(Connection.created_at)
        )
        return list(rows)


def _invalid(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


def _validate(body: ConnectionCreate, allowed_roots: list[str]) -> None:
    """Checks the form against the definition and normalises it in place (trimmed text, real booleans)."""
    definition = CATALOG.get(body.type)
    if definition is None or definition.status != "available":
        raise _invalid(f"Connector {body.type!r} is not available")
    fields = {f.key: f for f in definition.config_fields}
    for key in body.config:
        # config is stored in plain text and filled into commands, so only declared, non-secret keys
        if key not in fields or fields[key].secret:
            raise _invalid(f"Unknown setting {key!r} for {definition.display_name}")
    for field in definition.config_fields:
        values = body.secrets if field.secret else body.config
        if field.key not in values:
            continue
        value = values[field.key]
        if field.boolean:
            if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
                value = value.strip().lower() == "true"
            if not isinstance(value, bool):
                raise _invalid(f"{field.label} must be true or false")
            values[field.key] = value
            continue
        value = str(value).strip()
        if field.pattern and value and not re.fullmatch(field.pattern, value):
            raise _invalid(f"{field.label} does not look right" + (f" (expected {field.placeholder})"
                                                                  if field.placeholder else ""))
        values[field.key] = value
    missing = [
        f.label for f in definition.config_fields
        if f.required and not str((body.secrets if f.secret else body.config).get(f.key, "")).strip()
    ]
    if missing:
        raise _invalid(f"Missing required fields: {', '.join(missing)}")
    if definition.type == "knowledge":
        try:
            resolve_vault_path(str(body.config["vault_path"]), allowed_roots)
        except ValueError as exc:
            raise _invalid(str(exc)) from exc


@router.post("/connections", status_code=status.HTTP_201_CREATED, response_model=ConnectionCreated)
async def create_connection(
    body: ConnectionCreate, request: Request, user: CurrentUser = Depends(require_csrf)
) -> ConnectionCreated:
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
    return ConnectionCreated(**ConnectionOut.model_validate(row).model_dump(), detail=health.detail)


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


async def _owned(request: Request, user: CurrentUser, connection_id: str) -> Connection:
    async with request.app.state.session_factory() as session:
        row = await session.scalar(select(Connection).where(
            Connection.id == connection_id, Connection.workspace_id == user.workspace_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    return row


@router.get("/connections/{connection_id}/tools", response_model=list[Ability])
async def connection_tools(connection_id: str, request: Request,
                           user: CurrentUser = Depends(current_user)) -> list[Ability]:
    """The abilities this connection gives the agents right now, as the server reports them."""
    state = request.app.state
    row = await _owned(request, user, connection_id)
    try:
        connector = build_connector(row, state.secret_box, state.settings, state.embedder)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    try:
        specs = await connector.list_tools()
    except Exception as exc:  # noqa: BLE001 - reported to the user
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Could not list tools: {exc}") from exc
    finally:
        await connector.aclose()
    return [Ability(name=t.name, description=t.description, capability=t.capability,
                    desk=agent_for_capability(t.capability), permission=t.permission) for t in specs]


@router.post("/connections/{connection_id}/test", response_model=TestResult)
async def test_connection(connection_id: str, request: Request,
                          user: CurrentUser = Depends(require_csrf)) -> TestResult:
    state = request.app.state
    row = await _owned(request, user, connection_id)
    try:
        connector = build_connector(row, state.secret_box, state.settings, state.embedder)
        try:
            health = await connector.health_check()
        finally:
            await connector.aclose()
        ok, detail = health.ok, health.detail
    except ValueError as exc:
        ok, detail = False, str(exc)
    async with state.session_factory() as session:
        stored = await session.get(Connection, row.id)
        stored.status = "connected" if ok else "error"
        stored.last_error = None if ok else detail
        session.add(AuditLog(workspace_id=user.workspace_id, actor=user.email, channel="web",
                             action="connection.test", target=row.id, detail={"ok": ok}))
        await session.commit()
    return TestResult(ok=ok, detail=detail)
