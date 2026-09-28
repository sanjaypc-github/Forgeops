"""OAuth client tests. Every request is answered in memory; nothing leaves the machine."""

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest

from forgeops.connectors.oauth import (
    AuthServer, OAuthError, Tokens, authorization_url, challenge, discover, exchange_code,
    new_verifier, refresh_tokens, register_client,
)

MCP = "https://mcp.example.com/mcp"
REDIRECT = "http://localhost:8000/api/connections/oauth/callback"
NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)

METADATA = {
    "issuer": "https://auth.example.com",
    "authorization_endpoint": "https://auth.example.com/authorize",
    "token_endpoint": "https://auth.example.com/token",
    "registration_endpoint": "https://auth.example.com/register",
    "scopes_supported": ["account:read", "offline_access"],
}


def _client(routes: dict[str, httpx2.Response], seen: list | None = None) -> httpx2.AsyncClient:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if seen is not None:
            seen.append(request)
        response = routes.get(str(request.url))
        return response if response is not None else httpx2.Response(404, json={"error": "not found"})

    return httpx2.AsyncClient(transport=httpx2.MockTransport(handler))


def _server(**overrides) -> AuthServer:
    base = dict(issuer="https://auth.example.com", authorization_endpoint=METADATA["authorization_endpoint"],
                token_endpoint=METADATA["token_endpoint"], registration_endpoint=METADATA["registration_endpoint"],
                scopes_supported=["account:read"], resource=MCP)
    return AuthServer(**(base | overrides))


async def test_discovery_follows_the_protected_resource_to_its_authorization_server():
    routes = {
        "https://mcp.example.com/.well-known/oauth-protected-resource/mcp": httpx2.Response(
            200, json={"resource": MCP, "authorization_servers": ["https://auth.example.com"]}),
        "https://auth.example.com/.well-known/oauth-authorization-server": httpx2.Response(200, json=METADATA),
    }
    async with _client(routes) as client:
        server = await discover(MCP, client)
    assert server.issuer == "https://auth.example.com"
    assert server.token_endpoint == "https://auth.example.com/token"
    assert server.registration_endpoint == "https://auth.example.com/register"
    assert server.resource == MCP and server.scopes_supported == ["account:read", "offline_access"]


async def test_discovery_falls_back_to_the_mcp_origin_and_openid_metadata():
    routes = {  # no protected-resource document, and only OpenID discovery on the origin
        "https://mcp.example.com/.well-known/openid-configuration": httpx2.Response(200, json=METADATA),
    }
    async with _client(routes) as client:
        server = await discover(MCP, client)
    assert server.authorization_endpoint == METADATA["authorization_endpoint"]
    assert server.resource == MCP


async def test_a_server_without_metadata_is_reported_clearly():
    async with _client({}) as client:
        with pytest.raises(OAuthError, match="did not publish OAuth metadata"):
            await discover(MCP, client)


async def test_metadata_without_a_token_endpoint_is_refused():
    incomplete = {"issuer": "https://auth.example.com", "authorization_endpoint": "https://a/authorize"}
    routes = {"https://mcp.example.com/.well-known/openid-configuration": httpx2.Response(200, json=incomplete)}
    async with _client(routes) as client:
        with pytest.raises(OAuthError, match="no token_endpoint"):
            await discover(MCP, client)


async def test_forgeops_registers_itself_as_a_public_client():
    seen: list = []
    routes = {"https://auth.example.com/register": httpx2.Response(201, json={"client_id": "cid_1"})}
    async with _client(routes, seen) as client:
        registration = await register_client(_server(), REDIRECT, client)
    assert registration.client_id == "cid_1" and registration.client_secret is None
    body = seen[-1].content.decode()
    assert '"client_name":"ForgeOps"' in body.replace(" ", "")
    assert REDIRECT in body
    # a secret stored in our database would buy nothing, so ForgeOps registers as a public client
    assert '"token_endpoint_auth_method":"none"' in body.replace(" ", "")


async def test_registration_failures_name_the_provider():
    routes = {"https://auth.example.com/register": httpx2.Response(400, json={"error": "invalid_redirect_uri"})}
    async with _client(routes) as client:
        with pytest.raises(OAuthError, match="refused the client registration"):
            await register_client(_server(), REDIRECT, client)
    async with _client({}) as client:
        with pytest.raises(OAuthError, match="does not support automatic client registration"):
            await register_client(_server(registration_endpoint=None), REDIRECT, client)


def test_the_consent_url_carries_pkce_the_resource_and_the_state():
    verifier = new_verifier()
    url = authorization_url(_server(), client_id="cid_1", redirect_uri=REDIRECT, state="st_1",
                            verifier=verifier, scopes=["account:read"])
    query = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
    assert url.startswith("https://auth.example.com/authorize?")
    assert query["response_type"] == "code" and query["client_id"] == "cid_1"
    assert query["redirect_uri"] == REDIRECT and query["state"] == "st_1"
    assert query["scope"] == "account:read" and query["resource"] == MCP
    assert query["code_challenge_method"] == "S256"
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    assert query["code_challenge"] == expected == challenge(verifier)
    assert len(verifier) >= 43 and new_verifier() != verifier  # RFC 7636 length, and never reused


def test_the_consent_url_keeps_an_existing_query_string():
    server = _server(authorization_endpoint="https://auth.example.com/authorize?tenant=acme")
    url = authorization_url(server, client_id="c", redirect_uri=REDIRECT, state="s", verifier=new_verifier())
    assert "?tenant=acme&" in url and parse_qs(urlsplit(url).query)["tenant"] == ["acme"]


async def test_exchanging_the_code_returns_tokens_with_an_expiry():
    seen: list = []
    routes = {"https://auth.example.com/token": httpx2.Response(200, json={
        "access_token": "at_1", "refresh_token": "rt_1", "expires_in": 3600, "scope": "account:read"})}
    async with _client(routes, seen) as client:
        tokens = await exchange_code(_server(), code="code_1", client_id="cid_1", redirect_uri=REDIRECT,
                                     verifier="verifier_1", client=client, now=NOW)
    assert tokens.access_token == "at_1" and tokens.refresh_token == "rt_1"
    assert tokens.expires_at == NOW + timedelta(seconds=3600)
    form = {k: v[0] for k, v in parse_qs(seen[-1].content.decode()).items()}
    assert form["grant_type"] == "authorization_code" and form["code_verifier"] == "verifier_1"
    assert form["redirect_uri"] == REDIRECT and form["resource"] == MCP


async def test_a_refused_exchange_reports_the_provider_error():
    routes = {"https://auth.example.com/token": httpx2.Response(400, json={"error": "invalid_grant"})}
    async with _client(routes) as client:
        with pytest.raises(OAuthError, match="invalid_grant"):
            await exchange_code(_server(), code="bad", client_id="cid_1", redirect_uri=REDIRECT,
                                verifier="v", client=client, now=NOW)


async def test_refreshing_keeps_the_old_refresh_token_when_none_is_returned():
    routes = {"https://auth.example.com/token": httpx2.Response(
        200, json={"access_token": "at_2", "expires_in": 60})}
    old = Tokens(access_token="at_1", refresh_token="rt_1", expires_at=NOW, scope="account:read")
    async with _client(routes) as client:
        fresh = await refresh_tokens(_server(), old, client_id="cid_1", client=client, now=NOW)
    assert fresh.access_token == "at_2" and fresh.refresh_token == "rt_1"
    assert fresh.scope == "account:read" and fresh.expires_at == NOW + timedelta(seconds=60)


async def test_a_connection_without_a_refresh_token_asks_to_be_connected_again():
    async with _client({}) as client:
        with pytest.raises(OAuthError, match="connect it again"):
            await refresh_tokens(_server(), Tokens(access_token="at"), client_id="c", client=client)


def test_tokens_are_refreshed_before_the_provider_would_reject_them():
    assert Tokens(access_token="a").stale(NOW) is False  # no expiry: nothing to refresh
    assert Tokens(access_token="a", expires_at=NOW + timedelta(seconds=600)).stale(NOW) is False
    assert Tokens(access_token="a", expires_at=NOW + timedelta(seconds=60)).stale(NOW) is True
    assert Tokens(access_token="a", expires_at=NOW - timedelta(seconds=1)).stale(NOW) is True
