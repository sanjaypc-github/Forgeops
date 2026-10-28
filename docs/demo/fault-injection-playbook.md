# Fault injection playbook — CampusEvents

**Keep this file in the ForgeOps repository, never in `campus-events`.** If the answer is committed
to the repository under test, the Code desk can simply read it and the demonstration proves nothing.

---

## Before you break anything

1. The live URL lists five events.
2. All four connectors show **Connected** in ForgeOps: GitHub, Cloudflare, Supabase (the CampusEvents
   project), knowledge vault.
3. Cloudflare Pages has at least three successful deployments, so "the most recent deploy" means
   something.
4. **Run one investigation on the healthy site** — for example *"check whether the campus events site
   is healthy"*. This is your baseline: it shows the desks working and finding nothing wrong, which
   makes the later run far more convincing.
5. Note the time. The window matters to the Supervisor's plan.

## Fault A — the schema mismatch (primary)

One line in `src/lib/events.ts`:

```diff
-    .select("id, title, venue, starts_at, seats_left")
+    .select("id, title, venue, startTime, seats_left")
```

Commit with a message that does **not** give it away:

```
refactor: align event field naming with the new API style guide
```

Push to `main`. Cloudflare rebuilds; within about a minute the live site shows:

```
Unable to load events
Could not load events: column events.startTime does not exist
```

### What each desk should independently find

| Desk | Evidence available to it |
|---|---|
| Code (GitHub) | The commit, its message, the file and the changed line, author and timestamp |
| Frontend & Hosting (Cloudflare) | A deployment finished minutes before the failure began |
| Database (Supabase) | `public.events` has `starts_at`, not `startTime`; the API log shows the failing request |
| Knowledge (vault) | `schema.md` states the snake_case contract; `on-call.md` step 2 describes this exact failure |

### What to type into ForgeOps

Describe it as a user would, with **no hint of the cause**:

> "The campus events page stopped showing events this afternoon. Visitors see an error box instead of
> the list."

A good result names the commit and `src/lib/events.ts`, states that `startTime` does not exist in the
schema, and cites evidence from at least two desks.

## Fault B — the missing environment variable (reserve)

Use this if Fault A is resolved and you want a second run, or if a build problem blocks Fault A.

In `src/lib/events.ts`, change `VITE_SUPABASE_ANON_KEY` to `VITE_SUPABASE_KEY`. The build succeeds,
the key is `undefined`, and Supabase rejects every request with an authentication error. The Code
desk finds the commit; the Hosting desk finds no Pages variable by that name. The vault contains a
past incident with exactly this shape, so the Knowledge desk should recognise it.

## Recovering afterwards

```bash
git revert <commit>      # keeps the history honest, and triggers a fresh deployment
git push
```

Watch the Cloudflare deployment finish, then reload the live URL. Keep the faulty commit in history —
it is evidence that the demonstration was real.

## If the demonstration goes wrong

| Problem | What to do |
|---|---|
| OpenRouter rate limit | Free-tier daily cap. Add credit beforehand; this has already caused two failed runs |
| A desk shows "no connector" | Expected if that tool is not connected — ForgeOps reports the gap honestly; say so rather than hiding it |
| The run exceeds its time budget | Budgets are in `.env`: `FORGEOPS_SPECIALIST_SECONDS`, `FORGEOPS_RUN_SECONDS` |
| Cloudflare tool names are wrong | Run `uv run python -m forgeops.devtools.mcp_tools <connection-id>` and pin the real names |
| Nothing works live | Play the recorded video of a successful run — record one the night before |

## Honest framing for the reviewer

Say plainly what this demonstrates and what it does not. It shows that the architecture collects
evidence from four independent sources and reaches a cited conclusion on a real fault in a live
system. It is **one scenario**, not a benchmark; the measured evaluation against OpenRCA and injected
fault suites is the next phase, and the protocol is already written in
`docs/report/10-results-and-measurements.md`.
