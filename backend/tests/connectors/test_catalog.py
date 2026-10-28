from pathlib import Path

from forgeops.capabilities.routing import agent_for_capability
from forgeops.connectors.definitions import CATALOG
from forgeops.engine.models import AgentId, Capability

# Tool names verified against the real servers on 2026-09-22 (see the M3 plan).
GITHUB_UPSTREAM = {
    "list_commits", "get_commit", "get_file_contents", "list_branches", "search_code", "list_releases",
    "list_pull_requests", "pull_request_read", "search_pull_requests", "actions_list", "actions_get",
    "get_job_logs", "list_issues", "issue_read", "search_issues", "issue_write",
}
SUPABASE_UPSTREAM = {
    "list_tables", "list_extensions", "list_migrations", "execute_sql", "query_logs", "get_advisors",
    "list_edge_functions", "get_edge_function",
}
SUPABASE_NEVER = {"get_publishable_keys", "generate_typescript_types", "search_docs", "get_project_url"}


def test_available_connectors_and_coming_soon():
    available = {t for t, d in CATALOG.items() if d.status == "available"}
    assert available == {"knowledge", "github", "supabase", "cloudflare"}
    soon = {t for t, d in CATALOG.items() if d.status == "coming_soon"}
    assert {"vercel", "netlify", "sanity", "sentry"} <= soon


def test_cloudflare_disables_code_mode_and_stays_read_only():
    """Code Mode exposes only `search` and `execute`, and `execute` can call any Cloudflare API."""
    cf = CATALOG["cloudflare"]
    assert cf.transport == "http" and cf.url == "https://mcp.cloudflare.com/mcp?codemode=false"
    assert "codemode=false" in cf.url, "without this the agent gets an unrestricted execute tool"
    assert all(m.permission == "read" for m in cf.tools)
    assert cf.supports_writes is False and cf.write_headers == {}
    assert {agent_for_capability(m.capability) for m in cf.tools} == {
        AgentId.frontend_hosting, AgentId.observability}
    assert any("read" in step.lower() for step in cf.setup_steps)


def test_cloudflare_authenticates_with_oauth_not_an_api_token():
    """Verified against the live server on 2026-10-28.

    An unauthenticated POST to the endpoint answers 401 with
    `WWW-Authenticate: Bearer realm="OAuth", scope="user:read account:read"` and a
    resource_metadata pointer, and the authorization server advertises a
    registration_endpoint. A Cloudflare API token is a different credential and is
    always rejected, so this connector must never ask the customer for one.
    """
    cf = CATALOG["cloudflare"]
    assert cf.auth == "oauth"
    # the credential still travels as a bearer header; it is just minted by Cloudflare
    # rather than pasted by the customer, so the placeholder is {access_token}
    assert cf.headers == {"Authorization": "Bearer {access_token}"}
    assert "{api_token}" not in str(cf.headers), "an API token is rejected by this server"
    assert cf.write_headers == {}
    assert [f.key for f in cf.config_fields if f.secret] == []
    assert set(cf.oauth_scopes) == {"account:read", "user:read", "offline_access"}
    assert not any("write" in scope for scope in cf.oauth_scopes)


def test_cloudflare_tool_names_are_the_ones_the_server_offers():
    """Pinned from a live listing on 2026-10-28 (devtools.mcp_tools).

    With codemode=false the server names one tool per REST endpoint, so every upstream
    name is a get_* path. A name that is not a get_* is either invented or a write.
    """
    cf = CATALOG["cloudflare"]
    upstream = {m.upstream for m in cf.tools}
    assert upstream == {
        "get_accounts_workers_scripts",
        "get_accounts_workers_scripts_by_script_name",
        "get_accounts_workers_scripts_deployments",
        "get_accounts_workers_scripts_versions",
        "get_accounts_builds_workers_builds",
        "get_accounts_builds_builds_by_build_uuid",
        "get_accounts_builds_builds_logs",
        "get_accounts_workers_observability_issues",
        "get_accounts_workers_observability_issues_summary",
        "get_accounts_pages_projects",
        "get_accounts_pages_projects_deployments",
        "get_accounts_pages_projects_deployments_history_logs",
    }
    assert all(name.startswith("get_") for name in upstream), "only read endpoints belong here"
    source = Path(__file__).resolve().parents[2] / "forgeops" / "connectors" / "definitions.py"
    assert "UNVERIFIED TOOL NAMES" not in source.read_text(encoding="utf-8")


def test_cloudflare_covers_workers_builds_not_only_pages():
    """A Vite build on Workers Static Assets deploys through Workers Builds.

    Allowlisting only the Pages endpoints would send the Hosting desk to the wrong
    product and it would find nothing about the site under investigation.
    """
    cf = CATALOG["cloudflare"]
    upstream = {m.upstream for m in cf.tools}
    assert any("builds_logs" in name for name in upstream), "no build logs for a Worker"
    assert any("workers_scripts_deployments" in name for name in upstream)


def test_cloudflare_pins_the_account_and_the_model_cannot_change_it():
    """`fixed`, never `defaults`: a default is overwritten by the model's own arguments.

    The OAuth grant reaches every account the customer belongs to, so an account_id the
    model could set would let a desk read an account this connection is not for.
    """
    cf = CATALOG["cloudflare"]
    assert all(m.fixed == {"account_id": "{account_id}"} for m in cf.tools)
    assert all("account_id" not in m.defaults for m in cf.tools)


def test_oauth_connectors_actually_send_the_token_they_obtain():
    """An OAuth connector with no {access_token} placeholder authenticates with nothing.

    The token provider fills the placeholder into the headers at call time. A definition
    that declares no header sends the request bare, and the approval the customer just
    granted is silently thrown away.
    """
    for definition in CATALOG.values():
        if definition.auth != "oauth":
            continue
        headers = " ".join(definition.headers.values())
        assert "{access_token}" in headers, f"{definition.type} obtains a token it never sends"


def test_every_tool_routes_to_a_desk_the_connector_lists():
    for definition in CATALOG.values():
        names = [m.name for m in definition.tools]
        assert len(names) == len(set(names)), definition.type
        for mapping in definition.tools:
            desk = agent_for_capability(mapping.capability)
            assert desk in definition.agents or desk == AgentId.action, (definition.type, mapping.name)
            assert (mapping.permission == "write") == (mapping.capability == Capability.write)


def test_github_uses_the_official_remote_server_read_only_with_scoped_toolsets():
    gh = CATALOG["github"]
    assert gh.transport == "http" and gh.url == "https://api.githubcopilot.com/mcp/"
    assert gh.headers["Authorization"] == "Bearer {token}"
    assert gh.headers["X-MCP-Readonly"] == "true"
    assert gh.headers["X-MCP-Toolsets"] == "repos,pull_requests,actions,issues"
    assert "X-MCP-Readonly" not in gh.write_headers
    assert {m.upstream for m in gh.tools} <= GITHUB_UPSTREAM
    writes = [m for m in gh.tools if m.permission == "write"]
    assert [(m.name, m.upstream, m.fixed) for m in writes] == [("github.create_issue", "issue_write", {"method": "create"})]
    commits = next(m for m in gh.tools if m.upstream == "list_commits")
    assert commits.defaults == {"owner": "{owner}", "repo": "{repo}"}
    assert {agent_for_capability(m.capability) for m in gh.tools if m.permission == "read"} == {
        AgentId.code, AgentId.frontend_hosting}


def test_supabase_is_read_only_pinned_and_never_exposes_keys():
    sb = CATALOG["supabase"]
    assert sb.transport == "stdio"
    assert "--read-only" in sb.command and "--project-ref={project_ref}" in sb.command
    assert any(part.startswith("@supabase/mcp-server-supabase@0.") for part in sb.command)  # pinned version
    assert sb.env == {"SUPABASE_ACCESS_TOKEN": "{access_token}"}
    upstream = {m.upstream for m in sb.tools}
    assert upstream == SUPABASE_UPSTREAM and not upstream & SUPABASE_NEVER
    assert all(m.permission == "read" for m in sb.tools)
    desks = {m.upstream: agent_for_capability(m.capability) for m in sb.tools}
    assert desks["execute_sql"] == AgentId.database
    assert desks["query_logs"] == AgentId.observability
    assert desks["list_edge_functions"] == AgentId.backend_services


def test_secret_fields_are_marked_secret():
    assert [f.key for f in CATALOG["github"].config_fields if f.secret] == ["token"]
    assert [f.key for f in CATALOG["supabase"].config_fields if f.secret] == ["access_token"]
