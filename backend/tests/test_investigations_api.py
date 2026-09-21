import json

import pytest

from forgeops.db.models import Investigation, Workspace
from forgeops.events.models import EventIn, EventType


@pytest.fixture(autouse=True)
def idle_engine(app):
    """These tests cover the API and event stream only; the engine is tested elsewhere."""
    async def start(investigation_id):
        return None
    app.state.runner.start = start


async def test_create_requires_csrf(auth_client):
    auth_client.headers.pop("X-CSRF-Token")
    response = await auth_client.post("/api/investigations", json={"description": "checkout slow"})
    assert response.status_code == 403


async def test_create_and_get(auth_client, app):
    response = await auth_client.post(
        "/api/investigations", json={"description": "Checkout API latency is high"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("inv_")
    assert body["status"] == "running"
    assert body["source"] == "web"

    fetched = await auth_client.get(f"/api/investigations/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["description"] == "Checkout API latency is high"

    history = await app.state.event_bus.history(body["id"])
    assert [(e.seq, e.type) for e in history] == [(1, "investigation_started")]
    assert history[0].data == {"description": "Checkout API latency is high"}


async def test_description_is_validated(auth_client):
    response = await auth_client.post("/api/investigations", json={"description": "x"})
    assert response.status_code == 422


async def test_list_is_scoped_to_workspace(auth_client, session_factory):
    async with session_factory() as session:
        other = Workspace(name="Other company")
        session.add(other)
        await session.flush()
        session.add(Investigation(workspace_id=other.id, description="not yours"))
        await session.commit()
    await auth_client.post("/api/investigations", json={"description": "mine one"})

    listed = (await auth_client.get("/api/investigations")).json()
    assert [i["description"] for i in listed] == ["mine one"]


async def test_other_workspace_investigation_is_404(auth_client, session_factory):
    async with session_factory() as session:
        other = Workspace(name="Other company")
        session.add(other)
        await session.flush()
        inv = Investigation(workspace_id=other.id, description="not yours")
        session.add(inv)
        await session.commit()
    assert (await auth_client.get(f"/api/investigations/{inv.id}")).status_code == 404
    assert (await auth_client.get(f"/api/investigations/{inv.id}/events")).status_code == 404


def _sse_messages(text: str) -> list[dict]:
    messages, current = [], {}
    for line in text.splitlines():
        if not line:
            if current:
                messages.append(current)
                current = {}
            continue
        field, _, value = line.partition(":")
        current[field] = value.lstrip()
    if current:
        messages.append(current)
    return [m for m in messages if "data" in m]


async def test_events_stream_replays_finished_investigation(auth_client, app):
    created = (
        await auth_client.post("/api/investigations", json={"description": "orders failing"})
    ).json()
    bus = app.state.event_bus
    ws = (await auth_client.get("/api/auth/me")).json()["workspace"]["id"]
    await bus.emit(ws, created["id"], EventIn(type=EventType.investigation_completed))

    response = await auth_client.get(f"/api/investigations/{created['id']}/events")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    messages = _sse_messages(response.text)
    assert [m["id"] for m in messages] == ["1", "2"]
    assert [json.loads(m["data"])["type"] for m in messages] == [
        "investigation_started",
        "investigation_completed",
    ]


async def test_events_stream_honours_last_event_id(auth_client, app):
    created = (
        await auth_client.post("/api/investigations", json={"description": "orders failing"})
    ).json()
    ws = (await auth_client.get("/api/auth/me")).json()["workspace"]["id"]
    await app.state.event_bus.emit(
        ws, created["id"], EventIn(type=EventType.investigation_completed)
    )
    response = await auth_client.get(
        f"/api/investigations/{created['id']}/events", headers={"Last-Event-ID": "1"}
    )
    assert [m["id"] for m in _sse_messages(response.text)] == ["2"]
