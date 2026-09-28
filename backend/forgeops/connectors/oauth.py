"""OAuth for MCP servers that do not take an API token (Cloudflare, Sanity, Sentry, …).

The customer clicks "Connect", approves in the provider's own window, and ForgeOps stores the tokens.
It follows what the MCP specification requires of clients:

- RFC 9728: ask the MCP server which authorization server protects it
- RFC 8414: read that server's metadata (with the OpenID Connect discovery fallback)
- RFC 7591: register ForgeOps as a client, because these servers issue no client ids by hand
- RFC 7636: PKCE with S256, so an intercepted code is useless

Nothing here touches the database or the network by itself; it is given an HTTP client, which makes it
testable offline and reusable by the API layer.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx2

REGISTRATION_NAME = "ForgeOps"
REFRESH_MARGIN = timedelta(seconds=120)  # refresh before the provider would reject the token
DISCOVERY_TIMEOUT = 20.0


class OAuthError(Exception):
    """The provider could not be discovered, or refused the request."""


@dataclass(frozen=True)
class AuthServer:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None = None
    scopes_supported: list[str] = field(default_factory=list)
    resource: str | None = None  # the MCP server this authorization is for (RFC 8707)


@dataclass(frozen=True)
class ClientRegistration:
    client_id: str
    client_secret: str | None = None


@dataclass(frozen=True)
class Tokens:
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scope: str = ""

    def stale(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return (now or datetime.now(UTC)) >= self.expires_at - REFRESH_MARGIN


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _well_known(url: str, suffix: str) -> list[str]:
    """RFC 8414 puts the path after the well-known segment; try that, then the bare root."""
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    candidates = [urlunsplit((parts.scheme, parts.netloc, f"/.well-known/{suffix}{path}", "", ""))] if path else []
    candidates.append(urlunsplit((parts.scheme, parts.netloc, f"/.well-known/{suffix}", "", "")))
    return candidates


async def _json(client: httpx2.AsyncClient, url: str) -> dict[str, Any] | None:
    try:
        response = await client.get(url, headers={"MCP-Protocol-Version": "2025-06-18"},
                                    timeout=DISCOVERY_TIMEOUT)
    except httpx2.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


async def discover(mcp_url: str, client: httpx2.AsyncClient) -> AuthServer:
    """Find the authorization server that protects an MCP endpoint."""
    resource = await _first(client, _well_known(mcp_url, "oauth-protected-resource"))
    issuers = list((resource or {}).get("authorization_servers") or [])
    issuer = str(issuers[0]) if issuers else _origin(mcp_url)

    metadata = await _first(client, [
        *_well_known(issuer, "oauth-authorization-server"),
        *_well_known(issuer, "openid-configuration"),
    ])
    if metadata is None:
        raise OAuthError(f"{_origin(mcp_url)} did not publish OAuth metadata, so ForgeOps cannot "
                         "connect to it automatically")
    for required in ("authorization_endpoint", "token_endpoint"):
        if not metadata.get(required):
            raise OAuthError(f"the authorization server at {issuer} published no {required}")
    return AuthServer(
        issuer=str(metadata.get("issuer") or issuer),
        authorization_endpoint=str(metadata["authorization_endpoint"]),
        token_endpoint=str(metadata["token_endpoint"]),
        registration_endpoint=(str(metadata["registration_endpoint"])
                               if metadata.get("registration_endpoint") else None),
        scopes_supported=[str(s) for s in (metadata.get("scopes_supported") or [])],
        resource=str((resource or {}).get("resource") or mcp_url),
    )


async def _first(client: httpx2.AsyncClient, urls: list[str]) -> dict[str, Any] | None:
    for url in urls:
        body = await _json(client, url)
        if body is not None:
            return body
    return None


async def register_client(server: AuthServer, redirect_uri: str,
                          client: httpx2.AsyncClient) -> ClientRegistration:
    """Register ForgeOps with the provider (RFC 7591); these servers issue no client ids by hand."""
    if not server.registration_endpoint:
        raise OAuthError(f"{server.issuer} does not support automatic client registration")
    payload = {
        "client_name": REGISTRATION_NAME,
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",  # a public client: the secret would sit in our database
    }
    if server.scopes_supported:
        payload["scope"] = " ".join(server.scopes_supported)
    try:
        response = await client.post(server.registration_endpoint, json=payload, timeout=DISCOVERY_TIMEOUT)
    except httpx2.HTTPError as exc:
        raise OAuthError(f"could not register with {server.issuer}: {exc}") from exc
    if response.status_code not in (200, 201):
        raise OAuthError(f"{server.issuer} refused the client registration ({response.status_code}): "
                         f"{response.text[:200]}")
    body = response.json()
    if not body.get("client_id"):
        raise OAuthError(f"{server.issuer} returned no client_id")
    return ClientRegistration(client_id=str(body["client_id"]),
                              client_secret=str(body["client_secret"]) if body.get("client_secret") else None)


def new_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")


def challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def authorization_url(server: AuthServer, *, client_id: str, redirect_uri: str, state: str,
                      verifier: str, scopes: list[str] | None = None) -> str:
    """The URL the customer opens to approve access."""
    wanted = scopes if scopes is not None else server.scopes_supported
    query = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge(verifier),
        "code_challenge_method": "S256",
    }
    if wanted:
        query["scope"] = " ".join(wanted)
    if server.resource:
        query["resource"] = server.resource  # RFC 8707: this consent is for one MCP server
    joiner = "&" if urlsplit(server.authorization_endpoint).query else "?"
    return f"{server.authorization_endpoint}{joiner}{urlencode(query)}"


def _tokens(body: dict[str, Any], now: datetime, previous: Tokens | None = None) -> Tokens:
    access = body.get("access_token")
    if not access:
        raise OAuthError("the authorization server returned no access token")
    expires_in = body.get("expires_in")
    expires_at = now + timedelta(seconds=int(expires_in)) if expires_in else None
    refresh = body.get("refresh_token") or (previous.refresh_token if previous else None)
    return Tokens(access_token=str(access), refresh_token=str(refresh) if refresh else None,
                  expires_at=expires_at, scope=str(body.get("scope") or (previous.scope if previous else "")))


async def _token_request(server: AuthServer, form: dict[str, str], client: httpx2.AsyncClient,
                         now: datetime, previous: Tokens | None = None) -> Tokens:
    if server.resource:
        form = {**form, "resource": server.resource}
    try:
        response = await client.post(server.token_endpoint, data=form,
                                     headers={"Accept": "application/json"}, timeout=DISCOVERY_TIMEOUT)
    except httpx2.HTTPError as exc:
        raise OAuthError(f"could not reach {server.token_endpoint}: {exc}") from exc
    if response.status_code != 200:
        raise OAuthError(f"the authorization server refused the request ({response.status_code}): "
                         f"{response.text[:200]}")
    return _tokens(response.json(), now, previous)


async def exchange_code(server: AuthServer, *, code: str, client_id: str, redirect_uri: str,
                        verifier: str, client: httpx2.AsyncClient,
                        client_secret: str | None = None, now: datetime | None = None) -> Tokens:
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
            "client_id": client_id, "code_verifier": verifier}
    if client_secret:
        form["client_secret"] = client_secret
    return await _token_request(server, form, client, now or datetime.now(UTC))


async def refresh_tokens(server: AuthServer, tokens: Tokens, *, client_id: str,
                         client: httpx2.AsyncClient, client_secret: str | None = None,
                         now: datetime | None = None) -> Tokens:
    if not tokens.refresh_token:
        raise OAuthError("this connection has no refresh token; connect it again")
    form = {"grant_type": "refresh_token", "refresh_token": tokens.refresh_token, "client_id": client_id}
    if client_secret:
        form["client_secret"] = client_secret
    return await _token_request(server, form, client, now or datetime.now(UTC), previous=tokens)
