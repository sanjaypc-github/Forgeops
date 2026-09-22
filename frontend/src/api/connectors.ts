import { api } from "./client";
import type { AgentId } from "./types";

export interface ConfigField {
  key: string;
  label: string;
  secret: boolean;
  required: boolean;
  help: string;
  placeholder: string;
  boolean: boolean;
  pattern: string | null;
}

export interface Ability {
  name: string;
  description: string;
  capability: string;
  desk: AgentId;
  permission: "read" | "write";
}

export interface CatalogEntry {
  type: string;
  display_name: string;
  description: string;
  agents: AgentId[];
  status: "available" | "coming_soon";
  config_fields: ConfigField[];
  docs_url: string | null;
  setup_steps: string[];
  supports_writes: boolean;
  abilities: Ability[];
}

export interface Connection {
  id: string;
  type: string;
  name: string;
  config: Record<string, unknown>;
  status: "connected" | "error" | string;
  last_error: string | null;
  created_at: string;
}

export type ConnectionCreated = Connection & { detail: string };

export interface ConnectionInput {
  type: string;
  name: string;
  config: Record<string, string | boolean>;
  secrets: Record<string, string>;
}

export const DESK_LABELS: Record<AgentId, string> = {
  supervisor: "Supervisor",
  code: "Code",
  frontend_hosting: "Frontend & Hosting",
  backend_services: "Backend & Services",
  database: "Database",
  observability: "Observability",
  knowledge: "Knowledge",
  rca: "RCA",
  action: "Action (after approval)",
};

export const DESK_ORDER: AgentId[] = [
  "code", "frontend_hosting", "backend_services", "database", "observability", "knowledge", "action",
];

export const getCatalog = () => api<CatalogEntry[]>("/connectors/catalog");
export const listConnections = () => api<Connection[]>("/connections");
export const createConnection = (body: ConnectionInput) =>
  api<ConnectionCreated>("/connections", { method: "POST", body: JSON.stringify(body) });
export const deleteConnection = (id: string) => api<void>(`/connections/${id}`, { method: "DELETE" });
export const testConnection = (id: string) =>
  api<{ ok: boolean; detail: string }>(`/connections/${id}/test`, { method: "POST" });
export const connectionTools = (id: string) => api<Ability[]>(`/connections/${id}/tools`);

/** Abilities grouped by desk in the fixed desk order. */
export function byDesk(abilities: Ability[]): [AgentId, Ability[]][] {
  return DESK_ORDER
    .map((desk) => [desk, abilities.filter((a) => a.desk === desk)] as [AgentId, Ability[]])
    .filter(([, list]) => list.length > 0);
}
