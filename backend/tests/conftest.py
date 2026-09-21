import os

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from forgeops.config import Settings
from forgeops.db.models import Base
from forgeops.main import create_app, shutdown, startup

ADMIN_EMAIL = "admin@test.local"
ADMIN_PASSWORD = "correct horse battery"


def _test_database_url() -> str:
    if url := os.environ.get("TEST_DATABASE_URL"):
        return url
    base = Settings().database_url  # repo-root .env
    return make_url(base).set(database="forgeops_test").render_as_string(hide_password=False)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=_test_database_url(),
        forgeops_secret_key=Fernet.generate_key().decode(),
        forgeops_admin_email=ADMIN_EMAIL,
        forgeops_admin_password=ADMIN_PASSWORD,
        forgeops_workspace_name="Test workspace",
    )


@pytest.fixture
async def app(settings):
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    application = create_app(settings)
    await startup(application, settings)
    yield application
    await shutdown(application)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def session_factory(app):
    return app.state.session_factory


@pytest.fixture
async def auth_client(client):
    response = await client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client
