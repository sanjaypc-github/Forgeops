import { api } from "./client";
import type { Investigation } from "./types";

export const listInvestigations = () => api<Investigation[]>("/investigations");
export const getInvestigation = (id: string) => api<Investigation>(`/investigations/${id}`);
export const createInvestigation = (body: { description: string }) =>
  api<Investigation>("/investigations", { method: "POST", body: JSON.stringify(body) });
