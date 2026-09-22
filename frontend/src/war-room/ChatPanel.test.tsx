import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { expect, test, vi } from "vitest";
import type { EventType, InvestigationEvent } from "../api/types";
import { ChatPanel } from "./ChatPanel";
import { initialOfficeState, reduceEvents } from "./officeState";

let seq = 0;
const ev = (type: EventType, data: Record<string, unknown> = {}, agent: string | null = null): InvestigationEvent =>
  ({ seq: ++seq, type, agent, data, investigation_id: "inv_1", ts: "2026-09-22T10:00:00Z" });

function awaitingApproval() {
  seq = 0;
  return reduceEvents(initialOfficeState(), [
    ev("investigation_started", { description: "Checkout slow" }),
    ev("chat_message", { role: "user", text: "Checkout slow" }),
    ev("rca_completed", { summary: "Pool lowered", failure_point: "config/db.ts:4", category: "config_change", confidence: 0.86, supporting_evidence: ["ev_1"] }, "rca"),
    ev("approval_requested", { recommendations: [
      { id: "rec_1", title: "Open an issue", description: "Restore the pool", action: "github_issue", parameters: {}, requires_approval: true },
      { id: "rec_2", title: "Add a CI check", description: "Guard the pool size", action: "none", parameters: {}, requires_approval: false },
    ] }, "supervisor"),
  ]);
}

function renderChat(state = awaitingApproval()) {
  const onDecide = vi.fn().mockResolvedValue(undefined);
  const onSend = vi.fn().mockResolvedValue(undefined);
  render(<MemoryRouter><ChatPanel investigationId="inv_1" state={state} onSend={onSend} onDecide={onDecide} /></MemoryRouter>);
  return { onDecide, onSend };
}

test("shows the root cause and approves only the selected write actions", async () => {
  const { onDecide } = renderChat();
  expect(screen.getByText("Pool lowered")).toBeInTheDocument();
  expect(screen.getByText("config/db.ts:4")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Approve 1 action/ }));
  expect(onDecide).toHaveBeenCalledWith("approve", ["rec_1"], undefined);
});

test("unticking every write action disables approve", async () => {
  renderChat();
  await userEvent.click(screen.getByRole("checkbox"));
  expect(screen.getByRole("button", { name: /Approve 0 actions/ })).toBeDisabled();
});

test("investigate more asks for a note and sends it", async () => {
  const { onDecide } = renderChat();
  await userEvent.click(screen.getByRole("button", { name: /Investigate more/ }));
  await userEvent.type(screen.getByLabelText("What should the team look at?"), "Check the cache change");
  await userEvent.click(screen.getByRole("button", { name: /Send back to the desks/ }));
  expect(onDecide).toHaveBeenCalledWith("investigate_more", [], "Check the cache change");
});

test("Enter sends a follow-up question", async () => {
  const { onSend } = renderChat();
  await userEvent.type(screen.getByLabelText("Message"), "Why the pool?{Enter}");
  expect(onSend).toHaveBeenCalledWith("Why the pool?");
});
