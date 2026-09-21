import { api, ApiError, setCsrfToken } from "./client";
import type { Me } from "./types";

export async function login(email: string, password: string): Promise<Me> {
  const me = await api<Me>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setCsrfToken(me.csrf_token);
  return me;
}

export async function fetchMe(): Promise<Me | null> {
  try {
    const me = await api<Me>("/auth/me");
    setCsrfToken(me.csrf_token);
    return me;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

export async function logout(): Promise<void> {
  await api<void>("/auth/logout", { method: "POST" });
  setCsrfToken(null);
}
