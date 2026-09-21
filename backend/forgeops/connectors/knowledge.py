"""Native connector: search an Obsidian vault / Markdown folder owned by the customer."""

import asyncio
from pathlib import Path
from typing import Any

from forgeops.capabilities.models import HealthStatus, ToolResult, ToolSpec
from forgeops.engine.models import Capability
from forgeops.knowledge.chunking import chunk_markdown
from forgeops.knowledge.index import KnowledgeIndex

_SKIP_DIRS = {".obsidian", ".trash", ".git", "node_modules"}


def resolve_vault_path(raw: str, allowed_roots: list[str]) -> Path:
    """Resolve a vault path (following symlinks) and require it to be inside an allowed root."""
    resolved = Path(raw).expanduser().resolve()
    for root in allowed_roots:
        if resolved.is_relative_to(Path(root).expanduser().resolve()):
            return resolved
    raise ValueError(
        "The vault folder must be inside one of the allowed folders set by the server operator "
        "(KNOWLEDGE_VAULT_ROOTS in .env)"
    )


SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "What to look for, in plain words."},
        "limit": {"type": "integer", "minimum": 1, "maximum": 8, "default": 5},
    },
    "required": ["query"],
}


class KnowledgeConnector:
    connector_type = "knowledge"

    def __init__(self, connection_id: str, vault_path: Path, index: KnowledgeIndex):
        self.connection_id = connection_id
        self._vault = Path(vault_path)
        self._index = index

    def _documents(self) -> list[Path]:
        if not self._vault.is_dir():
            return []
        return sorted(
            p for p in self._vault.rglob("*.md")
            if not any(part in _SKIP_DIRS for part in p.relative_to(self._vault).parts)
        )

    def _reindex_sync(self) -> int:
        chunks = []
        for path in self._documents():
            source = path.relative_to(self._vault).as_posix()
            chunks.extend(chunk_markdown(path.read_text(encoding="utf-8", errors="replace"), source))
        self._index.replace(chunks)
        return len(chunks)

    async def reindex(self) -> int:
        return await asyncio.to_thread(self._reindex_sync)

    async def _ensure_indexed(self) -> None:
        if self._index.count() == 0:
            await self.reindex()

    async def health_check(self) -> HealthStatus:
        if not self._vault.is_dir():
            return HealthStatus(ok=False, detail=f"Vault folder not found: {self._vault}")
        count = len(self._documents())
        if count == 0:
            return HealthStatus(ok=False, detail=f"No Markdown (.md) files found in {self._vault}")
        return HealthStatus(ok=True, detail=f"{count} document{'s' if count != 1 else ''} found")

    async def list_tools(self) -> list[ToolSpec]:
        await self._ensure_indexed()
        return [ToolSpec(
            name="knowledge.search",
            description="Search the team's runbooks, architecture notes and past incident write-ups. "
                        "Returns matching passages with their file and heading.",
            capability=Capability.knowledge, permission="read", input_schema=SEARCH_SCHEMA,
            connection_id=self.connection_id, connector_type=self.connector_type,
        )]

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        if tool_name != "knowledge.search":
            return ToolResult(ok=False, error=f"{tool_name} is not an allowed tool for knowledge")
        query = str(arguments.get("query", "")).strip()
        if not query:
            return ToolResult(ok=False, error="query is required")
        limit = max(1, min(int(arguments.get("limit", 5)), 8))
        await self._ensure_indexed()
        hits = await asyncio.to_thread(self._index.search, query, limit)
        if not hits:
            return ToolResult(ok=True, content="No matching documents in the knowledge vault.", data=[])
        content = "\n\n".join(f"### {h.chunk.source} — {h.chunk.heading}\n{h.chunk.text}" for h in hits)
        data = [{"source": h.chunk.source, "heading": h.chunk.heading, "score": h.score} for h in hits]
        return ToolResult(ok=True, content=content, data=data)

    async def aclose(self) -> None:
        return None
