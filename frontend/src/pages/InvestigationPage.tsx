import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router";
import { getInvestigation } from "../api/investigations";
import { useEventStream } from "../investigations/eventStream";

export function InvestigationPage() {
  const { id = "" } = useParams();
  const investigation = useQuery({ queryKey: ["investigation", id], queryFn: () => getInvestigation(id) });
  const stream = useEventStream(id);

  if (investigation.isPending) return <p className="muted">Loading…</p>;
  if (investigation.isError) return <p className="error">Investigation not found.</p>;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <header style={{ display: "grid", gap: 6 }}>
        <h1>{investigation.data.description}</h1>
        <p className="muted">
          {stream.done ? "Finished" : stream.connected ? "Live" : "Connecting…"} · {stream.events.length} events
        </p>
      </header>
      <section aria-labelledby="events-title">
        <h2 id="events-title" style={{ fontSize: "1rem", marginBottom: 8 }}>Event log</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>#</th><th>Time</th><th>Event</th><th>Agent</th><th>Details</th></tr></thead>
            <tbody>
              {stream.events.map((e) => (
                <tr key={e.seq}>
                  <td className="mono">{e.seq}</td>
                  <td className="mono">{new Date(e.ts).toLocaleTimeString()}</td>
                  <td className="mono">{e.type}</td>
                  <td>{e.agent ?? "—"}</td>
                  <td className="mono">{JSON.stringify(e.data)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
