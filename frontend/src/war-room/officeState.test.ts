import { expect, test } from "vitest";
import type { Desk, EventType, InvestigationEvent } from "../api/types";
import { applyOfficeEvent, initialOfficeState, reduceEvents } from "./officeState";

let seq = 0;
const ev = (type: EventType, agent: string | null = null, data: Record<string, unknown> = {}): InvestigationEvent => ({
  seq: ++seq, type, agent, data, investigation_id: "inv_1", ts: `2026-09-22T10:00:${String(seq).padStart(2, "0")}Z`,
});

const desks: Desk[] = [
  { id: "code", title: "Code", area: "", specialist: true, connected: true, capabilities: ["code"], connectors: [] },
  { id: "knowledge", title: "Knowledge", area: "", specialist: true, connected: true, capabilities: ["knowledge"], connectors: [] },
  { id: "database", title: "Database", area: "", specialist: true, connected: false, capabilities: [], connectors: [] },
];

function run(events: InvestigationEvent[]) {
  return reduceEvents(initialOfficeState(desks), events);
}

function scenario() {
  seq = 0;
  return [
    ev("investigation_started", null, { description: "Checkout is slow" }),
    ev("chat_message", null, { role: "user", text: "Checkout is slow" }),
    ev("supervisor_started", "supervisor"),
    ev("plan_created", "supervisor", { summary: "Check the deploy", hypotheses: ["bad deploy"],
      tasks: [{ agent: "code", objective: "diff last deploy" }, { agent: "knowledge", objective: "runbooks" }] }),
    ev("agent_skipped", "database", { reason: "no connector" }),
    ev("agent_started", "code", { objective: "diff last deploy" }),
    ev("tool_called", "code", { call_id: "tc_1", tool: "github.list_commits", summary: "{}" }),
  ];
}

test("desks without connectors start offline, connected ones idle", () => {
  const s = initialOfficeState(desks);
  expect(s.agents.database.mode).toBe("offline");
  expect(s.agents.code.mode).toBe("idle");
  expect(s.agents.supervisor.mode).toBe("idle");
  expect(s.phase).toBe("idle");
});

test("planning, assignment and tool calls", () => {
  const s = run(scenario());
  expect(s.incident).toBe("Checkout is slow");
  expect(s.phase).toBe("investigating");
  expect(s.plan?.tasks.map((t) => t.agent)).toEqual(["code", "knowledge"]);
  expect(s.agents.knowledge.mode).toBe("assigned");
  expect(s.agents.knowledge.objective).toBe("runbooks");
  expect(s.agents.database.mode).toBe("offline");
  expect(s.agents.supervisor.location).toBe("supervisor");
  expect(s.agents.code.mode).toBe("calling");
  expect(s.agents.code.bubble).toMatchObject({ kind: "tool", text: expect.stringContaining("github.list_commits") });
  expect(s.agents.code.toolCalls).toBe(1);
  expect(s.timeline.map((t) => t.kind)).toEqual(["message", "plan"]);
});

test("supervisor walks to the whiteboard while planning", () => {
  seq = 0;
  const s = run([ev("investigation_started", null, { description: "x" }), ev("supervisor_started", "supervisor")]);
  expect(s.agents.supervisor.location).toBe("whiteboard");
  expect(s.phase).toBe("planning");
});

test("asking a colleague walks there and back; the colleague answers", () => {
  const events = scenario();
  const asking = run([...events, ev("agent_question", "code", { from: "code", to: "knowledge", question_id: "q_1", question: "Any runbook for pools?" })]);
  expect(asking.agents.code.location).toBe("knowledge");
  expect(asking.agents.code.mode).toBe("asking");
  expect(asking.agents.code.bubble).toMatchObject({ kind: "question" });
  expect(asking.agents.knowledge.mode).toBe("answering");

  const answered = applyOfficeEvent(asking, ev("agent_answer", "knowledge", { from: "code", to: "knowledge", question_id: "q_1", answer: "Yes: pool >= 20" }));
  expect(answered.agents.code.location).toBe("code");
  expect(answered.agents.code.mode).toBe("working");
  expect(answered.agents.knowledge.bubble).toMatchObject({ kind: "answer", text: "Yes: pool >= 20" });
  expect(answered.agents.knowledge.mode).toBe("assigned"); // restored to what it was doing
  expect(answered.questions[0]).toMatchObject({ id: "q_1", status: "answered", answer: "Yes: pool >= 20" });
});

test("evidence is pinned and counted; failures and completion", () => {
  const s = run([
    ...scenario(),
    ev("tool_completed", "code", { call_id: "tc_1", tool: "github.list_commits", ok: true, summary: "a1b2 lower pool" }),
    ev("evidence_added", "code", { evidence_id: "ev_1", finding: "Pool lowered", severity: "high", confidence: 0.8,
      failure_point: "config/db.ts:4", connector_type: "github" }),
    ev("agent_completed", "code", { findings: 1, summary: "found it" }),
    ev("agent_failed", "knowledge", { error: "timeout" }),
  ]);
  expect(s.evidence).toEqual([expect.objectContaining({ id: "ev_1", agent: "code", finding: "Pool lowered" })]);
  expect(s.agents.code.findings).toBe(1);
  expect(s.agents.code.mode).toBe("done");
  expect(s.agents.knowledge.mode).toBe("failed");
  expect(s.agents.knowledge.error).toBe("timeout");
});

test("rca, approval, action and completion", () => {
  const s = run([
    ...scenario(),
    ev("rca_started", "rca"),
    ev("rca_completed", "rca", { summary: "Pool lowered", failure_point: "a1b2", category: "config_change",
      confidence: 0.86, supporting_evidence: ["ev_1"] }),
    ev("approval_requested", "supervisor", { recommendations: [{ id: "rec_1", title: "Open issue", description: "d",
      action: "github_issue", parameters: {}, requires_approval: true }] }),
  ]);
  expect(s.phase).toBe("awaiting_approval");
  expect(s.rca).toMatchObject({ summary: "Pool lowered", confidence: 0.86 });
  expect(s.agents.rca.location).toBe("rcaBoard");
  expect(s.agents.human.mode).toBe("working");
  expect(s.recommendations.map((r) => r.id)).toEqual(["rec_1"]);
  expect(s.timeline.map((t) => t.kind)).toContain("approval");

  const done = reduceEvents(s, [
    ev("approval_granted", "supervisor", { kind: "approve", approved_recommendation_ids: ["rec_1"], decided_by: "usr_1" }),
    ev("action_started", "action", { recommendation_id: "rec_1", action: "github_issue" }),
  ]);
  expect(done.agents.action.location).toBe("door");
  expect(done.phase).toBe("acting");
  const finished = reduceEvents(done, [
    ev("action_completed", "action", { recommendation_id: "rec_1", status: "done", url: "https://github.com/o/r/issues/7" }),
    ev("report_ready", "supervisor"),
    ev("investigation_completed", "supervisor", { status: "completed" }),
  ]);
  expect(finished.agents.action.location).toBe("action");
  expect(finished.actions[0]).toMatchObject({ status: "done", url: "https://github.com/o/r/issues/7" });
  expect(finished.phase).toBe("completed");
  expect(finished.reportReady).toBe(true);
  expect(finished.endedAt).not.toBeNull();
});

test("failure is shown in the timeline", () => {
  seq = 0;
  const s = run([ev("investigation_started", null, { description: "x" }),
    ev("investigation_failed", null, { reason: "OPENROUTER_API_KEY is not set in .env" })]);
  expect(s.phase).toBe("failed");
  expect(s.failure).toBe("OPENROUTER_API_KEY is not set in .env");
  expect(s.timeline.at(-1)?.kind).toBe("failure");
});

test("replaying the same events is idempotent", () => {
  const events = scenario();
  const once = run(events);
  const twice = reduceEvents(once, events);
  expect(twice).toEqual(once);
});

test("the live feed keeps a bounded, readable history", () => {
  const s = run(scenario());
  expect(s.feed.at(-1)).toMatchObject({ agent: "code", text: expect.stringContaining("github.list_commits") });
  expect(s.feed.length).toBeLessThanOrEqual(60);
});

test("tool arguments are shown readably", async () => {
  const { readableArgs } = await import("./officeState");
  expect(readableArgs('{"base":"v2.13.4","head":"v2.14.0"}')).toBe("base v2.13.4 · head v2.14.0");
  expect(readableArgs("{}")).toBe("");
  expect(readableArgs("{\"a\":1,\"b\":[1]}")).toBe("a 1 · b [1]");
});
