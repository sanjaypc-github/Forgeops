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
    assert available == {"knowledge", "github", "supabase"}
    soon = {t for t, d in CATALOG.items() if d.status == "coming_soon"}
    assert {"cloudflare", "vercel", "netlify", "sanity", "sentry"} <= soon


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
