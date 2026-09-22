import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { listInvestigations } from "../api/investigations";

export function InvestigationsPage() {
  const investigations = useQuery({ queryKey: ["investigations"], queryFn: listInvestigations });

  return (
    <section aria-labelledby="history-title" style={{ display: "grid", gap: 12, maxWidth: 1100, margin: "0 auto" }}>
      <h1 id="history-title" style={{ fontSize: "1.375rem" }}>Investigation history</h1>
      {investigations.isPending && <p className="muted">Loading…</p>}
      {investigations.isError && <p className="error">Could not load investigations. Check that the API is running.</p>}
      {investigations.data?.length === 0 && (
        <p className="muted">No investigations yet. Describe a problem in the <Link to="/">War Room</Link> chat to start one.</p>
      )}
      {!!investigations.data?.length && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Problem</th><th>Status</th><th>Started from</th><th>Started</th></tr></thead>
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
  );
}
