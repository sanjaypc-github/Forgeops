"""What an OAuth connection stores, and how its access token stays fresh while an investigation runs.

The authorization server's metadata is stored with the tokens, so a refresh needs no rediscovery, and
a refreshed token is written back immediately: providers may rotate refresh tokens, and losing one would
force the customer to connect again.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import httpx2
import structlog
from pydantic import BaseModel, Field

from forgeops.connectors.oauth import AuthServer, OAuthError, Tokens, refresh_tokens

log = structlog.get_logger()
Save = Callable[["OAuthSession"], Awaitable[None]]


class OAuthSession(BaseModel):
    """The whole OAuth state of one connection; stored encrypted, never returned to the browser."""

    client_id: str
    client_secret: str | None = None
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    registration_endpoint: str | None = None
    scopes_supported: list[str] = Field(default_factory=list)
    resource: str | None = None
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scope: str = ""

    @classmethod
    def build(cls, server: AuthServer, client_id: str, client_secret: str | None,
              tokens: Tokens) -> "OAuthSession":
        return cls(client_id=client_id, client_secret=client_secret, issuer=server.issuer,
                   authorization_endpoint=server.authorization_endpoint,
                   token_endpoint=server.token_endpoint,
                   registration_endpoint=server.registration_endpoint,
                   scopes_supported=server.scopes_supported, resource=server.resource,
                   access_token=tokens.access_token, refresh_token=tokens.refresh_token,
                   expires_at=tokens.expires_at, scope=tokens.scope)

    @property
    def server(self) -> AuthServer:
        return AuthServer(issuer=self.issuer, authorization_endpoint=self.authorization_endpoint,
                          token_endpoint=self.token_endpoint,
                          registration_endpoint=self.registration_endpoint,
                          scopes_supported=list(self.scopes_supported), resource=self.resource)

    @property
    def tokens(self) -> Tokens:
        return Tokens(access_token=self.access_token, refresh_token=self.refresh_token,
                      expires_at=self.expires_at, scope=self.scope)

    def with_tokens(self, tokens: Tokens) -> "OAuthSession":
        return self.model_copy(update={"access_token": tokens.access_token,
                                       "refresh_token": tokens.refresh_token,
                                       "expires_at": tokens.expires_at, "scope": tokens.scope})

    def dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ReconnectNeeded(Exception):
    """The provider will not issue a new token; only the customer can fix this."""


class TokenProvider:
    """Hands out an access token, refreshing and storing it when it is about to expire."""

    def __init__(self, session: OAuthSession, save: Save, connection_id: str = "",
                 now: Callable[[], datetime] = lambda: datetime.now(UTC),
                 client_factory: Callable[[], httpx2.AsyncClient] = httpx2.AsyncClient) -> None:
        self._session = session
        self._save = save
        self._connection_id = connection_id
        self._now = now
        self._client_factory = client_factory
        self._lock = asyncio.Lock()

    @property
    def session(self) -> OAuthSession:
        return self._session

    async def __call__(self) -> str:
        async with self._lock:  # parallel desks share one connection; refresh once
            if not self._session.tokens.stale(self._now()):
                return self._session.access_token
            try:
                async with self._client_factory() as client:
                    fresh = await refresh_tokens(self._session.server, self._session.tokens,
                                                 client_id=self._session.client_id, client=client,
                                                 client_secret=self._session.client_secret,
                                                 now=self._now())
            except OAuthError as exc:
                log.warning("oauth.refresh_failed", connection_id=self._connection_id, error=str(exc))
                raise ReconnectNeeded(f"the access token expired and could not be renewed ({exc}). "
                                      "Connect this tool again.") from exc
            self._session = self._session.with_tokens(fresh)
            await self._save(self._session)
            log.info("oauth.refreshed", connection_id=self._connection_id,
                     expires_at=str(self._session.expires_at))
            return self._session.access_token
