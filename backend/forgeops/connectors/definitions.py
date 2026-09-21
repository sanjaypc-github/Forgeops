"""The connector catalog: what each connector is, how it connects, and which tools it may expose."""

from typing import Literal

from pydantic import BaseModel, Field

from forgeops.engine.models import AgentId, Capability


class ConfigField(BaseModel):
    key: str
    label: str
    secret: bool = False
    required: bool = True
    help: str = ""


class ToolMapping(BaseModel):
    upstream: str  # tool name exposed by the MCP server
    name: str  # ForgeOps name given to agents
    capability: Capability
    permission: Literal["read", "write"]


class ConnectorDefinition(BaseModel):
    type: str
    display_name: str
    description: str
    agents: list[AgentId]  # desks it appears under in the catalog
    status: Literal["available", "coming_soon"]
    transport: Literal["native", "stdio", "http"]
    command: list[str] = Field(default_factory=list)  # stdio; may contain {config_key}
    env: dict[str, str] = Field(default_factory=dict)  # stdio; values may contain {config_key}
    url: str | None = None  # http
    config_fields: list[ConfigField] = Field(default_factory=list)
    tools: list[ToolMapping] = Field(default_factory=list)  # allowlist
    docs_url: str | None = None


KNOWLEDGE = ConnectorDefinition(
    type="knowledge",
    display_name="Knowledge vault",
    description="Obsidian vault or any folder of Markdown runbooks and docs, searched by ForgeOps.",
    agents=[AgentId.knowledge],
    status="available",
    transport="native",
    config_fields=[ConfigField(
        key="vault_path", label="Vault folder",
        help="Absolute path to the Obsidian vault or Markdown folder on the ForgeOps server.",
    )],
)

CATALOG: dict[str, ConnectorDefinition] = {d.type: d for d in (KNOWLEDGE,)}
