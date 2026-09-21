import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { ApiError } from "../api/client";
import { createInvestigation, listInvestigations } from "../api/investigations";

export function InvestigationsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [description, setDescription] = useState("");
  const investigations = useQuery({ queryKey: ["investigations"], queryFn: listInvestigations });
  const create = useMutation({
    mutationFn: createInvestigation,
    onSuccess: (inv) => {
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
      navigate(`/investigations/${inv.id}`);
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate({ description });
  }

  return (
    <div style={{ display: "grid", gap: 28 }}>
      <section aria-labelledby="new-title" style={{ display: "grid", gap: 10 }}>
        <h1 id="new-title">New investigation</h1>
        <form onSubmit={onSubmit} style={{ display: "grid", gap: 10 }}>
          <label htmlFor="description">What is happening?</label>
          <textarea id="description" rows={3} required minLength={3} maxLength={4000}
            placeholder="Checkout API latency increased after the last deployment"
            value={description} onChange={(e) => setDescription(e.target.value)} />
          {create.isError && (
            <p role="alert" className="error">
              {create.error instanceof ApiError ? create.error.message : "Could not start the investigation."}
            </p>
          )}
          <div><button type="submit" disabled={create.isPending}>
            {create.isPending ? "Starting…" : "Start investigation"}
          </button></div>
        </form>
      </section>

      <section aria-labelledby="list-title" style={{ display: "grid", gap: 10 }}>
        <h2 id="list-title">Recent investigations</h2>
        {investigations.isPending && <p className="muted">Loading…</p>}
        {investigations.isError && <p className="error">Could not load investigations.</p>}
        {investigations.data?.length === 0 && <p className="muted">No investigations yet.</p>}
        {!!investigations.data?.length && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Incident</th><th>Status</th><th>Source</th><th>Started</th></tr></thead>
              <tbody>
                {investigations.data.map((inv) => (
                  <tr key={inv.id}>
                    <td><Link to={`/investigations/${inv.id}`}>{inv.description}</Link></td>
                    <td><span className={`pill ${inv.status}`}>{inv.status.replace("_", " ")}</span></td>
                    <td>{inv.source}</td>
                    <td className="mono">{new Date(inv.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
