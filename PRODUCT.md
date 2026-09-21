# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **SaaS founders and CTOs** of small teams without dedicated SRE/DevOps staff, and **B2B engineering teams** with on-call rotations.
- Situation: in the middle of a live production incident (the site is slow, erroring, or broken), stressed and time-critical, often not the person who knows every part of the stack.
- Job: find the root cause, the exact point of failure, and the evidence for it in 10–20 minutes instead of 2–3 hours, then decide what to do.

## Product Purpose

ForgeOps investigates production incidents across the tools a SaaS product runs on (GitHub, Cloudflare, Vercel, Supabase, Sentry, Sanity, AWS, …). The user pastes a symptom into a chat; a Supervisor agent splits the work across specialist AI desks that investigate in parallel through connected tools and ask each other questions; an RCA step returns the root cause, failure point, evidence and confidence; a human approves any action. Success: a correct, evidence-backed root cause fast enough to act on during the incident.

## Positioning

- Parallel specialist desks grouped by system area (Code, Frontend & Hosting, Backend & Services, Database, Observability, Knowledge) that talk to each other, visible live as a 2D office.
- Every claim is tied to a real tool call against the customer's own systems; nothing is invented, and gaps are stated plainly.
- Read-only by default; every write needs explicit human approval.

## Operating Context

- Used during incidents, often under pressure; also for replaying past investigations and reading reports.
- Customers connect tools from a connector catalog (each connector an MCP server, read/write abilities shown).
- Surfaces: War Room (office + chat bar), connector catalog, investigation history, report.

## Capabilities and Constraints

- Web app: React + TypeScript + Vite frontend; FastAPI + LangGraph backend; live updates over server-sent events.
- The office must be driven only by real backend events (no simulated activity); refreshing replays the same state.
- One workspace per install in the MVP UI; data model is multi-company ready.
- Undecided: hosting, pricing, sign-up flow.

## Brand Commitments

- Name: ForgeOps (also referred to as EOPS, Engineering Operations Platform, in research material).
- No logo, colors, typefaces or visual identity exist yet.

## Evidence on Hand

- No customers, testimonials, benchmarks or case studies exist; none may be invented.
- Research framing in `docs/reference/` (EOPS project spec and architecture diagrams).

## Product Principles

1. Truth over theater: every visual state reflects a real event; every claim links to evidence.
2. Calm under pressure: the user is mid-incident; clarity and scanability beat decoration.
3. Show the work: parallel investigation and agent collaboration are visible, not hidden.
4. Human decides: actions are proposed, never taken silently.

## Accessibility & Inclusion

- Target WCAG 2.2 AA: contrast, full keyboard use, visible focus, screen-reader equivalents for office activity, and `prefers-reduced-motion` support for all walking and animation.
