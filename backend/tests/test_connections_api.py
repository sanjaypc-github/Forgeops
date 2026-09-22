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


async def test_vault_outside_allowed_roots_is_rejected(auth_client, app, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("# private", "utf-8")
    app.state.settings = app.state.settings.model_copy(
        update={"knowledge_vault_roots": [str(tmp_path / "allowed")]})
    resp = await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "Sneaky", "config": {"vault_path": str(outside)}, "secrets": {}})
    assert resp.status_code == 422 and "allowed" in resp.json()["detail"]
    traversal = str(tmp_path / "allowed" / ".." / "outside")
    resp = await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "Sneaky2", "config": {"vault_path": traversal}, "secrets": {}})
    assert resp.status_code == 422


def test_factory_refuses_stored_path_outside_roots(app, tmp_path):
    import pytest

    from forgeops.connectors.factory import build_connector
    from forgeops.db.models import Connection

    settings = app.state.settings.model_copy(update={"knowledge_vault_roots": [str(tmp_path / "allowed")]})
    row = Connection(id="con_x", workspace_id="ws_x", type="knowledge", name="x",
                     config={"vault_path": str(tmp_path)})
    with pytest.raises(ValueError, match="allowed"):
        build_connector(row, app.state.secret_box, settings, app.state.embedder)


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


async def test_catalog_shows_github_and_supabase_abilities_by_desk(auth_client):
    catalog = {c["type"]: c for c in (await auth_client.get("/api/connectors/catalog")).json()}
    gh = catalog["github"]
    assert gh["status"] == "available" and gh["supports_writes"] and gh["setup_steps"]
    desks = {a["desk"] for a in gh["abilities"] if a["permission"] == "read"}
    assert desks == {"code", "frontend_hosting"}
    assert [a["desk"] for a in gh["abilities"] if a["permission"] == "write"] == ["action"]
    token = next(f for f in gh["config_fields"] if f["key"] == "token")
    assert token["secret"] is True
    sb = catalog["supabase"]
    assert {a["desk"] for a in sb["abilities"]} == {"database", "observability", "backend_services"}
    assert catalog["vercel"]["status"] == "coming_soon" and catalog["vercel"]["abilities"] == []


async def test_github_form_is_validated(auth_client):
    async def post(config, secrets=None):
        return await auth_client.post("/api/connections", json={
            "type": "github", "name": "Site", "config": config, "secrets": {"token": "t"} if secrets is None else secrets})

    bad_repo = await post({"repository": "not a repo"})
    assert bad_repo.status_code == 422 and "owner/repo" in bad_repo.json()["detail"]
    assert (await post({"repository": "a/b", "allow_writes": "maybe"})).status_code == 422
    # a secret must never be sent (and stored) as plain config
    assert (await post({"repository": "a/b", "token": "t"}, secrets={})).status_code == 422
    assert (await post({"repository": "a/b", "extra": "x"})).status_code == 422
    assert (await post({"repository": "a/b"}, secrets={})).status_code == 422  # token missing


async def test_supabase_project_ref_is_validated(auth_client):
    resp = await auth_client.post("/api/connections", json={
        "type": "supabase", "name": "DB", "config": {"project_ref": "--help"}, "secrets": {"access_token": "t"}})
    assert resp.status_code == 422


async def test_tools_and_retest_for_a_connection(auth_client, tmp_path):
    created = (await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "K", "config": {"vault_path": _vault(tmp_path)}, "secrets": {}})).json()
    assert created["detail"]
    tools = (await auth_client.get(f"/api/connections/{created['id']}/tools")).json()
    assert [(t["name"], t["desk"], t["permission"]) for t in tools] == [("knowledge.search", "knowledge", "read")]

    tested = await auth_client.post(f"/api/connections/{created['id']}/test")
    assert tested.status_code == 200 and tested.json()["ok"] is True
    assert (await auth_client.get("/api/connections/con_missing/tools")).status_code == 404
    assert (await auth_client.post("/api/connections/con_missing/test")).status_code == 404


async def test_retest_records_a_broken_connection(auth_client, tmp_path):
    vault = tmp_path / "v"
    vault.mkdir()
    (vault / "a.md").write_text("# A", "utf-8")
    cid = (await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "K", "config": {"vault_path": str(vault)}, "secrets": {}})).json()["id"]
    (vault / "a.md").unlink()
    vault.rmdir()
    result = (await auth_client.post(f"/api/connections/{cid}/test")).json()
    assert result["ok"] is False
    listed = (await auth_client.get("/api/connections")).json()
    assert listed[0]["status"] == "error" and listed[0]["last_error"]


async def test_service_map_describes_connections(auth_client, app, tmp_path):
    from forgeops.connectors.factory import build_registry_for_workspace

    await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "Runbooks", "config": {"vault_path": _vault(tmp_path)}, "secrets": {}})
    ws = (await auth_client.get("/api/auth/me")).json()["workspace"]["id"]
    registry = await build_registry_for_workspace(
        app.state.session_factory, ws, app.state.secret_box, app.state.settings, app.state.embedder)
    try:
        assert "Knowledge vault" in registry.service_map and '"Runbooks"' in registry.service_map
    finally:
        await registry.aclose()


def test_describe_connection_fills_the_repository():
    from forgeops.connectors.factory import describe_connection

    row = Connection(id="con_1", workspace_id="ws", type="github", name="Site",
                     config={"repository": "acme/web", "allow_writes": False})
    assert describe_connection(row).startswith("- GitHub repository acme/web:")
