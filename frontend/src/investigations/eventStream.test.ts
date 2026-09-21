import { expect, test } from "vitest";
import type { InvestigationEvent } from "../api/types";
import { applyEvent, initialStreamState } from "./eventStream";

const ev = (seq: number, type: InvestigationEvent["type"]): InvestigationEvent => ({
  seq, type, investigation_id: "inv_1", agent: null, ts: "2026-09-21T10:00:00Z", data: {},
});

test("appends events in order", () => {
  const s = applyEvent(applyEvent(initialStreamState, ev(1, "investigation_started")), ev(2, "agent_started"));
  expect(s.events.map((e) => e.seq)).toEqual([1, 2]);
  expect(s.done).toBe(false);
});

test("ignores duplicate or older events (replay after reconnect)", () => {
  let s = applyEvent(initialStreamState, ev(1, "investigation_started"));
  s = applyEvent(s, ev(2, "agent_started"));
  s = applyEvent(s, ev(2, "agent_started"));
  s = applyEvent(s, ev(1, "investigation_started"));
  expect(s.events.map((e) => e.seq)).toEqual([1, 2]);
});

test("marks the stream done on a terminal event", () => {
  const s = applyEvent(initialStreamState, ev(1, "investigation_failed"));
  expect(s.done).toBe(true);
});
