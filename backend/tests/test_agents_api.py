async def test_agents_lists_every_desk_with_its_connectors(auth_client, tmp_path):
    (tmp_path / "a.md").write_text("# A\nhello", "utf-8")
    await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "Runbooks", "config": {"vault_path": str(tmp_path)}, "secrets": {}})
    await auth_client.post("/api/connections", json={
        "type": "knowledge", "name": "Broken", "config": {"vault_path": str(tmp_path / "missing")},
        "secrets": {}})

    agents = (await auth_client.get("/api/agents")).json()
    assert [a["id"] for a in agents] == [
        "supervisor", "code", "frontend_hosting", "backend_services", "database",
        "observability", "knowledge", "rca", "action"]
    knowledge = next(a for a in agents if a["id"] == "knowledge")
    assert knowledge["title"] == "Knowledge" and knowledge["connected"] is True
    assert knowledge["capabilities"] == ["knowledge"]
    assert [c["name"] for c in knowledge["connectors"]] == ["Runbooks"]  # error rows are not counted
    code = next(a for a in agents if a["id"] == "code")
    assert code["connected"] is False and code["connectors"] == []
    supervisor = next(a for a in agents if a["id"] == "supervisor")
    assert supervisor["specialist"] is False


async def test_agents_requires_login(client):
    assert (await client.get("/api/agents")).status_code == 401
