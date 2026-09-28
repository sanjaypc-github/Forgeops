"""Turn stored connection rows into live connectors and a per-investigation registry."""

from pathlib import Path

from sqlalchemy import select

from forgeops.capabilities.models import Connector
from forgeops.capabilities.registry import CapabilityRegistry
from forgeops.config import Settings
from forgeops.connectors.definitions import CATALOG
from forgeops.connectors.knowledge import KnowledgeConnector, resolve_vault_path
from forgeops.connectors.mcp import McpConnector
from forgeops.connectors.tokens import OAuthSession, TokenProvider
from forgeops.db.models import Connection
from forgeops.db.session import SessionFactory
from forgeops.knowledge.index import EmbedFn, KnowledgeIndex
from forgeops.security.crypto import SecretBox


def describe_connection(row: Connection) -> str:
    """The definition's context line with the connection's (non-secret) values, e.g. the repository."""
    definition = CATALOG.get(row.type)
    if definition is None or not definition.context:
        return ""
    try:
        line = definition.context.format_map({k: str(v) for k, v in row.config.items()})
    except (KeyError, ValueError):
        line = definition.display_name
    return f"- {line} (connection \"{row.name}\")"


OAUTH_KEY = "oauth"  # where an OAuth session lives inside a connection's encrypted secrets


def build_connector(row: Connection, secret_box: SecretBox, settings: Settings, embed: EmbedFn,
                    session_factory: SessionFactory | None = None) -> Connector:
    definition = CATALOG.get(row.type)
    if definition is None:
        raise ValueError(f"Unknown connector type {row.type!r}")
    secrets = secret_box.decrypt_json(row.secret_encrypted) if row.secret_encrypted else {}
    if definition.type == "knowledge":
        index = KnowledgeIndex(Path(settings.knowledge_data_dir), f"kv_{row.id}", embed)
        vault = resolve_vault_path(row.config["vault_path"], settings.knowledge_vault_roots)
        return KnowledgeConnector(row.id, vault, index)
    if definition.transport in ("stdio", "http"):
        token = None
        if definition.auth == "oauth":
            token = _token_provider(row, secrets, secret_box, session_factory)
        return McpConnector(definition, row.id, row.config, secrets, access_token=token)
    raise ValueError(f"No connector implementation for {row.type!r}")


def _token_provider(row: Connection, secrets: dict, secret_box: SecretBox,
                    session_factory: SessionFactory | None) -> TokenProvider:
    stored = secrets.get(OAUTH_KEY)
    if not stored:
        raise ValueError(f"{row.name} is not connected yet; open the Connectors page and connect it")
    session = OAuthSession.model_validate(stored)

    async def save(updated: OAuthSession) -> None:
        """Persist a refreshed token immediately: providers may rotate the refresh token."""
        if session_factory is None:
            return
        async with session_factory() as db:
            current = await db.get(Connection, row.id)
            if current is None:
                return
            secrets_now = secret_box.decrypt_json(current.secret_encrypted) if current.secret_encrypted else {}
            secrets_now[OAUTH_KEY] = updated.dump()
            current.secret_encrypted = secret_box.encrypt_json(secrets_now)
            await db.commit()

    return TokenProvider(session, save, connection_id=row.id)


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
    connectors: list[Connector] = []
    warnings: list[str] = []
    lines: list[str] = []
    for row in rows:
        try:
            connectors.append(build_connector(row, secret_box, settings, embed, session_factory))
            lines.append(describe_connection(row))
        except Exception as exc:  # noqa: BLE001 - one bad connection must not block the others
            warnings.append(f"{row.type} ({row.id}) unavailable: {exc}")
    registry = await CapabilityRegistry.build(connectors, warnings)
    registry.service_map = "\n".join(line for line in lines if line)
    return registry
