from forgeops.connectors.knowledge import KnowledgeConnector
from forgeops.engine.models import Capability
from forgeops.knowledge.index import KnowledgeIndex
from tests.engine.fakes import HashEmbedder


def _vault(tmp_path):
    vault = tmp_path / "vault"
    (vault / "Runbooks").mkdir(parents=True)
    (vault / ".obsidian").mkdir()
    (vault / "Runbooks" / "db.md").write_text("# DB\nPool exhausted: raise pool size to 40.", "utf-8")
    (vault / ".obsidian" / "workspace.md").write_text("# ignore me", "utf-8")
    return vault


async def test_search_tool_returns_cited_hits(tmp_path):
    conn = KnowledgeConnector("con_kv", _vault(tmp_path),
                              KnowledgeIndex(tmp_path / "idx", "con_kv", HashEmbedder()))
    tools = await conn.list_tools()
    assert [(t.name, t.capability, t.permission) for t in tools] == [
        ("knowledge.search", Capability.knowledge, "read")]
    result = await conn.call("knowledge.search", {"query": "pool exhausted"})
    assert result.ok and "Runbooks/db.md" in result.content and "raise pool size" in result.content
    assert "workspace.md" not in result.content
    assert result.data[0]["source"] == "Runbooks/db.md"


async def test_health_check_explains_missing_vault(tmp_path):
    conn = KnowledgeConnector("con_kv", tmp_path / "nope",
                              KnowledgeIndex(tmp_path / "idx", "con_kv", HashEmbedder()))
    health = await conn.health_check()
    assert not health.ok and "not found" in health.detail


async def test_health_check_counts_documents(tmp_path):
    conn = KnowledgeConnector("con_kv", _vault(tmp_path),
                              KnowledgeIndex(tmp_path / "idx", "con_kv", HashEmbedder()))
    health = await conn.health_check()
    assert health.ok and "1 document" in health.detail
