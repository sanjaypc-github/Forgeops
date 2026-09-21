from sqlalchemy import select

from forgeops.db.models import Membership, User
from tests.conftest import ADMIN_EMAIL


async def test_health_reports_database_ok(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_startup_creates_admin_and_workspace_once(app, settings, session_factory):
    from forgeops.services.bootstrap import ensure_admin

    async with session_factory() as session:
        user, workspace = await ensure_admin(session, settings)  # second call
        users = (await session.scalars(select(User))).all()
        memberships = (await session.scalars(select(Membership))).all()
    assert [u.email for u in users] == [ADMIN_EMAIL]
    assert len(memberships) == 1 and memberships[0].workspace_id == workspace.id
