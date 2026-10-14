# 08 — Frontend guide (the War Room)

Feeds **Chapter 4 (Implementation)** and the report's screenshot figures.

---

## 8.1 Why the interface matters to the contribution

Most agent systems show a chat transcript. ForgeOps shows a **2D top-down office** in which every
movement is caused by a real backend event. The purpose is not decoration; it is **explainability**:
an engineer can see which desk is working, which tool it is calling right now, which desk asked whom
a question, and which findings are already on the evidence wall. Transparency of process is part of
why a human can be asked to approve the outcome.

A second property worth stating: the office is a **pure function of the event stream**. Refreshing
the browser mid-investigation replays the same state rather than losing it.

## 8.2 Screens

| Route | Screen | Contents |
|---|---|---|
| `/login` | Sign in | Email and password; issues the session and CSRF token |
| `/` and `/investigations/:id` | **War Room** | The office, the chat bar, evidence and activity panels, the run-cost meter |
| `/connectors` | Connectors | Catalog grouped by desk, connect forms, abilities, test and disconnect |
| `/investigations` | History | All investigations with status, source, tokens and date |
| `/investigations/:id/report` | Report | The rendered Markdown report |
| `/dev/office` | Developer harness | Replays scripted events into the office; development builds only |

## 8.3 The office

| File | Responsibility |
|---|---|
| `war-room/layout.ts` | A 40 × 24 tile grid; desk positions, boards, props, walking waypoints and a path-finder |
| `war-room/floor.ts` | Draws walls, floor, rugs, desks, chairs and props onto a canvas from a CC0 tile set |
| `war-room/tiles.ts` | Verified tile indices into the sprite sheet |
| `war-room/AgentSprite.tsx` | One agent: idle, typing, walking and talking states, animated with the Web Animations API |
| `war-room/art/portraitArt.ts` | Procedural pixel characters; engine adapted from an MIT-licensed project, with original recipes per agent |
| `war-room/Office.tsx` | Composes the canvas floor with DOM sprites and scales the stage |
| `war-room/placement.ts` | Where each agent stands for a given state |

**Assets and licensing, for the report's appendix:** the tile set is Kenney's *Tiny Town*
(CC0, public domain). The character-drawing engine is adapted from the MIT-licensed *Munder Difflin*
project, with its licence notice retained in the source file; the character recipes themselves are
original to this project.

## 8.4 The reducer — events to office state

`war-room/officeState.ts` (334 lines) is the heart of the frontend and the part most worth describing
in the report.

```ts
applyOfficeEvent(previousState, event) → nextState     // pure, no side effects
reduceEvents(initialState, events)     → state         // fold over the whole stream
```

Selected mappings:

| Event | Effect on the office |
|---|---|
| `plan_created` | Task cards travel to the chosen desks; skipped desks are greyed out as "no connector" |
| `agent_started` | That desk's agent sits and begins typing |
| `tool_called` | A speech bubble shows the readable tool call, e.g. "GitHub: list commits · acme/web" |
| `agent_question` | The asking agent **walks** to the other desk; both show the question |
| `agent_answer` | The answer appears; the agent walks back to its own desk |
| `evidence_added` | A finding card is pinned to the shared evidence wall |
| `rca_completed` | The root cause is written on the board |
| `approval_requested` | The chat bar shows Approve / Reject / Investigate more |
| `llm_usage` | The run-cost meter updates (calls, tokens, savings) |
| `investigation_failed` | The failure is shown plainly, with its reason |

Because the reducer is pure, it is unit-tested with scripted event sequences and needs no browser,
no backend and no model.

## 8.5 Panels and chat

- `ChatPanel.tsx` — the conversation: user messages, Supervisor replies, and the **approval card**
  listing each recommendation with its action; buttons for approve, reject and investigate more.
- `SidePanels.tsx` — `EvidencePanel` (findings with their citations and links), `ActivityPanel` (the
  live feed), `AgentCard` (a desk's detail when clicked) and `CostMeter` (calls, tokens, savings).

## 8.6 Connectors page

`pages/ConnectorsPage.tsx` (336 lines):

- the catalog grouped by desk, with a desk filter, and "coming soon" entries shown as dashed cards;
- a connect form built dynamically from each connector's `config_fields`, with secret fields rendered
  as password inputs and the provider's setup steps listed above them;
- for OAuth connectors, no token form at all — a consent button that opens the provider's own window
  and a plain statement that ForgeOps never sees the password;
- for each connection: status, what it points at, its abilities grouped by desk, a re-test button and
  a two-step disconnect.

## 8.7 Live updates

`investigations/eventStream.ts` subscribes to the SSE endpoint and tracks the last sequence number.
On reconnect it sends `Last-Event-ID`, so no event is missed and none is applied twice (the reducer
also ignores any event whose sequence it has already seen).

## 8.8 Design system

`styles/tokens.css` defines the palette, type scale, radii and shadows, with a dark-mode block. The
neutrals lean slightly green-grey so that the warm pixel floor remains the loudest thing on screen;
one warm accent is reserved for the live incident clock. Keeping the design tokens in one file is
what lets the report claim a consistent visual system rather than ad-hoc styling.

## 8.9 Suggested screenshots for the report

1. The War Room mid-investigation — desks working, a speech bubble visible, evidence wall filling.
2. An agent walking to another desk during `agent_question`.
3. The chat bar showing the approval card.
4. The Connectors page with the catalog grouped by desk.
5. A connection's abilities list, showing read versus write.
6. The report page with the evidence table and the Run cost table.
7. `/docs` (Swagger UI) for the API appendix.
