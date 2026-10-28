# Sample application spec — "CampusEvents"

Hand this whole file to Claude Code. It is designed so that **one deliberate bug leaves a trail in
four different connected tools**, which is exactly what ForgeOps needs to demonstrate cross-source
root-cause analysis.

Build it simple. The app is a stage, not the performance.

---

## 1. What to build

A single-page public website that lists upcoming campus events, read live from Supabase.

- **One page.** A heading, a list of event cards, a loading state, and an error state.
- **No authentication, no writes, no admin screen.** Read-only.
- Must be **deployable to Cloudflare Pages from GitHub** so that every push produces a deployment.

## 2. Stack (do not substitute)

| Layer | Choice | Why it must be this |
|---|---|---|
| Framework | **Vite + React + TypeScript** | Fast build, works on Cloudflare Pages with zero config |
| Data | **Supabase** (`@supabase/supabase-js`) | The Database desk reads its schema, migrations and logs |
| Hosting | **Cloudflare Pages**, connected to the GitHub repo | The Frontend & Hosting desk reads deployments and build logs |
| Repository | **GitHub**, public | The Code desk reads commits and diffs |
| Docs | **Notion** page + local Markdown runbooks | The Knowledge desk reads them |

## 3. Database schema

Run this in the Supabase SQL editor of a **new project** (do not reuse the ForgeOps database):

```sql
create table public.events (
  id           uuid primary key default gen_random_uuid(),
  title        text not null,
  venue        text not null,
  starts_at    timestamptz not null,
  seats_left   integer not null default 0,
  is_published boolean not null default true,
  created_at   timestamptz not null default now()
);

alter table public.events enable row level security;

create policy "public read published events"
  on public.events for select
  to anon
  using (is_published = true);

insert into public.events (title, venue, starts_at, seats_left) values
  ('AI & Data Science Symposium', 'Main Auditorium',  now() + interval '3 days',  120),
  ('Hackathon Kickoff',           'Innovation Lab',   now() + interval '7 days',   60),
  ('Robotics Workshop',           'Mechanical Block', now() + interval '10 days',  35),
  ('Alumni Tech Talk',            'Seminar Hall 2',   now() + interval '14 days',  90),
  ('Open Source Day',             'Library Lawn',     now() + interval '21 days', 200);
```

**Note the exact column name `starts_at`.** The whole demo depends on it.

## 4. The single data call

Put this in one file, `src/lib/events.ts`, and nowhere else — the bug is injected here later:

```ts
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
);

export interface CampusEvent {
  id: string;
  title: string;
  venue: string;
  starts_at: string;
  seats_left: number;
}

export async function fetchEvents(): Promise<CampusEvent[]> {
  const { data, error } = await supabase
    .from("events")
    .select("id, title, venue, starts_at, seats_left")   // ← the line the bug will change
    .eq("is_published", true)
    .order("starts_at", { ascending: true });

  if (error) throw new Error(`Could not load events: ${error.message}`);
  return data ?? [];
}
```

## 5. Error state — make the failure visible

When `fetchEvents` throws, the page must render, visibly, in the browser:

```
Unable to load events
Could not load events: column events.<name> does not exist
```

Show the real message from Supabase. **Do not swallow the error, do not fall back to sample data, do
not show only "something went wrong".** The visible error is the symptom ForgeOps investigates, and
the reviewer must be able to see it on the live URL.

Also `console.error` the full error object.

## 6. Repository layout

```
campus-events/
├── src/
│   ├── lib/events.ts          ← the data call (the bug goes here)
│   ├── components/EventCard.tsx
│   ├── App.tsx                ← loading / error / list states
│   └── main.tsx
├── docs/
│   ├── runbooks/
│   │   ├── schema.md          ← documents the events table, column by column
│   │   ├── deploy.md          ← how a deploy reaches Cloudflare Pages
│   │   └── incident-2026-09-site-blank.md   ← a past incident write-up
│   └── architecture.md
├── .env.example               ← VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
├── package.json
└── README.md
```

The `docs/runbooks/` folder is **also** what you point the ForgeOps knowledge vault at, so write it
properly — 150–300 words per file, in the voice of a real team.

`docs/runbooks/schema.md` must state plainly: *"the start time column is named `starts_at`
(snake_case). The frontend selects it by that exact name in `src/lib/events.ts`."* That single
sentence is what lets the Knowledge desk confirm the Code desk's finding.

## 7. Deployment

1. Push the repository to GitHub (public).
2. Cloudflare dashboard → **Workers & Pages → Create → Pages → Connect to Git** → select the repo.
3. Build command `npm run build`, output directory `dist`.
4. Add the two environment variables (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`) in the Pages
   project settings.
5. Confirm the live URL renders the five events.

Every later push now produces a Cloudflare deployment — which is what the Frontend & Hosting desk
investigates.

## 8. Notion page

Create one Notion page titled **"CampusEvents — architecture and schema"** containing:
- a one-paragraph description of the app;
- the `events` table with each column and its type;
- a line saying the site is deployed on Cloudflare Pages from `main`;
- an "On call" section: *"If the events list fails to load, check the most recent commit to
  `src/lib/events.ts` and compare the selected columns against the schema."*

Share the page with the integration you create for the ForgeOps Notion connector.

## 9. The fault to inject (only after everything is connected and working)

**Do not add this now.** Build the healthy version first, confirm the live site works, connect all
the connectors to ForgeOps, and only then commit this one-line change:

```diff
-    .select("id, title, venue, starts_at, seats_left")
+    .select("id, title, venue, startTime, seats_left")
```

Commit it with a realistic, slightly misleading message — a real incident never arrives labelled:

```
refactor: align event field naming with the new API style guide
```

Push to `main`. Cloudflare rebuilds and deploys. Within a minute the live site shows:

```
Unable to load events
Could not load events: column events.startTime does not exist
```

### Why this particular fault is the right one

| Desk | What it can independently discover |
|---|---|
| **Code** (GitHub) | The commit, its message, the exact file and line, the author and the time |
| **Frontend & Hosting** (Cloudflare) | A deployment happened minutes before the failure started |
| **Database** (Supabase) | The `events` table has `starts_at`, not `startTime`; logs show the failing request |
| **Knowledge** (vault + Notion) | The schema runbook states the column is `starts_at` |

Four desks, four independent pieces of evidence, one conclusion — and ForgeOps must name the commit
and the file and line as the failure point. That is the demonstration.

### A second fault, if you want one in reserve

Change the environment variable name in `src/lib/events.ts` from `VITE_SUPABASE_ANON_KEY` to
`VITE_SUPABASE_KEY`. The build succeeds, the key is `undefined`, every request returns 401, and the
page shows an authentication error. The Code desk finds the commit; the Hosting desk finds that the
Pages project has no variable by that name.

## 10. Checklist before the demo

- [ ] Live URL loads five events
- [ ] GitHub repository public, with a real commit history (not one squashed commit)
- [ ] Cloudflare Pages deploying on push, with at least three successful deployments in its history
- [ ] Supabase project separate from the ForgeOps database
- [ ] `docs/runbooks/` has three files, written like a real team wrote them
- [ ] Notion page created and shared with the integration
- [ ] All connectors connected in ForgeOps and showing "Connected"
- [ ] The healthy site investigated once **before** breaking it, so you have a "nothing wrong" baseline
- [ ] Only then: push the faulty commit
