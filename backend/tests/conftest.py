import asyncio
import os

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from forgeops.config import Settings
from forgeops.db.models import Base
from forgeops.db.session import create_engine, ensure_schema
from forgeops.main import create_app, shutdown, startup
from tests.engine.fakes import HashEmbedder

ADMIN_EMAIL = "admin@test.local"
ADMIN_PASSWORD = "correct horse battery"
TEST_SCHEMA = "forgeops_test"


def _test_database_url() -> str:
    # Same database as development (repo-root .env), isolated in its own schema.
    return os.environ.get("TEST_DATABASE_URL") or Settings().database_url


async def _create_test_tables(url: str) -> None:
    engine = create_engine(url, TEST_SCHEMA, poolclass=NullPool)
    await ensure_schema(engine, TEST_SCHEMA)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture(scope="session")
def database_url() -> str:
    url = _test_database_url()
    asyncio.run(_create_test_tables(url))  # once per test run
    return url


@pytest.fixture
def settings(database_url, tmp_path_factory) -> Settings:
    return Settings(
        database_url=database_url,
        database_schema=TEST_SCHEMA,
        forgeops_secret_key=Fernet.generate_key().decode(),
        forgeops_admin_email=ADMIN_EMAIL,
        forgeops_admin_password=ADMIN_PASSWORD,
        forgeops_workspace_name="Test workspace",
        openrouter_api_key=None,
        knowledge_data_dir=str(tmp_path_factory.mktemp("knowledge-index")),
        knowledge_vault_roots=[str(tmp_path_factory.getbasetemp())],
    )


@pytest.fixture
async def app(settings):
    engine = create_engine(settings.database_url, TEST_SCHEMA, poolclass=NullPool)
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await engine.dispose()

    application = create_app(settings)
    await startup(application, settings)
    application.state.embedder = HashEmbedder()  # never download a model in tests
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
