"""The connector catalog: what each connector is, how it connects, and which tools it may expose."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from forgeops.engine.models import AgentId, Capability


class ConfigField(BaseModel):
    key: str
    label: str
    secret: bool = False
    required: bool = True
    help: str = ""
    placeholder: str = ""
    boolean: bool = False  # shown as a checkbox; stored as "true"/"false"


class ToolMapping(BaseModel):
    upstream: str  # tool name exposed by the MCP server
    name: str  # ForgeOps name given to agents
    capability: Capability
    permission: Literal["read", "write"]
    description: str | None = None  # overrides the server's description when set
    # Filled from the connection (e.g. {"owner": "{owner}"}) unless the agent passes a value.
    defaults: dict[str, str] = Field(default_factory=dict)
    # Always applied, whatever the model sends (e.g. {"method": "create"}).
    fixed: dict[str, Any] = Field(default_factory=dict)


class ConnectorDefinition(BaseModel):
    type: str
    display_name: str
    description: str
    agents: list[AgentId]  # desks it appears under in the catalog
    status: Literal["available", "coming_soon"]
    transport: Literal["native", "stdio", "http"]
    command: list[str] = Field(default_factory=list)  # stdio; may contain {config_key}
    env: dict[str, str] = Field(default_factory=dict)  # stdio; values may contain {config_key}
    url: str | None = None  # http; may contain {config_key}
    headers: dict[str, str] = Field(default_factory=dict)  # http read session; values may contain {config_key}
    write_headers: dict[str, str] = Field(default_factory=dict)  # http write session (approved actions only)
    config_fields: list[ConfigField] = Field(default_factory=list)
    tools: list[ToolMapping] = Field(default_factory=list)  # allowlist
    docs_url: str | None = None
    setup_steps: list[str] = Field(default_factory=list)  # shown on the connect form
    supports_writes: bool = False


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
        placeholder="/srv/forgeops/knowledge-vault",
    )],
    setup_steps=["The folder must be inside a KNOWLEDGE_VAULT_ROOTS folder on the ForgeOps server."],
)

_REPO_DEFAULTS = {"owner": "{owner}", "repo": "{repo}"}


def _gh(upstream: str, capability: Capability, description: str, repo_scoped: bool = True) -> ToolMapping:
    return ToolMapping(upstream=upstream, name=f"github.{upstream}", capability=capability, permission="read",
                       description=description, defaults=_REPO_DEFAULTS if repo_scoped else {})


GITHUB = ConnectorDefinition(
    type="github",
    display_name="GitHub",
    description="Commits, pull requests, code, issues, releases and Actions runs from one repository.",
    agents=[AgentId.code, AgentId.frontend_hosting],
    status="available",
    transport="http",
    url="https://api.githubcopilot.com/mcp/",
    headers={
        "Authorization": "Bearer {token}",
        "X-MCP-Readonly": "true",
        "X-MCP-Toolsets": "repos,pull_requests,actions,issues",
    },
    write_headers={"Authorization": "Bearer {token}", "X-MCP-Toolsets": "issues"},
    supports_writes=True,
    docs_url="https://github.com/github/github-mcp-server",
    config_fields=[
        ConfigField(key="repository", label="Repository", placeholder="owner/repo",
                    help="The repository ForgeOps investigates."),
        ConfigField(key="token", label="Personal access token", secret=True, placeholder="github_pat_…",
                    help="A fine-grained token limited to this repository."),
        ConfigField(key="allow_writes", label="Allow creating issues after approval", boolean=True, required=False,
                    help="Needs Issues: read and write on the token. Every issue still needs your approval."),
    ],
    setup_steps=[
        "GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token.",
        "Repository access: Only select repositories → pick this repository.",
        "Permissions (read-only): Contents, Metadata, Pull requests, Actions, Issues.",
        "Optional: Issues read and write, only if you want ForgeOps to open issues after approval.",
    ],
    tools=[
        _gh("list_commits", Capability.code, "List recent commits in the repository (newest first)."),
        _gh("get_commit", Capability.code, "Show one commit with its changed files and diff."),
        _gh("get_file_contents", Capability.code, "Read a file or directory at a branch, tag or commit."),
        _gh("list_branches", Capability.code, "List the repository's branches."),
        _gh("search_code", Capability.code, "Search code with GitHub code search; include repo:owner/name in the query.",
            repo_scoped=False),
        _gh("list_pull_requests", Capability.code, "List pull requests, e.g. recently merged ones."),
        _gh("pull_request_read", Capability.code, "Read one pull request: details, diff, files, reviews or comments."),
        _gh("search_pull_requests", Capability.code, "Search pull requests; include repo:owner/name in the query.",
            repo_scoped=False),
        _gh("list_issues", Capability.code, "List issues, e.g. recently opened bug reports."),
        _gh("issue_read", Capability.code, "Read one issue with its comments."),
        _gh("search_issues", Capability.code, "Search issues; include repo:owner/name in the query.", repo_scoped=False),
        _gh("list_releases", Capability.hosting, "List releases and their dates."),
        _gh("actions_list", Capability.hosting, "List workflows, workflow runs and their jobs (deploys and CI)."),
        _gh("actions_get", Capability.hosting, "Get one workflow, run or job in detail."),
        _gh("get_job_logs", Capability.hosting, "Read the logs of a failed Actions job or run."),
        ToolMapping(upstream="issue_write", name="github.create_issue", capability=Capability.write,
                    permission="write", description="Open a GitHub issue (only after human approval).",
                    defaults=_REPO_DEFAULTS, fixed={"method": "create"}),
    ],
)


def _sb(upstream: str, capability: Capability, description: str) -> ToolMapping:
    return ToolMapping(upstream=upstream, name=f"supabase.{upstream}", capability=capability, permission="read",
                       description=description)


# Never exposed: get_publishable_keys, generate_typescript_types, search_docs, get_project_url, list_branches.
SUPABASE = ConnectorDefinition(
    type="supabase",
    display_name="Supabase",
    description="Postgres schema, migrations, read-only SQL, advisors, service logs and edge functions of one project.",
    agents=[AgentId.database, AgentId.backend_services, AgentId.observability],
    status="available",
    transport="stdio",
    command=["npx", "-y", "@supabase/mcp-server-supabase@0.13.0", "--read-only", "--project-ref={project_ref}"],
    env={"SUPABASE_ACCESS_TOKEN": "{access_token}"},
    docs_url="https://supabase.com/docs/guides/getting-started/mcp",
    config_fields=[
        ConfigField(key="project_ref", label="Project ref", placeholder="abcdefghijklmnopqrst",
                    help="Project Settings → General → Project ID."),
        ConfigField(key="access_token", label="Access token", secret=True, placeholder="sbp_…",
                    help="A personal access token. ForgeOps runs the server in read-only mode for one project."),
    ],
    setup_steps=[
        "Supabase dashboard → Account → Access Tokens → Generate new token (name it ForgeOps).",
        "Copy the project ref from Project Settings → General.",
        "ForgeOps starts the official Supabase MCP server with --read-only and --project-ref, so SQL cannot change data.",
    ],
    tools=[
        _sb("list_tables", Capability.database, "List tables with columns, keys and row-level security status."),
        _sb("list_extensions", Capability.database, "List installed Postgres extensions."),
        _sb("list_migrations", Capability.database, "List applied migrations with versions (recent schema changes)."),
        _sb("execute_sql", Capability.database, "Run a read-only SQL query (SELECT only)."),
        _sb("get_advisors", Capability.database, "Security and performance advisor notices (missing RLS, slow indexes)."),
        _sb("query_logs", Capability.logs, "Query recent logs of a service: api, postgres, edge-function, auth, storage, realtime."),
        _sb("list_edge_functions", Capability.backend, "List deployed edge functions and their versions."),
        _sb("get_edge_function", Capability.backend, "Read the source of a deployed edge function."),
    ],
)


def _soon(type_: str, name: str, description: str, *agents: AgentId) -> ConnectorDefinition:
    return ConnectorDefinition(type=type_, display_name=name, description=description, agents=list(agents),
                               status="coming_soon", transport="http")


COMING_SOON = [
    _soon("cloudflare", "Cloudflare", "Pages and Workers deployments, analytics and logs.", AgentId.frontend_hosting,
          AgentId.observability),
    _soon("vercel", "Vercel", "Deployments, build logs and runtime logs.", AgentId.frontend_hosting),
    _soon("netlify", "Netlify", "Deploys and function logs.", AgentId.frontend_hosting),
    _soon("sanity", "Sanity", "Content schema and recent document changes.", AgentId.backend_services),
    _soon("sentry", "Sentry", "Errors, stack traces and releases.", AgentId.observability),
    _soon("gitlab", "GitLab", "Commits, merge requests and pipelines.", AgentId.code, AgentId.frontend_hosting),
    _soon("firebase", "Firebase", "Firestore, functions and hosting.", AgentId.database, AgentId.backend_services),
    _soon("mongodb", "MongoDB", "Collections, indexes and read-only queries.", AgentId.database),
    _soon("datadog", "Datadog", "Metrics, logs and monitors.", AgentId.observability),
    _soon("prometheus", "Prometheus", "Metrics and alerts.", AgentId.observability),
    _soon("notion", "Notion", "Runbooks and postmortems.", AgentId.knowledge),
    _soon("jira", "Jira", "Incidents and related tickets.", AgentId.knowledge),
    _soon("slack", "Slack", "Incident channels and alerts.", AgentId.knowledge),
]

CATALOG: dict[str, ConnectorDefinition] = {d.type: d for d in (KNOWLEDGE, GITHUB, SUPABASE, *COMING_SOON)}
