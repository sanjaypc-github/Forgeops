"""Turn stored connection rows into live connectors and a per-investigation registry."""

from pathlib import Path

from sqlalchemy import select

from forgeops.capabilities.models import Connector
from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.config import Settings
from forgeops.connectors.definitions import CATALOG
from forgeops.connectors.knowledge import KnowledgeConnector
from forgeops.connectors.mcp import McpConnector
from forgeops.db.models import Connection
from forgeops.db.session import SessionFactory
from forgeops.knowledge.index import EmbedFn, KnowledgeIndex
from forgeops.security.crypto import SecretBox


def build_connector(row: Connection, secret_box: SecretBox, settings: Settings, embed: EmbedFn) -> Connector:
    definition = CATALOG.get(row.type)
    if definition is None:
        raise ValueError(f"Unknown connector type {row.type!r}")
    secrets = secret_box.decrypt_json(row.secret_encrypted) if row.secret_encrypted else {}
    if definition.type == "knowledge":
        index = KnowledgeIndex(Path(settings.knowledge_data_dir), f"kv_{row.id}", embed)
        return KnowledgeConnector(row.id, Path(row.config["vault_path"]), index)
    if definition.transport in ("stdio", "http"):
        return McpConnector(definition, row.id, row.config, secrets)
    raise ValueError(f"No connector implementation for {row.type!r}")


async def build_registry_for_workspace(
    session_factory: SessionFactory,
    workspace_id: str,
    secret_box: SecretBox,
    settings: Settings,
    embed: EmbedFn,
) -> CapabilityRegistry:
    async with session_factory() as session:
        rows = list(await session.scalars(
            select(Connection)
            .where(Connection.workspace_id == workspace_id, Connection.status == "connected")
            .order_by(Connection.created_at)
        ))
    connectors = [build_connector(row, secret_box, settings, embed) for row in rows]
    return await CapabilityRegistry.build(connectors)
