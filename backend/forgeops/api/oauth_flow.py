"""Connecting a tool that uses OAuth: start the consent, then finish it at the callback.

The PKCE verifier never leaves the server, and a consent is only ever completed by the workspace that
started it. Pending consents live in memory with a short life: a restart simply means clicking Connect
again, which is safer than storing half-finished authorizations.
"""

import json
import secrets
from typing import Any
from dataclasses import dataclass, field
from html import escape
from datetime import UTC, datetime, timedelta

import httpx2
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from forgeops.api.connections import ConnectionCreate, validate_config
from forgeops.api.deps import CurrentUser, current_user, require_csrf
from forgeops.connectors.definitions import CATALOG
from forgeops.connectors.factory import OAUTH_KEY, build_connector
from forgeops.connectors.oauth import (
    OAuthError, authorization_url, discover, exchange_code, new_verifier, register_client,
)
from forgeops.connectors.tokens import OAuthSession
from forgeops.db.models import AuditLog, Connection

log = structlog.get_logger()
router = APIRouter(tags=["connections"])

CALLBACK_PATH = "/api/connections/oauth/callback"
PENDING_MINUTES = 10


@dataclass
class Pending:
    connection_id: str
    workspace_id: str
    verifier: str
    client_id: str
    client_secret: str | None
    server: object
    expires_at: datetime


@dataclass
class PendingConsents:
    """Consents waiting for the customer to approve them, keyed by the OAuth state."""

    items: dict[str, Pending] = field(default_factory=dict)

    def put(self, state: str, pending: Pending) -> None:
        self.prune()
        self.items[state] = pending

    def take(self, state: str) -> Pending | None:
        self.prune()
        return self.items.pop(state, None)

    def prune(self, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        for key in [k for k, v in self.items.items() if v.expires_at <= now]:
            del self.items[key]


def consents(request: Request) -> PendingConsents:
    store = getattr(request.app.state, "oauth_consents", None)
    if store is None:
        store = PendingConsents()
        request.app.state.oauth_consents = store
    return store


class OAuthStart(BaseModel):
    type: str
    name: str = ""
    # The connector still has non-secret settings to collect (Cloudflare's account id
    # names the account the service map talks about). Only the credential comes from
    # the provider, so dropping these would store a connection nothing can describe.
    config: dict[str, Any] = Field(default_factory=dict)


class OAuthStarted(BaseModel):
    connection_id: str
    authorize_url: str


def _redirect_uri(request: Request) -> str:
    return str(request.base_url).rstrip("/") + CALLBACK_PATH


def _openers(request: Request) -> list[str]:
    """Origins allowed to receive the result: the configured app origins, never a wildcard."""
    configured = [o for o in (request.app.state.settings.cors_origins or []) if o and o != "*"]
    return configured or [str(request.base_url).rstrip("/")]


def _page(title: str, message: str, ok: bool, request: Request) -> HTMLResponse:
    """A tiny self-contained page: the consent window shows it and closes itself.

    Everything shown here can come from the provider's query string, so every value is escaped and
    the result is posted only to the app's own origins.
    """
    colour = "#2e7d4f" if ok else "#b3261e"
    payload = json.dumps({"source": "forgeops-oauth", "ok": ok})
    origins = json.dumps(_openers(request))
    return HTMLResponse(
        "<!doctype html><meta charset='utf-8'><title>ForgeOps</title>"
        "<body style=\"font:16px/1.5 system-ui;margin:0;display:grid;place-items:center;height:100vh\">"
        "<main style='text-align:center;max-width:36rem;padding:24px'>"
        f"<h1 style='color:{colour};font-size:1.25rem'>{escape(title)}</h1><p>{escape(message)}</p>"
        "<p style='color:#6b746f'>You can close this window.</p></main>"
        "<script>try{for(const o of " + origins + "){window.opener&&window.opener.postMessage("
        + payload + ",o)}setTimeout(()=>window.close(),1200)}catch(e){}</script></body>",
        status_code=200 if ok else 400,
    )


@router.post("/connections/oauth/start", response_model=OAuthStarted,
             status_code=status.HTTP_201_CREATED)
async def start_oauth(body: OAuthStart, request: Request,
                      user: CurrentUser = Depends(require_csrf)) -> OAuthStarted:
    definition = CATALOG.get(body.type)
    if definition is None or definition.status != "available" or definition.auth != "oauth":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"Connector {body.type!r} does not connect with OAuth")
    draft = ConnectionCreate(type=body.type, name=body.name.strip() or definition.display_name,
                             config=dict(body.config), secrets={})
    validate_config(draft, request.app.state.settings.knowledge_vault_roots)

    redirect_uri = _redirect_uri(request)
    try:
        async with httpx2.AsyncClient() as client:
            server = await discover(definition.url or "", client)
            registration = await register_client(server, redirect_uri, client)
    except OAuthError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    row = Connection(workspace_id=user.workspace_id, type=definition.type,
                     name=draft.name, config=draft.config,
                     status="connecting", last_error="Waiting for you to approve access")
    async with request.app.state.session_factory() as session:
        session.add(row)
        await session.flush()
        session.add(AuditLog(workspace_id=user.workspace_id, actor=user.email, channel="web",
                             action="connection.oauth_start", target=row.id, detail={"type": row.type}))
        await session.commit()

    state = secrets.token_urlsafe(32)
    verifier = new_verifier()
    consents(request).put(state, Pending(
        connection_id=row.id, workspace_id=user.workspace_id, verifier=verifier,
        client_id=registration.client_id, client_secret=registration.client_secret, server=server,
        expires_at=datetime.now(UTC) + timedelta(minutes=PENDING_MINUTES)))
    url = authorization_url(server, client_id=registration.client_id, redirect_uri=redirect_uri,
                            state=state, verifier=verifier,
                            scopes=definition.oauth_scopes or None)
    log.info("oauth.started", connection_id=row.id, type=row.type)
    return OAuthStarted(connection_id=row.id, authorize_url=url)


@router.get(CALLBACK_PATH.removeprefix("/api"), response_class=HTMLResponse)
async def oauth_callback(request: Request, code: str = "", state: str = "", error: str = "",
                         error_description: str = "",
                         user: CurrentUser = Depends(current_user)) -> HTMLResponse:
    if error:
        return _page("Access was not granted", error_description or error, ok=False, request=request)
    pending = consents(request).take(state)
    if pending is None or not code:
        return _page("That approval has expired", "Start the connection again from the Connectors page.",
                     ok=False, request=request)
    if pending.workspace_id != user.workspace_id:
        log.warning("oauth.workspace_mismatch", connection_id=pending.connection_id)
        return _page("That approval belongs to another workspace", "Nothing was connected.", ok=False, request=request)

    app_state = request.app.state
    try:
        async with httpx2.AsyncClient() as client:
            tokens = await exchange_code(pending.server, code=code, client_id=pending.client_id,
                                         redirect_uri=_redirect_uri(request), verifier=pending.verifier,
                                         client=client, client_secret=pending.client_secret)
    except OAuthError as exc:
        await _record_failure(app_state, pending.connection_id, str(exc))
        return _page("The provider refused the connection", str(exc), ok=False, request=request)

    session = OAuthSession.build(pending.server, pending.client_id, pending.client_secret, tokens)
    async with app_state.session_factory() as db:
        row = await db.get(Connection, pending.connection_id)
        if row is None:
            return _page("That connection was removed", "Start again from the Connectors page.", ok=False, request=request)
        row.secret_encrypted = app_state.secret_box.encrypt_json({OAUTH_KEY: session.dump()})
        row.status, row.last_error = "connected", None
        await db.commit()
        await db.refresh(row)

    health = await _check(app_state, row)
    async with app_state.session_factory() as db:
        stored = await db.get(Connection, pending.connection_id)
        stored.status = "connected" if health.ok else "error"
        stored.last_error = None if health.ok else health.detail
        db.add(AuditLog(workspace_id=pending.workspace_id, actor=user.email, channel="web",
                        action="connection.oauth_complete", target=stored.id,
                        detail={"type": stored.type, "ok": health.ok}))
        await db.commit()
    log.info("oauth.completed", connection_id=row.id, ok=health.ok)
    return _page(f"{row.name} is connected" if health.ok else f"{row.name} needs attention",
                 health.detail, ok=health.ok, request=request)


async def _check(app_state, row: Connection):
    from forgeops.capabilities.models import HealthStatus

    try:
        connector = build_connector(row, app_state.secret_box, app_state.settings, app_state.embedder,
                                    app_state.session_factory)
    except ValueError as exc:
        return HealthStatus(ok=False, detail=str(exc))
    try:
        return await connector.health_check()
    finally:
        await connector.aclose()


async def _record_failure(app_state, connection_id: str, detail: str) -> None:
    async with app_state.session_factory() as db:
        row = await db.get(Connection, connection_id)
        if row is not None:
            row.status, row.last_error = "error", detail
            await db.commit()
