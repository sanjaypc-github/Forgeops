import asyncio

import pytest
from sqlalchemy import select, update

from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.db.models import AuditLog, Investigation
from forgeops.engine.llm.base import LLMReply
from tests.engine.fakes import ScriptedLLM
from tests.engine.graph_fixtures import fake_connectors, script


@pytest.fixture
def engine(app):
    """Point the app's runner at a scripted LLM and fake connectors (test-only)."""
    s = script()
    s["followup"] = [LLMReply(text="Because ev_x shows the pool change.")]
    llm = ScriptedLLM(s)
    app.state.llm_factory = lambda: llm

    async def registry(workspace_id):
        return await CapabilityRegistry.build(list(fake_connectors()))

    app.state.registry_factory = registry
    return llm


async def _start(auth_client, app, text="Checkout is slow after the deploy"):
    resp = await auth_client.post("/api/chat", json={"text": text})
    assert resp.status_code == 201, resp.text
    inv_id = resp.json()["investigation_id"]
    await app.state.runner.wait(inv_id)
    return inv_id


async def test_chat_starts_an_investigation_that_pauses_for_approval(auth_client, app, engine):
    inv_id = await _start(auth_client, app)
    detail = (await auth_client.get(f"/api/investigations/{inv_id}")).json()
    assert detail["status"] == "awaiting_approval" and detail["source"] == "chat"
    assert detail["details"]["rca"]["summary"] == "Pool lowered"
    assert len(detail["details"]["evidence"]) == 2
    history = await app.state.event_bus.history(inv_id)
    assert [e.type for e in history[:3]] == ["investigation_started", "chat_message", "supervisor_started"]
    assert history[1].data == {"role": "user", "text": "Checkout is slow after the deploy"}


async def test_approve_completes_and_report_is_available(auth_client, app, engine, session_factory):
    inv_id = await _start(auth_client, app)
    assert (await auth_client.get(f"/api/investigations/{inv_id}/report")).status_code == 404
    rec_id = (await auth_client.get(f"/api/investigations/{inv_id}")).json()["details"]["rca"][
        "recommendations"][0]["id"]
    resp = await auth_client.post(f"/api/investigations/{inv_id}/decision",
                                  json={"kind": "approve", "approved_recommendation_ids": [rec_id]})
    assert resp.status_code == 202
    await app.state.runner.wait(inv_id)
    detail = (await auth_client.get(f"/api/investigations/{inv_id}")).json()
    assert detail["status"] == "completed"
    assert detail["details"]["action_results"][0]["status"] == "done"
    report = await auth_client.get(f"/api/investigations/{inv_id}/report")
    assert report.status_code == 200 and report.headers["content-type"].startswith("text/markdown")
    assert "Pool lowered" in report.text
    async with session_factory() as s:
        actions = [a.action for a in (await s.scalars(select(AuditLog))).all()]
    assert "investigation.approve" in actions
    again = await auth_client.post(f"/api/investigations/{inv_id}/decision", json={"kind": "reject"})
    assert again.status_code == 409


async def test_decision_rejects_unknown_recommendation(auth_client, app, engine):
    inv_id = await _start(auth_client, app)
    resp = await auth_client.post(f"/api/investigations/{inv_id}/decision",
                                  json={"kind": "approve", "approved_recommendation_ids": ["rec_99"]})
    assert resp.status_code == 422


async def test_follow_up_question_gets_a_supervisor_answer(auth_client, app, engine):
    inv_id = await _start(auth_client, app)
    resp = await auth_client.post("/api/chat", json={"text": "Why the pool?", "investigation_id": inv_id})
    assert resp.status_code == 202 and resp.json()["status"] == "answering"
    await asyncio.gather(*app.state.chat_tasks)
    chat = (await auth_client.get(f"/api/investigations/{inv_id}/chat")).json()
    assert [(m["role"], m["text"]) for m in chat][-2:] == [
        ("user", "Why the pool?"), ("supervisor", "Because ev_x shows the pool change.")]


async def test_missing_openrouter_key_fails_clearly(auth_client, app):
    inv_id = await _start(auth_client, app)  # default factory: settings have no key
    detail = (await auth_client.get(f"/api/investigations/{inv_id}")).json()
    assert detail["status"] == "failed"
    last = (await app.state.event_bus.history(inv_id))[-1]
    assert last.type == "investigation_failed"
    assert last.data["reason"] == "OPENROUTER_API_KEY is not set in .env"
    resp = await auth_client.post("/api/chat", json={"text": "hello?", "investigation_id": inv_id})
    assert resp.status_code == 409


async def test_web_form_also_starts_the_engine(auth_client, app, engine):
    resp = await auth_client.post("/api/investigations", json={"description": "Orders failing"})
    inv_id = resp.json()["id"]
    await app.state.runner.wait(inv_id)
    assert (await auth_client.get(f"/api/investigations/{inv_id}")).json()["status"] == "awaiting_approval"


async def test_restart_recovery_marks_running_investigations_failed(auth_client, app, session_factory):
    resp = await auth_client.post("/api/investigations", json={"description": "Orders failing"})
    inv_id = resp.json()["id"]
    await app.state.runner.wait(inv_id)
    async with session_factory() as s:
        await s.execute(update(Investigation).where(Investigation.id == inv_id).values(status="running"))
        await s.commit()
    assert await app.state.runner.recover_on_startup() == 1
    async with session_factory() as s:
        assert (await s.get(Investigation, inv_id)).status == "failed"
