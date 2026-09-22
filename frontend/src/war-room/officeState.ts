/**
 * What the office shows, derived purely from investigation events. Same events in, same office out:
 * a page refresh replays the stored events and lands on exactly this state.
 */
import type { Desk, InvestigationEvent } from "../api/types";
import type { Place } from "./layout";
import { PERSONAS, type Persona, isAgentId } from "./personas";

export type Mode =
  | "offline" | "idle" | "skipped" | "assigned" | "working" | "calling"
  | "asking" | "answering" | "done" | "failed";

export interface Bubble {
  kind: "tool" | "question" | "answer" | "note" | "error" | "found";
  text: string;
  seq: number;
}

export interface AgentView {
  id: Persona;
  mode: Mode;
  location: Place;
  objective?: string;
  bubble: Bubble | null;
  findings: number;
  toolCalls: number;
  error?: string;
  skippedReason?: string;
  /** Mode to return to after answering a colleague. */
  resumeMode?: Mode;
}

export interface EvidenceCard {
  id: string;
  agent: Persona;
  finding: string;
  severity: string;
  confidence: number;
  failurePoint: string | null;
  connector: string;
  seq: number;
}

export interface RecommendationView {
  id: string;
  title: string;
  description: string;
  action: string;
  requires_approval: boolean;
}

export type TimelineEntry =
  | { kind: "message"; seq: number; role: "user" | "supervisor"; text: string }
  | { kind: "plan"; seq: number }
  | { kind: "rca"; seq: number }
  | { kind: "approval"; seq: number }
  | { kind: "decision"; seq: number; decision: string; note: string | null }
  | { kind: "action"; seq: number; recommendationId: string }
  | { kind: "failure"; seq: number; reason: string };

export interface FeedItem {
  seq: number;
  ts: string;
  agent: Persona | null;
  text: string;
  tone: "neutral" | "good" | "bad" | "talk";
}

export type Phase =
  | "idle" | "planning" | "investigating" | "reviewing" | "analyzing"
  | "awaiting_approval" | "acting" | "completed" | "rejected" | "failed";

export interface OfficeState {
  lastSeq: number;
  phase: Phase;
  incident: string | null;
  startedAt: string | null;
  endedAt: string | null;
  agents: Record<Persona, AgentView>;
  plan: { summary: string; hypotheses: string[]; tasks: { agent: Persona; objective: string }[] } | null;
  evidence: EvidenceCard[];
  questions: { id: string; from: Persona; to: Persona; question: string; answer?: string; status: string }[];
  rca: { summary: string; failurePoint: string; category: string; confidence: number; supporting: string[] } | null;
  recommendations: RecommendationView[];
  decision: { kind: string; note: string | null } | null;
  actions: { recommendationId: string; status: string; url: string | null; detail: string }[];
  timeline: TimelineEntry[];
  feed: FeedItem[];
  failure: string | null;
  reportReady: boolean;
}

const FEED_LIMIT = 60;
const str = (v: unknown, fallback = ""): string => (typeof v === "string" ? v : fallback);
const num = (v: unknown, fallback = 0): number => (typeof v === "number" ? v : fallback);
const short = (text: string, n = 90): string => (text.length > n ? `${text.slice(0, n - 1)}…` : text);

/** `{"base":"v2.13.4","head":"v2.14.0"}` -> `base v2.13.4 · head v2.14.0` (readable in a bubble). */
export function readableArgs(summary: string): string {
  if (!summary || summary === "{}") return "";
  try {
    const parsed = JSON.parse(summary) as Record<string, unknown>;
    return Object.entries(parsed).map(([k, v]) => `${k} ${typeof v === "string" ? v : JSON.stringify(v)}`).join(" · ");
  } catch {
    // truncated summaries are not valid JSON; strip the punctuation instead
    return summary.replace(/[{}"]/g, "").replace(/,/g, " · ").replace(/:/g, " ");
  }
}

export function initialOfficeState(desks: Desk[] = []): OfficeState {
  const connected = new Set(desks.filter((d) => d.connected).map((d) => d.id));
  const known = new Set(desks.map((d) => d.id));
  const agents = {} as Record<Persona, AgentView>;
  for (const id of Object.keys(PERSONAS) as Persona[]) {
    const offline = isAgentId(id) && PERSONAS[id] && known.has(id) && !connected.has(id)
      && !["supervisor", "rca", "action"].includes(id);
    agents[id] = { id, mode: offline ? "offline" : "idle", location: id, bubble: null, findings: 0, toolCalls: 0 };
  }
  return {
    lastSeq: 0, phase: "idle", incident: null, startedAt: null, endedAt: null, agents, plan: null,
    evidence: [], questions: [], rca: null, recommendations: [], decision: null, actions: [],
    timeline: [], feed: [], failure: null, reportReady: false,
  };
}

function patchAgent(state: OfficeState, id: Persona, patch: Partial<AgentView>): OfficeState {
  return { ...state, agents: { ...state.agents, [id]: { ...state.agents[id], ...patch } } };
}

function feed(state: OfficeState, event: InvestigationEvent, agent: Persona | null, text: string,
              tone: FeedItem["tone"] = "neutral"): OfficeState {
  const item: FeedItem = { seq: event.seq, ts: event.ts, agent, text, tone };
  return { ...state, feed: [...state.feed, item].slice(-FEED_LIMIT) };
}

const title = (p: Persona) => PERSONAS[p].short;

export function applyOfficeEvent(prev: OfficeState, event: InvestigationEvent): OfficeState {
  if (event.seq <= prev.lastSeq) return prev;
  let s: OfficeState = { ...prev, lastSeq: event.seq };
  const d = event.data;
  const agent: Persona | null = isAgentId(event.agent) ? event.agent : null;
  const bubble = (kind: Bubble["kind"], text: string): Bubble => ({ kind, text: short(text), seq: event.seq });

  switch (event.type) {
    case "investigation_started":
      s = { ...s, incident: str(d.description), phase: "planning", startedAt: event.ts };
      return feed(s, event, null, `Investigation started: ${short(str(d.description), 70)}`);

    case "chat_message": {
      const role = d.role === "supervisor" ? "supervisor" : "user";
      s = { ...s, timeline: [...s.timeline, { kind: "message", seq: event.seq, role, text: str(d.text) }] };
      return s;
    }

    case "supervisor_started":
      s = patchAgent(s, "supervisor", { mode: "working", location: "whiteboard", bubble: bubble("note", "Planning the investigation") });
      return feed({ ...s, phase: "planning" }, event, "supervisor", "Planning the investigation");

    case "plan_created": {
      const tasks = (Array.isArray(d.tasks) ? d.tasks : [])
        .map((t) => t as { agent?: string; objective?: string })
        .filter((t) => isAgentId(t.agent))
        .map((t) => ({ agent: t.agent as Persona, objective: str(t.objective) }));
      s = { ...s, phase: "investigating",
        plan: { summary: str(d.summary), hypotheses: (d.hypotheses as string[]) ?? [], tasks },
        timeline: [...s.timeline, { kind: "plan", seq: event.seq }] };
      s = patchAgent(s, "supervisor", { location: "supervisor", bubble: null });
      for (const t of tasks) s = patchAgent(s, t.agent, { mode: "assigned", objective: t.objective });
      return feed(s, event, "supervisor", `Plan: ${short(str(d.summary), 60)} (${tasks.map((t) => title(t.agent)).join(", ")})`);
    }

    case "agent_skipped": {
      if (!agent) return s;
      const reason = str(d.reason);
      return patchAgent(s, agent, { mode: reason === "no connector" ? "offline" : "skipped", skippedReason: reason });
    }

    case "agent_started":
      if (!agent) return s;
      s = patchAgent(s, agent, { mode: "working", location: agent, objective: str(d.objective) || s.agents[agent].objective });
      return feed(s, event, agent, `${title(agent)} started: ${short(str(d.objective), 60)}`);

    case "tool_called": {
      if (!agent) return s;
      const text = `${str(d.tool)} ${readableArgs(str(d.summary))}`.trim();
      s = patchAgent(s, agent, { mode: agent === "action" ? "working" : "calling", bubble: bubble("tool", text),
        toolCalls: s.agents[agent].toolCalls + 1 });
      return feed(s, event, agent, `→ ${text}`);
    }

    case "tool_completed": {
      if (!agent) return s;
      const ok = d.ok === true;
      const text = `${str(d.tool)} ${ok ? "✓" : "✗"} ${str(d.summary)}`.trim();
      const current = s.agents[agent];
      s = patchAgent(s, agent, { mode: current.mode === "calling" ? "working" : current.mode, bubble: bubble(ok ? "tool" : "error", text) });
      return feed(s, event, agent, text, ok ? "neutral" : "bad");
    }

    case "agent_question": {
      const from = isAgentId(str(d.from)) ? (d.from as Persona) : null;
      const to = isAgentId(str(d.to)) ? (d.to as Persona) : null;
      if (!from || !to) return s;
      s = patchAgent(s, from, { mode: "asking", location: to, bubble: bubble("question", str(d.question)) });
      s = patchAgent(s, to, { mode: "answering", resumeMode: s.agents[to].mode === "answering" ? s.agents[to].resumeMode : s.agents[to].mode });
      s = { ...s, questions: [...s.questions, { id: str(d.question_id), from, to, question: str(d.question), status: "asked" }] };
      return feed(s, event, from, `${title(from)} asks ${title(to)}: ${short(str(d.question), 60)}`, "talk");
    }

    case "agent_answer": {
      const from = isAgentId(str(d.from)) ? (d.from as Persona) : null;
      const to = isAgentId(str(d.to)) ? (d.to as Persona) : null;
      if (!from || !to) return s;
      s = patchAgent(s, from, { mode: "working", location: from, bubble: null });
      s = patchAgent(s, to, { mode: s.agents[to].resumeMode ?? "working", resumeMode: undefined, bubble: bubble("answer", str(d.answer)) });
      s = { ...s, questions: s.questions.map((q) => q.id === str(d.question_id) ? { ...q, answer: str(d.answer), status: "answered" } : q) };
      return feed(s, event, to, `${title(to)} answers ${title(from)}: ${short(str(d.answer), 60)}`, "talk");
    }

    case "agent_question_failed": {
      const from = isAgentId(str(d.from)) ? (d.from as Persona) : agent;
      const to = isAgentId(str(d.to)) ? (d.to as Persona) : null;
      if (from) s = patchAgent(s, from, { mode: s.agents[from].mode === "asking" ? "working" : s.agents[from].mode,
        location: from, bubble: bubble("error", `Couldn't ask ${to ? title(to) : "colleague"}: ${str(d.reason)}`) });
      if (to && s.agents[to].mode === "answering") s = patchAgent(s, to, { mode: s.agents[to].resumeMode ?? "working", resumeMode: undefined });
      s = { ...s, questions: s.questions.map((q) => q.id === str(d.question_id) ? { ...q, status: "failed" } : q) };
      return feed(s, event, from, `Question not answered: ${short(str(d.reason), 60)}`, "bad");
    }

    case "evidence_added": {
      if (!agent) return s;
      const card: EvidenceCard = { id: str(d.evidence_id), agent, finding: str(d.finding), severity: str(d.severity, "info"),
        confidence: num(d.confidence), failurePoint: typeof d.failure_point === "string" ? d.failure_point : null,
        connector: str(d.connector_type), seq: event.seq };
      if (s.evidence.some((e) => e.id === card.id)) return s;
      s = { ...s, evidence: [...s.evidence, card] };
      s = patchAgent(s, agent, { findings: s.agents[agent].findings + 1, bubble: bubble("found", card.finding) });
      return feed(s, event, agent, `Evidence: ${short(card.finding, 70)}`, "good");
    }

    case "agent_completed":
      if (!agent) return s;
      s = patchAgent(s, agent, { mode: "done", location: agent, bubble: null });
      return feed(s, event, agent, `${title(agent)} finished (${num(d.findings)} finding${num(d.findings) === 1 ? "" : "s"})`);

    case "agent_failed":
      if (!agent) return s;
      s = patchAgent(s, agent, { mode: "failed", location: agent, error: str(d.error), bubble: bubble("error", str(d.error)) });
      return feed(s, event, agent, `${title(agent)} failed: ${short(str(d.error), 60)}`, "bad");

    case "review_completed": {
      const followUps = Array.isArray(d.follow_ups) ? d.follow_ups.length : 0;
      s = { ...s, phase: followUps ? "investigating" : "reviewing" };
      s = patchAgent(s, "supervisor", { bubble: bubble("note", followUps ? `${followUps} follow-up task${followUps > 1 ? "s" : ""}` : "Evidence is enough") });
      return feed(s, event, "supervisor", followUps ? `Review: ${followUps} follow-up task(s)` : "Review: evidence is sufficient");
    }

    case "rca_started":
      s = patchAgent({ ...s, phase: "analyzing" }, "rca", { mode: "working", location: "evidenceWall", bubble: bubble("note", "Reading the evidence") });
      return feed(s, event, "rca", "Analysing all evidence");

    case "rca_completed":
      s = { ...s, rca: { summary: str(d.summary), failurePoint: str(d.failure_point), category: str(d.category),
        confidence: num(d.confidence), supporting: (d.supporting_evidence as string[]) ?? [] },
        timeline: [...s.timeline, { kind: "rca", seq: event.seq }] };
      s = patchAgent(s, "rca", { mode: "done", location: "rcaBoard", bubble: null });
      return feed(s, event, "rca", `Root cause (${Math.round(num(d.confidence) * 100)}%): ${short(str(d.summary), 60)}`, "good");

    case "approval_requested": {
      const recs = (Array.isArray(d.recommendations) ? d.recommendations : []) as RecommendationView[];
      s = { ...s, phase: "awaiting_approval", recommendations: recs, timeline: [...s.timeline, { kind: "approval", seq: event.seq }] };
      s = patchAgent(s, "human", { mode: "working" });
      return feed(s, event, "supervisor", "Waiting for your decision");
    }

    case "approval_granted":
    case "approval_rejected": {
      const kind = str(d.kind, event.type === "approval_granted" ? "approve" : "reject");
      const note = typeof d.note === "string" ? d.note : null;
      s = { ...s, decision: { kind, note }, phase: kind === "approve" ? "acting" : kind === "investigate_more" ? "planning" : s.phase,
        timeline: [...s.timeline, { kind: "decision", seq: event.seq, decision: kind, note }] };
      s = patchAgent(s, "human", { mode: "done" });
      return feed(s, event, "human", kind === "approve" ? "Approved" : kind === "investigate_more" ? "Asked for more investigation" : "Rejected");
    }

    case "action_started":
      s = patchAgent(s, "action", { mode: "working", location: "door", bubble: bubble("note", "Opening the issue") });
      return feed(s, event, "action", "Carrying out the approved action");

    case "action_completed": {
      const result = { recommendationId: str(d.recommendation_id), status: str(d.status), url: typeof d.url === "string" ? d.url : null, detail: str(d.detail) };
      s = { ...s, actions: [...s.actions, result], timeline: [...s.timeline, { kind: "action", seq: event.seq, recommendationId: result.recommendationId }] };
      s = patchAgent(s, "action", { mode: "done", location: "action", bubble: null });
      return feed(s, event, "action", `Action ${result.status}${result.url ? `: ${result.url}` : ""}`, result.status === "done" ? "good" : "bad");
    }

    case "report_ready":
      return { ...s, reportReady: true };

    case "investigation_completed": {
      const status = str(d.status) === "rejected" ? "rejected" : "completed";
      return feed({ ...s, phase: status, endedAt: event.ts }, event, null, status === "rejected" ? "Investigation closed" : "Investigation complete");
    }

    case "investigation_failed":
      s = { ...s, phase: "failed", endedAt: event.ts, failure: str(d.reason, "The investigation failed"),
        timeline: [...s.timeline, { kind: "failure", seq: event.seq, reason: str(d.reason) }] };
      return feed(s, event, null, `Failed: ${short(str(d.reason), 70)}`, "bad");

    default:
      return s;
  }
}

export function reduceEvents(state: OfficeState, events: InvestigationEvent[]): OfficeState {
  return events.reduce(applyOfficeEvent, state);
}
