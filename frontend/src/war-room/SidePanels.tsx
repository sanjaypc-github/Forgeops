import { ExternalLink } from "lucide-react";
import type { InvestigationDetails } from "../api/investigations";
import type { OfficeState } from "./officeState";
import { PERSONAS, isAgentId } from "./personas";

const time = (ts: string) => new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export function EvidencePanel({ state, details }: { state: OfficeState; details: InvestigationDetails | null }) {
  const full = new Map((details?.evidence ?? []).map((e) => [e.id, e]));
  if (state.evidence.length === 0) {
    return <p className="panel-empty muted">No evidence yet. Findings appear here as the desks report them, each linked to the tool call behind it.</p>;
  }
  const supporting = new Set(state.rca?.supporting ?? []);
  return (
    <ol className="evidence-list">
      {state.evidence.map((card) => {
        const detail = full.get(card.id);
        const persona = PERSONAS[card.agent];
        return (
          <li key={card.id} className={`evidence sev-${card.severity}`}>
            <div className="evidence-head">
              <span className="chip"><i style={{ background: persona.accent }} />{persona.short}</span>
              <span className="tag">{card.connector}</span>
              <span className={`sev sev-${card.severity}`}>{card.severity}</span>
              {supporting.has(card.id) && <span className="tag tag-support">supports root cause</span>}
              <span className="conf">{Math.round(card.confidence * 100)}%</span>
            </div>
            <p className="evidence-finding">{card.finding}</p>
            {card.failurePoint && <p className="mono failure-point">{card.failurePoint}</p>}
            {detail?.artifacts.length ? (
              <ul className="artifacts">
                {detail.artifacts.map((a, i) => (
                  <li key={`${a.ref}-${i}`}>
                    <span className="tag">{a.type.replace("_", " ")}</span>{" "}
                    {a.url ? <a href={a.url} target="_blank" rel="noreferrer" className="mono">{a.ref} <ExternalLink size={12} aria-hidden /></a>
                           : <span className="mono">{a.ref}</span>}
                    {a.excerpt && <pre className="excerpt">{a.excerpt}</pre>}
                  </li>
                ))}
              </ul>
            ) : null}
            {detail?.limitations && <p className="muted small">Limitations: {detail.limitations}</p>}
            <p className="muted small mono">{card.id}{detail ? ` · from ${detail.tool_call_ids.join(", ")}` : ""}</p>
          </li>
        );
      })}
    </ol>
  );
}

export function ActivityPanel({ state }: { state: OfficeState }) {
  if (state.feed.length === 0) return <p className="panel-empty muted">Every plan, tool call, question and finding is listed here as it happens.</p>;
  return (
    <ol className="feed">
      {state.feed.slice().reverse().map((item) => (
        <li key={item.seq} className={`feed-${item.tone}`}>
          <time className="mono">{time(item.ts)}</time>
          {item.agent && isAgentId(item.agent) ? (
            <span className="chip"><i style={{ background: PERSONAS[item.agent].accent }} />{PERSONAS[item.agent].short}</span>
          ) : item.agent === "human" ? <span className="chip">You</span> : <span className="chip chip-system">ForgeOps</span>}
          <span className="feed-text">{item.text}</span>
        </li>
      ))}
    </ol>
  );
}

export function AgentCard({ state, id, onClose }: { state: OfficeState; id: keyof OfficeState["agents"]; onClose: () => void }) {
  const view = state.agents[id];
  const persona = PERSONAS[id];
  const asked = state.questions.filter((q) => q.from === id || q.to === id);
  return (
    <div className="agent-card" role="dialog" aria-label={`${persona.title} desk`}>
      <div className="agent-card-head">
        <span className="chip"><i style={{ background: persona.accent }} />{persona.title}</span>
        <button type="button" className="ghost small" onClick={onClose}>Close</button>
      </div>
      <p><strong>Status:</strong> {view.mode.replace("_", " ")}{view.skippedReason ? ` (${view.skippedReason})` : ""}</p>
      {view.objective && <p><strong>Task:</strong> {view.objective}</p>}
      <p className="muted">{view.toolCalls} tool call{view.toolCalls === 1 ? "" : "s"} · {view.findings} finding{view.findings === 1 ? "" : "s"}</p>
      {view.error && <p className="error">{view.error}</p>}
      {asked.length > 0 && (
        <ul className="qa">
          {asked.map((q) => (
            <li key={q.id}><strong>{PERSONAS[q.from].short} → {PERSONAS[q.to].short}:</strong> {q.question}
              {q.answer && <span className="muted"> — {q.answer}</span>}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
