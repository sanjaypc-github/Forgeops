import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Navigate, useLocation } from "react-router";
import { fetchMe } from "../api/auth";

export const ME_QUERY_KEY = ["me"] as const;

export function useMe() {
  return useQuery({ queryKey: ME_QUERY_KEY, queryFn: fetchMe, retry: false, staleTime: 60_000 });
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { data, isPending, isError } = useMe();
  const location = useLocation();
  if (isPending) return <p className="muted pad">Loading…</p>;
  if (isError) return <p className="error pad">Could not reach ForgeOps. Check that the API is running.</p>;
  if (!data) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}
