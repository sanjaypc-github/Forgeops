# 07 — API reference

Feeds the report's **implementation chapter and appendix**. All 21 endpoints, generated from the
running application's OpenAPI schema and verified against the route handlers.

Base URL in development: `http://localhost:8000`. Every path is prefixed with `/api`.

---

## 7.1 Conventions

| Aspect | Rule |
|---|---|
| Authentication | Session cookie issued by `POST /api/auth/login` |
| CSRF | Unsafe methods (POST, DELETE) require the `X-CSRF-Token` header matching the session's token |
| Scoping | Every resource is scoped to the caller's workspace; another workspace's id returns 404, never 403 with detail |
| Errors | FastAPI shape `{"detail": "…"}` with a human-readable sentence |
| Secrets | No endpoint ever returns a connector token or an OAuth token |

## 7.2 Endpoint summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness and database check |
| POST | `/api/auth/login` | Sign in; sets the session cookie, returns the CSRF token |
| POST | `/api/auth/logout` | Invalidate the session |
| GET | `/api/auth/me` | Current user and workspace |
| GET | `/api/agents` | Desk roster with connected capabilities |
| POST | `/api/chat` | Send a chat message; starts or annotates an investigation |
| GET | `/api/investigations` | List investigations (newest first) |
| POST | `/api/investigations` | Start an investigation from a description |
| GET | `/api/investigations/{id}` | Investigation with its collected detail |
| GET | `/api/investigations/{id}/events` | **SSE stream**, replayable with `Last-Event-ID` |
| POST | `/api/investigations/{id}/decision` | Approve, reject, or ask for more investigation |
| GET | `/api/investigations/{id}/report` | Final Markdown report |
| GET | `/api/investigations/{id}/chat` | Chat history for that investigation |
| GET | `/api/connectors/catalog` | The connector catalog with abilities per desk |
| GET | `/api/connections` | Connected tools in this workspace |
| POST | `/api/connections` | Connect a tool with a token; health-checks immediately |
| GET | `/api/connections/{id}/tools` | Abilities this connection currently offers |
| POST | `/api/connections/{id}/test` | Re-run the health check |
| DELETE | `/api/connections/{id}` | Disconnect |
| POST | `/api/connections/oauth/start` | Begin an OAuth consent; returns the provider URL |
| GET | `/api/connections/oauth/callback` | Provider callback; exchanges the code and stores the session |

## 7.3 Selected endpoints in detail

### `POST /api/auth/login`
```jsonc
// request
{ "email": "admin@example.com", "password": "…" }
// response 200
{ "user": {"id": "usr_…", "email": "…"},
  "workspace": {"id": "ws_…", "name": "My workspace"},
  "csrf_token": "…" }
```
Sets an `HttpOnly` session cookie. The CSRF token must accompany later unsafe requests.

### `POST /api/chat`
```jsonc
// request
{ "text": "checkout is slow since the morning deploy", "investigation_id": null }
// response 201
{ "investigation_id": "inv_…", "status": "running" }
```
With `investigation_id` omitted, a new investigation starts. With it supplied, the message is added
as a note that the Supervisor sees in the next round.

### `GET /api/investigations/{id}/events` — Server-Sent Events
```
event: message
id: 17
data: {"seq":17,"type":"tool_called","agent":"database","ts":"…",
       "data":{"call_id":"tc_…","tool":"supabase.execute_sql","summary":"{\"query\":\"…\"}"}}
```
The browser reconnects with `Last-Event-ID: 17` and receives everything after sequence 17, including
events stored after the investigation finished. This is what makes the War Room refresh-safe.

### `POST /api/investigations/{id}/decision`
```jsonc
// request
{ "kind": "approve", "approved_recommendation_ids": ["rec_1"], "note": "go ahead" }
// response 200
{ "status": "acting" }
```
`kind` is `approve`, `reject` or `investigate_more`. Approval resumes the paused LangGraph run from
its checkpoint. Only the listed recommendation ids are executed.

### `GET /api/connectors/catalog`
Returns every catalog entry with: type, display name, description, the desks it serves, status
(`available` or `coming_soon`), authentication mode (`token` or `oauth`), configuration fields
(with `secret`, `required`, `placeholder`, `pattern`, `boolean` flags), setup steps, and the
**abilities** it would grant, each tagged with its desk and read/write permission.

### `POST /api/connections`
```jsonc
// request
{ "type": "github", "name": "Website repo",
  "config": { "repository": "acme/web", "allow_writes": false },
  "secrets": { "token": "github_pat_…" } }
// response 201
{ "id": "con_…", "type": "github", "name": "Website repo",
  "config": {…}, "status": "connected", "last_error": null,
  "created_at": "…", "detail": "15 read tools available" }
```
Validation before storage: unknown settings rejected; a secret sent as plain config rejected; values
checked against the field's pattern; booleans normalised. The secret is Fernet-encrypted; the
response contains the health-check detail, never the token.

### `POST /api/connections/oauth/start`
```jsonc
// request  { "type": "cloudflare", "name": "Hosting" }
// response 201
{ "connection_id": "con_…", "authorize_url": "https://…/authorize?…&code_challenge=…" }
```
The server discovers the provider's authorization server, registers ForgeOps dynamically, and builds
a PKCE authorization URL. **The code verifier never leaves the server.** The pending consent expires
after 10 minutes and is single-use.

### `GET /api/connections/oauth/callback`
Exchanges the authorization code, stores the encrypted OAuth session, health-checks the connection,
and returns a small self-closing HTML page. Every value shown is HTML-escaped, and the completion
message is posted only to the application's configured origins.

## 7.4 Status codes used

| Code | Meaning in this API |
|---|---|
| 200 / 201 | Success |
| 204 | Deleted |
| 401 | Not signed in |
| 403 | Missing or invalid CSRF token |
| 404 | Not found **or** not in the caller's workspace |
| 409 | Connection cannot be built (for example, an OAuth connection not yet authorised) |
| 422 | Validation failure, with a sentence naming the field |
| 502 | An upstream provider failed (MCP server or authorization server) |

## 7.5 Interactive documentation

FastAPI serves OpenAPI at `/openapi.json`, Swagger UI at `/docs` and ReDoc at `/redoc`. A screenshot
of `/docs` makes a good appendix figure.
