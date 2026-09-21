from forgeops.knowledge.chunking import Chunk
from forgeops.knowledge.index import KnowledgeIndex
from tests.engine.fakes import HashEmbedder

CHUNKS = [
    Chunk(id="1", source="db.md", heading="Pool", text="connection pool exhausted timeouts raise pool size"),
    Chunk(id="2", source="cdn.md", heading="Cache", text="cloudflare cache purge after deploy stale assets"),
    Chunk(id="3", source="auth.md", heading="Login", text="supabase auth jwt expired login loop"),
]


def test_hybrid_search_ranks_relevant_chunk_first(tmp_path):
    index = KnowledgeIndex(tmp_path, "kv_test", HashEmbedder())
    index.replace(CHUNKS)
    assert index.count() == 3
    hits = index.search("pool timeouts", k=2)
    assert hits[0].chunk.source == "db.md" and len(hits) == 2


def test_index_persists_and_replace_is_idempotent(tmp_path):
    KnowledgeIndex(tmp_path, "kv_test", HashEmbedder()).replace(CHUNKS)
    reopened = KnowledgeIndex(tmp_path, "kv_test", HashEmbedder())
    assert reopened.count() == 3
    reopened.replace(CHUNKS[:1])
    assert reopened.count() == 1
    assert reopened.search("cloudflare cache")[0].chunk.source == "db.md"  # only one left


def test_empty_index_returns_no_hits(tmp_path):
    assert KnowledgeIndex(tmp_path, "empty", HashEmbedder()).search("anything") == []
