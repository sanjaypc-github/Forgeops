from sqlalchemy import select

from forgeops.db.models import AuditLog
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


async def test_login_sets_cookie_and_returns_me(client):
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL.upper(), "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == ADMIN_EMAIL
    assert body["workspace"]["name"] == "Test workspace"
    assert len(body["csrf_token"]) >= 32
    assert "forgeops_session" in response.cookies
    assert "password" not in response.text


async def test_login_wrong_password_is_401(client):
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": "nope"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email or password is incorrect"


async def test_login_is_rate_limited(client):
    for _ in range(5):
        await client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "nope"})
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 429


async def test_me_requires_login(client):
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_me_after_login(auth_client):
    response = await auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == ADMIN_EMAIL


async def test_logout_requires_csrf_then_ends_session(auth_client):
    token = auth_client.headers.pop("X-CSRF-Token")
    assert (await auth_client.post("/api/auth/logout")).status_code == 403
    auth_client.headers["X-CSRF-Token"] = token
    assert (await auth_client.post("/api/auth/logout")).status_code == 204
    assert (await auth_client.get("/api/auth/me")).status_code == 401


async def test_login_is_audited(auth_client, session_factory):
    async with session_factory() as session:
        rows = (await session.scalars(select(AuditLog))).all()
    assert [(r.action, r.actor, r.channel) for r in rows] == [("auth.login", ADMIN_EMAIL, "web")]
