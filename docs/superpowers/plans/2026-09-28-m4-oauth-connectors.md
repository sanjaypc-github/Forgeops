# M4 Connectors: OAuth, then Cloudflare and Sanity

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Connect the rest of the customer's stack. Verified on 2026-09-28, the two connectors M4 needs have
moved to OAuth, so ForgeOps needs an OAuth connect flow before it can have them.

## What the research found (2026-09-28)

| Server | Endpoint | Auth | Consequence for ForgeOps |
|---|---|---|---|
| Cloudflare API MCP | `https://mcp.cloudflare.com/mcp` | OAuth, **or** a Cloudflare API token as `Authorization: Bearer` (documented for CI/CD) | Token path works today, but the server ships "Code Mode": only `search` and `execute` tools, and `execute` can call **any** Cloudflare endpoint, including writes. `?codemode=false` registers each endpoint as its own tool, which suits our allowlist. |
| Sanity | `https://mcp.sanity.io` | OAuth | The local `@sanity/mcp-server` is **deprecated**; the org-token path (`https://api.sanity.io/v1/context/organizations/<org>/mcp/<endpoint>`) needs an endpoint created in the Sanity dashboard and exposes only `initial_context` + `groq_query`. |
| Sentry, Vercel, Notion, Linear | remote MCP | OAuth | Same blocker; OAuth unlocks all of them at once. |

Building two bespoke token workarounds would be thrown away as soon as OAuth exists, so OAuth comes first.

## Tasks

1. **OAuth client** (`forgeops/connectors/oauth.py`), pure and offline-testable:
   discovery (RFC 9728 protected resource → RFC 8414 authorization server metadata, with the OpenID
   fallback), dynamic client registration (RFC 7591), PKCE (S256) authorize URL, code exchange, refresh.
   Tests use `httpx2.MockTransport`; nothing leaves the machine.
2. **Connection storage and API**: `auth: "token" | "oauth"` on the definition; `POST /connections/{id}/authorize`
   returns the consent URL; `GET /api/connections/oauth/callback` completes it; tokens encrypted in the
   existing secret box; refresh before expiry; the pending verifier is kept server-side, keyed by state.
3. **McpConnector**: an OAuth connection injects `Authorization: Bearer <access token>`, refreshing when
   the token is near expiry, and reports "reconnect needed" when the refresh fails.
4. **Cloudflare connector**: `https://mcp.cloudflare.com/mcp?codemode=false`, read tools allowlisted for
   the Frontend & Hosting and Observability desks. Exact upstream names are pinned only after listing them
   against a real account, the way GitHub and Supabase were.
5. **Sanity connector**: OAuth against `https://mcp.sanity.io`, read tools for the Backend & Services desk.
6. **Connectors page**: a "Connect with OAuth" button, the consent window, and a clear reconnect state.
7. **Live check** with the owner's Cloudflare account and Sanity project.

## Constraints kept from M3

- Allowlist only; a tool the server does not offer is reported by the health check, never faked.
- Investigating agents get read tools only; writes need an opted-in connection and human approval.
- Secrets, including OAuth tokens, never leave the backend.
- No runtime mock data.
