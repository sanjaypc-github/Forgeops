import { api } from "./client";
import type { Desk, Investigation } from "./types";

export interface EvidenceDetail {
  id: string;
  agent: string;
  capability: string;
  connector_type: string;
  finding: string;
  failure_point: string | null;
  artifacts: { type: string; ref: string; url: string | null; timestamp: string | null; excerpt: string | null }[];
  severity: string;
  confidence: number;
  limitations: string | null;
  tool_call_ids: string[];
}

export interface InvestigationDetails {
  plan: { summary: string; hypotheses: string[] } | null;
  evidence: EvidenceDetail[] | null;
  rca: {
    summary: string; failure_point: string; category: string; confidence: number;
    supporting_evidence: string[]; contradicting_evidence: string[]; alternative_hypotheses: string[];
    missing_information: string[];
    recommendations: { id: string; title: string; description: string; action: string; parameters: Record<string, unknown>; requires_approval: boolean }[];
  } | null;
  action_results: { recommendation_id: string; status: string; detail: string; url: string | null }[] | null;
  errors: { agent: string; message: string }[] | null;
}

export type InvestigationDetail = Investigation & { details: InvestigationDetails | null };

export const listInvestigations = () => api<Investigation[]>("/investigations");
export const getInvestigation = (id: string) => api<InvestigationDetail>(`/investigations/${id}`);
export const createInvestigation = (body: { description: string }) =>
  api<Investigation>("/investigations", { method: "POST", body: JSON.stringify(body) });
export const listDesks = () => api<Desk[]>("/agents");
export const sendChat = (body: { text: string; investigation_id?: string }) =>
  api<{ investigation_id: string; status: string }>("/chat", { method: "POST", body: JSON.stringify(body) });
export const decide = (id: string, body: { kind: "approve" | "reject" | "investigate_more"; approved_recommendation_ids?: string[]; note?: string }) =>
  api<{ status: string }>(`/investigations/${id}/decision`, { method: "POST", body: JSON.stringify(body) });
