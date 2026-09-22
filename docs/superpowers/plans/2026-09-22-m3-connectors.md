# M3 Connectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** One Connectors page where a user connects the tools their product runs on; each connection is tested, shows its read/write abilities, and powers the right desks. First real connectors: **GitHub** (official remote MCP server) and **Supabase** (official MCP server, read-only). Everything else is listed as "coming soon".

**Verified against the real servers (2026-09-22):**
- GitHub remote MCP: `https://api.githubcopilot.com/mcp/`, `Authorization: Bearer <PAT>`, `X-MCP-Readonly: true`, `X-MCP-Toolsets: repos,pull_requests,actions,issues`. Current consolidated tool names: `list_commits`, `get_commit`, `get_file_contents`, `list_branches`, `search_code`, `list_releases`, `list_pull_requests`, `pull_request_read`, `search_pull_requests`, `actions_list`, `actions_get`, `get_job_logs`, `list_issues`, `issue_read`, `search_issues`, `issue_write` (write).
- Supabase MCP (`npx -y @supabase/mcp-server-supabase@latest --read-only --project-ref=<ref>`, `SUPABASE_ACCESS_TOKEN`): `list_tables`, `list_extensions`, `list_migrations`, `execute_sql`, `query_logs`, `get_advisors(type: security|performance)`, `list_edge_functions`, `get_edge_function`, plus tools deliberately not exposed (`get_publishable_keys`, `generate_typescript_types`, `list_branches`, `search_docs`, `get_project_url`).

## Global constraints
- Allowlist only: unmapped upstream tools are never exposed. A mapped tool the server does not offer is reported in the health check, never faked.
- Investigating agents get read tools only. Write tools (GitHub `issue_write` as `github.create_issue`) exist only when the connection opts in to writes, open a separate non-read-only session only when the Action agent calls them, and only after approval.
- Connection-level defaults (e.g. `owner`/`repo`, `project_ref`) are injected into tool calls so agents look in the right place; "fixed" arguments (e.g. `method: create`) can never be overridden by the model.
- Secrets never leave the backend.

## Tasks
1. **MCP connector upgrades**: HTTP transport with header templates; `ToolMapping.defaults` and `ToolMapping.fixed`; separate write session; health check lists allowlisted tools the server does not offer. Tests with the local test server over stdio and streamable HTTP.
2. **Catalog**: GitHub and Supabase definitions; coming-soon entries for Cloudflare, Vercel, Netlify, GitLab, Sanity, Sentry, Datadog, Prometheus/Grafana, Firebase, MongoDB Atlas, Notion, Jira, Slack. Tests pin the verified tool names and desk routing.
3. **API**: `GET /connections/{id}/tools` (abilities with desk and read/write), `POST /connections/{id}/test`; connection context ("GitHub repository owner/repo") passed to the Supervisor and specialists as the service map. Tests.
4. **Connectors page**: catalog grouped by desk, connect form built from each connector's fields (secrets masked), test result with abilities per desk, re-test and disconnect; desks in the War Room show their tools. Tests.
5. **Live check** with the owner's tokens entered on the page; live investigation run.
