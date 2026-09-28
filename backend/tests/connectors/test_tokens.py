import asyncio
from datetime import UTC, datetime, timedelta

import httpx2
import pytest

from forgeops.connectors.oauth import AuthServer, Tokens
from forgeops.connectors.tokens import OAuthSession, ReconnectNeeded, TokenProvider

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
SERVER = AuthServer(issuer="https://auth.example.com", authorization_endpoint="https://auth.example.com/a",
                    token_endpoint="https://auth.example.com/token", scopes_supported=["read"],
                    resource="https://mcp.example.com/mcp")


def _session(expires_in: int | None = 3600, refresh: str | None = "rt_1") -> OAuthSession:
    tokens = Tokens(access_token="at_1", refresh_token=refresh, scope="read",
                    expires_at=NOW + timedelta(seconds=expires_in) if expires_in is not None else None)
    return OAuthSession.build(SERVER, "cid_1", None, tokens)


def _provider(session, response: httpx2.Response, saved: list, calls: list | None = None):
    def handler(request):
        if calls is not None:
            calls.append(request)
        return response

    async def save(updated):
        saved.append(updated)

    return TokenProvider(session, save, connection_id="con_1", now=lambda: NOW,
                         client_factory=lambda: httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))


async def test_a_fresh_token_is_used_without_calling_the_provider():
    calls: list = []
    saved: list = []
    provider = _provider(_session(), httpx2.Response(500), saved, calls)
    assert await provider() == "at_1"
    assert calls == [] and saved == []


async def test_an_expiring_token_is_refreshed_and_stored():
    saved: list = []
    provider = _provider(_session(expires_in=30), httpx2.Response(
        200, json={"access_token": "at_2", "refresh_token": "rt_2", "expires_in": 3600}), saved)

    assert await provider() == "at_2"
    assert [s.access_token for s in saved] == ["at_2"]
    assert saved[0].refresh_token == "rt_2"  # rotated tokens must not be lost
    assert saved[0].expires_at == NOW + timedelta(seconds=3600)
    assert provider.session.access_token == "at_2"
    # the second caller reuses the refreshed token
    assert await provider() == "at_2" and len(saved) == 1


async def test_parallel_desks_refresh_the_token_only_once():
    saved: list = []
    calls: list = []
    provider = _provider(_session(expires_in=0), httpx2.Response(
        200, json={"access_token": "at_2", "expires_in": 3600}), saved, calls)

    results = await asyncio.gather(*(provider() for _ in range(5)))
    assert results == ["at_2"] * 5
    assert len(calls) == 1 and len(saved) == 1


async def test_a_refusal_asks_the_customer_to_connect_again():
    saved: list = []
    provider = _provider(_session(expires_in=0),
                         httpx2.Response(400, json={"error": "invalid_grant"}), saved)
    with pytest.raises(ReconnectNeeded, match="Connect this tool again"):
        await provider()
    assert saved == []


async def test_a_session_without_an_expiry_is_never_refreshed():
    calls: list = []
    provider = _provider(_session(expires_in=None), httpx2.Response(500), [], calls)
    assert await provider() == "at_1" and calls == []


def test_a_session_round_trips_through_storage():
    stored = _session().dump()
    assert stored["access_token"] == "at_1" and stored["token_endpoint"] == SERVER.token_endpoint
    back = OAuthSession.model_validate(stored)
    assert back.server == SERVER and back.tokens.refresh_token == "rt_1"
