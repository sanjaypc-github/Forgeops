from sqlalchemy import select

from forgeops.db.models import Connection


def _vault(tmp_path):
    (tmp_path / "a.md").write_text("# A\nhello", "utf-8")
    return str(tmp_path)


async def test_catalog_lists_knowledge_as_available(auth_client):
    catalog = (await auth_client.get("/api/connectors/catalog")).json()
    knowledge = next(c for c in catalog if c["type"] == "knowledge")
    assert knowledge["status"] == "available" and knowledge["agents"] == ["knowledge"]
    assert [f["key"] for f in knowledge["config_fields"]] == ["vault_path"]


async def test_connect_knowledge_vault(auth_client, tmp_path):
    resp = await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "Runbooks", "config": {"vault_path": _vault(tmp_path)}, "secrets": {}})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "connected" and body["id"].startswith("con_")
    listed = (await auth_client.get("/api/connections")).json()
    assert [c["name"] for c in listed] == ["Runbooks"]


async def test_bad_vault_is_stored_with_error(auth_client, tmp_path):
    resp = await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "Missing", "config": {"vault_path": str(tmp_path / "x")},
        "secrets": {}})
    assert resp.status_code == 201
    assert resp.json()["status"] == "error" and "not found" in resp.json()["last_error"]


async def test_unknown_type_and_missing_fields_are_rejected(auth_client):
    assert (await auth_client.post("/api/connections", json={
        "type": "nope", "name": "x", "config": {}, "secrets": {}})).status_code == 422
    assert (await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "x", "config": {}, "secrets": {}})).status_code == 422


async def test_requires_csrf(auth_client, tmp_path):
    auth_client.headers.pop("X-CSRF-Token")
    resp = await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "K", "config": {"vault_path": _vault(tmp_path)}, "secrets": {}})
    assert resp.status_code == 403


async def test_secrets_are_encrypted_and_never_returned(auth_client, session_factory, app, tmp_path):
    await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "K", "config": {"vault_path": _vault(tmp_path)},
        "secrets": {"unused_token": "s3cr3t"}})
    async with session_factory() as s:
        row = (await s.scalars(select(Connection))).one()
    assert "s3cr3t" not in (row.secret_encrypted or "")
    assert app.state.secret_box.decrypt_json(row.secret_encrypted) == {"unused_token": "s3cr3t"}
    assert "s3cr3t" not in (await auth_client.get("/api/connections")).text


async def test_delete(auth_client, tmp_path):
    cid = (await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "K", "config": {"vault_path": _vault(tmp_path)},
        "secrets": {}})).json()["id"]
    assert (await auth_client.delete(f"/api/connections/{cid}")).status_code == 204
    assert (await auth_client.get("/api/connections")).json() == []


async def test_registry_for_workspace_uses_connected_rows(auth_client, app, tmp_path):
    from forgeops.connectors.factory import build_registry_for_workspace
    from forgeops.engine.models import AgentId

    await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "K", "config": {"vault_path": _vault(tmp_path)}, "secrets": {}})
    await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "Broken", "config": {"vault_path": str(tmp_path / "missing")},
        "secrets": {}})
    ws = (await auth_client.get("/api/auth/me")).json()["workspace"]["id"]
    registry = await build_registry_for_workspace(
        app.state.session_factory, ws, app.state.secret_box, app.state.settings, app.state.embedder)
    try:
        assert [t.name for t in registry.tools_for(AgentId.knowledge)] == ["knowledge.search"]
    finally:
        await registry.aclose()
