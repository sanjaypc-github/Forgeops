export interface Me {
  user: { id: string; email: string };
  workspace: { id: string; name: string };
  csrf_token: string;
}

export type InvestigationStatus =
  | "queued" | "running" | "awaiting_approval" | "acting" | "completed" | "rejected" | "failed";

export interface Investigation {
  id: string;
  description: string;
  status: InvestigationStatus;
  source: "web" | "slack";
  service_id: string | null;
  window_start: string | null;
  window_end: string | null;
  created_at: string;
}

export type EventType =
  | "investigation_started" | "supervisor_started" | "plan_created" | "agent_skipped"
  | "agent_started" | "tool_called" | "tool_completed" | "evidence_added" | "agent_failed"
  | "agent_completed" | "agent_question" | "agent_answer" | "agent_question_failed" | "chat_message"
  | "review_completed" | "rca_started" | "rca_completed"
  | "approval_requested" | "approval_granted" | "approval_rejected" | "action_started"
  | "action_completed" | "report_ready" | "investigation_completed" | "investigation_failed";

export interface InvestigationEvent {
  seq: number;
  investigation_id: string;
  type: EventType;
  agent: string | null;
  ts: string;
  data: Record<string, unknown>;
}
