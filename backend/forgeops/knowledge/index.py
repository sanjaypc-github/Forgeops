"""Hybrid search (vector + BM25, reciprocal-rank fusion) over knowledge chunks."""

import re
from collections.abc import Callable
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from pydantic import BaseModel
from rank_bm25 import BM25Okapi

from forgeops.knowledge.chunking import Chunk

EmbedFn = Callable[[list[str]], list[list[float]]]
RRF_K = 60
_TOKEN = re.compile(r"\w+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def default_embedder() -> EmbedFn:
    """Chroma's bundled MiniLM ONNX model (downloaded once, runs locally)."""
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    model = DefaultEmbeddingFunction()

    def embed(texts: list[str]) -> list[list[float]]:
        return [list(map(float, vector)) for vector in model(texts)]

    return embed


class SearchHit(BaseModel):
    chunk: Chunk
    score: float


class KnowledgeIndex:
    def __init__(self, data_dir: Path, name: str, embed: EmbedFn):
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(data_dir), settings=ChromaSettings(anonymized_telemetry=False)
        )
        self._name = name
        self._embed = embed
        self._collection = self._client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
        self._load_bm25()

    def _load_bm25(self) -> None:
        stored = self._collection.get(include=["documents", "metadatas"])
        self._chunks = [
            Chunk(id=cid, source=meta["source"], heading=meta["heading"], text=doc)
            for cid, doc, meta in zip(stored["ids"], stored["documents"], stored["metadatas"], strict=True)
        ]
        self._bm25 = BM25Okapi([_tokens(c.text + " " + c.heading) for c in self._chunks]) if self._chunks else None

    def replace(self, chunks: list[Chunk]) -> None:
        self._client.delete_collection(self._name)
        self._collection = self._client.get_or_create_collection(self._name, metadata={"hnsw:space": "cosine"})
        if chunks:
            self._collection.add(
                ids=[c.id for c in chunks],
                documents=[c.text for c in chunks],
                embeddings=self._embed([f"{c.heading}\n{c.text}" for c in chunks]),
                metadatas=[{"source": c.source, "heading": c.heading} for c in chunks],
            )
        self._load_bm25()

    def count(self) -> int:
        return len(self._chunks)

    def search(self, query: str, k: int = 5) -> list[SearchHit]:
        if not self._chunks:
            return []
        pool = min(len(self._chunks), max(k * 4, 20))
        vector = self._collection.query(query_embeddings=self._embed([query]), n_results=pool)
        vector_ranking = vector["ids"][0]
        scores = self._bm25.get_scores(_tokens(query))
        bm25_ranking = [self._chunks[i].id for i in sorted(range(len(scores)), key=lambda i: -scores[i])
                        if scores[i] > 0][:pool]

        fused: dict[str, float] = {}
        for ranking in (vector_ranking, bm25_ranking):
            for rank, chunk_id in enumerate(ranking):
                fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
        by_id = {c.id: c for c in self._chunks}
        best = sorted(fused.items(), key=lambda item: -item[1])[:k]
        return [SearchHit(chunk=by_id[cid], score=round(score, 5)) for cid, score in best]
