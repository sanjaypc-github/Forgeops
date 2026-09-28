"""The OAuth connect flow end to end, with the provider answered in memory."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from sqlalchemy import select

from forgeops.api.oauth_flow import PENDING_MINUTES, Pending, PendingConsents
from forgeops.connectors.definitions import CATALOG, ConnectorDefinition
from forgeops.connectors.factory import OAUTH_KEY
from forgeops.db.models import Connection
from forgeops.engine.models import AgentId, Capability

MCP_URL = "https://mcp.provider.test/mcp"
METADATA = {
    "issuer": "https://auth.provider.test",
    "authorization_endpoint": "https://auth.provider.test/authorize",
    "token_endpoint": "https://auth.provider.test/token",
    "registration_endpoint": "https://auth.provider.test/register",
    "scopes_supported": ["account:read"],
}


@pytest.fixture
def oauth_connector(monkeypatch):
    """A catalog entry that connects with OAuth; removed again after the test."""
    from forgeops.connectors.definitions import ToolMapping

    definition = ConnectorDefinition(
        type="provider", display_name="Provider", description="test", agents=[AgentId.frontend_hosting],
        status="available", transport="http", auth="oauth", url=MCP_URL,
        headers={"Authorization": "Bearer {access_token}"},
        tools=[ToolMapping(upstream="list_deployments", name="provider.list_deployments",
                           capability=Capability.hosting, permission="read")])
    monkeypatch.setitem(CATALOG, "provider", definition)
    return definition


@pytest.fixture
def provider(monkeypatch):
    """Answers discovery, registration and the token endpoint without leaving the machine."""
    calls: list[httpx2.Request] = []
    routes = {
        "https://mcp.provider.test/.well-known/oauth-protected-resource/mcp": httpx2.Response(
            200, json={"resource": MCP_URL, "authorization_servers": ["https://auth.provider.test"]}),
        "https://auth.provider.test/.well-known/oauth-authorization-server": httpx2.Response(200, json=METADATA),
        "https://auth.provider.test/register": httpx2.Response(201, json={"client_id": "cid_1"}),
        "https://auth.provider.test/token": httpx2.Response(200, json={
            "access_token": "at_1", "refresh_token": "rt_1", "expires_in": 3600, "scope": "account:read"}),
    }

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(request)
        return routes.get(str(request.url), httpx2.Response(404, json={"error": "not found"}))

    original = httpx2.AsyncClient

    def patched(*args, **kwargs):
        kwargs.setdefault("transport", httpx2.MockTransport(handler))
        return original(*args, **kwargs)

    monkeypatch.setattr("forgeops.api.oauth_flow.httpx2.AsyncClient", patched)
    return calls, routes


async def test_start_returns_a_consent_url_and_keeps_the_verifier_on_the_server(
        auth_client, app, oauth_connector, provider):
    calls, _ = provider
    resp = await auth_client.post("/api/connections/oauth/start",
                                  json={"type": "provider", "name": "Hosting"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    query = {k: v[0] for k, v in parse_qs(urlsplit(body["authorize_url"]).query).items()}
    assert body["authorize_url"].startswith("https://auth.provider.test/authorize?")
    assert query["client_id"] == "cid_1" and query["code_challenge_method"] == "S256"
    assert query["resource"] == MCP_URL and "code_verifier" not in query
    assert query["redirect_uri"].endswith("/api/connections/oauth/callback")

    # the connection exists but is not usable yet
    listed = (await auth_client.get("/api/connections")).json()
    assert [(c["name"], c["status"]) for c in listed] == [("Hosting", "connecting")]
    pending = app.state.oauth_consents.items[query["state"]]
    assert pending.connection_id == body["connection_id"] and len(pending.verifier) >= 43
    assert pending.verifier not in resp.text  # the verifier is never sent to the browser


async def test_the_callback_stores_the_tokens_and_marks_the_connection(
        auth_client, app, session_factory, oauth_connector, provider, monkeypatch):
    async def health(app_state, row):
        from forgeops.capabilities.models import HealthStatus
        return HealthStatus(ok=True, detail="1 read tools available")

    monkeypatch.setattr("forgeops.api.oauth_flow._check", health)
    started = (await auth_client.post("/api/connections/oauth/start", json={"type": "provider"})).json()
    state = next(iter(app.state.oauth_consents.items))

    page = await auth_client.get(f"/api/connections/oauth/callback?code=code_1&state={state}")
    assert page.status_code == 200 and "is connected" in page.text
    assert "at_1" not in page.text  # the page never shows the token

    async with session_factory() as db:
        row = (await db.scalars(select(Connection))).one()
    assert row.id == started["connection_id"] and row.status == "connected"
    stored = app.state.secret_box.decrypt_json(row.secret_encrypted)[OAUTH_KEY]
    assert stored["access_token"] == "at_1" and stored["refresh_token"] == "rt_1"
    assert stored["token_endpoint"] == METADATA["token_endpoint"]
    assert app.state.oauth_consents.items == {}  # the consent is single use


async def test_a_failed_health_check_leaves_the_reason_on_the_connection(
        auth_client, app, session_factory, oauth_connector, provider, monkeypatch):
    async def health(app_state, row):
        from forgeops.capabilities.models import HealthStatus
        return HealthStatus(ok=False, detail="the server offers none of the tools ForgeOps uses")

    monkeypatch.setattr("forgeops.api.oauth_flow._check", health)
    await auth_client.post("/api/connections/oauth/start", json={"type": "provider"})
    state = next(iter(app.state.oauth_consents.items))
    page = await auth_client.get(f"/api/connections/oauth/callback?code=c&state={state}")
    assert page.status_code == 400 and "needs attention" in page.text

    listed = (await auth_client.get("/api/connections")).json()
    assert listed[0]["status"] == "error" and "none of the tools" in listed[0]["last_error"]


async def test_a_denied_or_unknown_consent_changes_nothing(auth_client, app, oauth_connector, provider):
    denied = await auth_client.get("/api/connections/oauth/callback"
                                   "?error=access_denied&error_description=You+said+no&state=x")
    assert denied.status_code == 400 and "You said no" in denied.text

    unknown = await auth_client.get("/api/connections/oauth/callback?code=c&state=never_issued")
    assert unknown.status_code == 400 and "expired" in unknown.text
    assert (await auth_client.get("/api/connections")).json() == []


async def test_another_workspace_cannot_finish_someone_elses_consent(auth_client, app, oauth_connector,
                                                                     provider):
    await auth_client.post("/api/connections/oauth/start", json={"type": "provider"})
    state = next(iter(app.state.oauth_consents.items))
    app.state.oauth_consents.items[state].workspace_id = "ws_someone_else"

    page = await auth_client.get(f"/api/connections/oauth/callback?code=c&state={state}")
    assert page.status_code == 400 and "another workspace" in page.text
    listed = (await auth_client.get("/api/connections")).json()
    assert listed[0]["status"] == "connecting"  # nothing was stored


async def test_a_token_connector_cannot_use_the_oauth_flow(auth_client):
    resp = await auth_client.post("/api/connections/oauth/start", json={"type": "github"})
    assert resp.status_code == 422 and "does not connect with OAuth" in resp.json()["detail"]


async def test_starting_requires_csrf(auth_client, oauth_connector, provider):
    auth_client.headers.pop("X-CSRF-Token")
    assert (await auth_client.post("/api/connections/oauth/start",
                                   json={"type": "provider"})).status_code == 403


def test_pending_consents_expire():
    store = PendingConsents()
    old = Pending(connection_id="con_1", workspace_id="ws", verifier="v", client_id="c",
                  client_secret=None, server=object(),
                  expires_at=datetime.now(UTC) - timedelta(seconds=1))
    fresh = Pending(connection_id="con_2", workspace_id="ws", verifier="v", client_id="c",
                    client_secret=None, server=object(),
                    expires_at=datetime.now(UTC) + timedelta(minutes=PENDING_MINUTES))
    store.items.update({"old": old, "fresh": fresh})
    assert store.take("old") is None
    assert store.take("fresh") is fresh and store.take("fresh") is None
