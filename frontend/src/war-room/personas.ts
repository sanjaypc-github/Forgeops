import type { AgentId } from "../api/types";

export type Persona = AgentId | "human";

export interface PersonaInfo {
  id: Persona;
  /** Desk name shown on the name plate. */
  title: string;
  /** Short label for tight spots (bubbles, feed). */
  short: string;
  /** Accent: matches the character's outfit, used for the desk lamp, feed chips and cards. */
  accent: string;
}

export const PERSONAS: Record<Persona, PersonaInfo> = {
  supervisor: { id: "supervisor", title: "Supervisor", short: "Supervisor", accent: "#2c3a60" },
  code: { id: "code", title: "Code", short: "Code", accent: "#1f7f83" },
  frontend_hosting: { id: "frontend_hosting", title: "Frontend & Hosting", short: "Frontend", accent: "#c4621f" },
  backend_services: { id: "backend_services", title: "Backend & Services", short: "Backend", accent: "#6f4fa8" },
  database: { id: "database", title: "Database", short: "Database", accent: "#2f7d4f" },
  observability: { id: "observability", title: "Observability", short: "Observability", accent: "#b43c3c" },
  knowledge: { id: "knowledge", title: "Knowledge", short: "Knowledge", accent: "#9a7418" },
  rca: { id: "rca", title: "RCA analyst", short: "RCA", accent: "#3f4150" },
  action: { id: "action", title: "Action", short: "Action", accent: "#2f5fb4" },
  human: { id: "human", title: "You", short: "You", accent: "#5c616b" },
};

export const SPECIALISTS: AgentId[] = [
  "code", "frontend_hosting", "backend_services", "database", "observability", "knowledge",
];

export function isAgentId(value: string | null | undefined): value is AgentId {
  return !!value && value in PERSONAS && value !== "human";
}
