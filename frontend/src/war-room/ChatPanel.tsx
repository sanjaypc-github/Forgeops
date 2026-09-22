import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Check, ExternalLink, FileText, Send, X, Search } from "lucide-react";
import { Link } from "react-router";
import { ApiError } from "../api/client";
import type { OfficeState, TimelineEntry } from "./officeState";
import { PERSONAS } from "./personas";

interface Props {
  investigationId: string | null;
  state: OfficeState;
  onSend: (text: string) => Promise<void>;
  onDecide: (kind: "approve" | "reject" | "investigate_more", ids: string[], note?: string) => Promise<void>;
}

const PLACEHOLDER_NEW = "What's broken? For example: “Checkout got slow after this morning's deploy”";

function PlanCard({ state }: { state: OfficeState }) {
  if (!state.plan) return null;
  return (
    <div className="card card-plan">
      <p className="card-title">Plan</p>
      <p>{state.plan.summary}</p>
      {state.plan.hypotheses.length > 0 && (
        <ul className="hypotheses">{state.plan.hypotheses.map((h) => <li key={h}>{h}</li>)}</ul>
      )}
      <div className="chips">
        {state.plan.tasks.map((t) => (
          <span key={t.agent} className="chip" title={t.objective}>
            <i style={{ background: PERSONAS[t.agent].accent }} />{PERSONAS[t.agent].short}
          </span>
        ))}
      </div>
    </div>
  );
}

function RcaCard({ state, investigationId }: { state: OfficeState; investigationId: string | null }) {
  if (!state.rca) return null;
  const pct = Math.round(state.rca.confidence * 100);
  return (
    <div className="card card-rca">
      <p className="card-title">Root cause</p>
      <p className="rca-summary">{state.rca.summary}</p>
      <dl className="facts">
        <dt>Failure point</dt><dd className="mono">{state.rca.failurePoint}</dd>
        <dt>Confidence</dt><dd><span className="meter"><span style={{ width: `${pct}%` }} /></span>{pct}%</dd>
        <dt>Evidence</dt><dd>{state.rca.supporting.length} supporting finding{state.rca.supporting.length === 1 ? "" : "s"}</dd>
      </dl>
      {state.reportReady && investigationId && (
        <Link className="text-link" to={`/investigations/${investigationId}/report`}><FileText size={15} aria-hidden /> Open the report</Link>
      )}
    </div>
  );
}

function ApprovalCard({ state, onDecide }: { state: OfficeState; onDecide: Props["onDecide"] }) {
  const writable = state.recommendations.filter((r) => r.action !== "none");
  const [picked, setPicked] = useState<string[]>(() => writable.map((r) => r.id));
  const [note, setNote] = useState("");
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const waiting = state.phase === "awaiting_approval";

  async function act(kind: "approve" | "reject" | "investigate_more") {
    setBusy(true);
    setError(null);
    try {
      await onDecide(kind, kind === "approve" ? picked : [], kind === "investigate_more" ? note : undefined);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The decision could not be sent. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card card-approval">
      <p className="card-title">Your decision</p>
      {state.recommendations.length === 0 && <p className="muted">No actions were proposed.</p>}
      <ul className="recs">
        {state.recommendations.map((r) => (
          <li key={r.id}>
            {r.action !== "none" ? (
              <label>
                <input type="checkbox" checked={picked.includes(r.id)} disabled={!waiting || busy}
                       onChange={(e) => setPicked((p) => e.target.checked ? [...p, r.id] : p.filter((x) => x !== r.id))} />
                <span><strong>{r.title}</strong> <span className="tag">{r.action === "github_issue" ? "creates a GitHub issue" : r.action}</span><br />
                  <span className="muted">{r.description}</span></span>
              </label>
            ) : (
              <span><strong>{r.title}</strong><br /><span className="muted">{r.description}</span></span>
            )}
          </li>
        ))}
      </ul>
      {waiting ? (
        <>
          {asking && (
            <div className="note-field">
              <label htmlFor="more-note">What should the team look at?</label>
              <textarea id="more-note" rows={2} value={note} onChange={(e) => setNote(e.target.value)}
                        placeholder="We also changed the cache settings yesterday" />
            </div>
          )}
          <div className="actions">
            {!asking && (
              <button type="button" className="primary" disabled={busy || (writable.length > 0 && picked.length === 0)} onClick={() => act("approve")}>
                <Check size={16} aria-hidden /> {writable.length ? `Approve ${picked.length} action${picked.length === 1 ? "" : "s"}` : "Accept"}
              </button>
            )}
            {!asking && <button type="button" className="secondary" disabled={busy} onClick={() => act("reject")}><X size={16} aria-hidden /> Reject</button>}
            <button type="button" className="secondary" disabled={busy || (asking && !note.trim())}
                    onClick={() => (asking ? act("investigate_more") : setAsking(true))}>
              <Search size={16} aria-hidden /> {asking ? "Send back to the desks" : "Investigate more"}
            </button>
            {asking && <button type="button" className="ghost" onClick={() => setAsking(false)}>Cancel</button>}
          </div>
          {error && <p role="alert" className="error">{error}</p>}
        </>
      ) : (
        <p className="muted">{state.decision ? `Decision recorded: ${state.decision.kind.replace("_", " ")}.` : "Decision closed."}</p>
      )}
    </div>
  );
}

function Entry({ entry, state, investigationId, onDecide }: { entry: TimelineEntry; state: OfficeState; investigationId: string | null; onDecide: Props["onDecide"] }) {
  switch (entry.kind) {
    case "message":
      return (
        <div className={`msg msg-${entry.role}`}>
          <span className="who">{entry.role === "user" ? "You" : "Supervisor"}</span>
          <p>{entry.text}</p>
        </div>
      );
    case "plan":
      return <PlanCard state={state} />;
    case "rca":
      return <RcaCard state={state} investigationId={investigationId} />;
    case "approval":
      return <ApprovalCard state={state} onDecide={onDecide} />;
    case "decision":
      return <p className="event-line">You chose to {entry.decision.replace("_", " ")}{entry.note ? `: “${entry.note}”` : ""}.</p>;
    case "action": {
      const result = state.actions.find((a) => a.recommendationId === entry.recommendationId);
      if (!result) return null;
      return (
        <p className={`event-line ${result.status === "done" ? "good" : "bad"}`}>
          {result.status === "done" ? "Action completed" : `Action ${result.status}: ${result.detail}`}
          {result.url && <> · <a href={result.url} target="_blank" rel="noreferrer">open <ExternalLink size={13} aria-hidden /></a></>}
        </p>
      );
    }
    case "failure":
      return (
        <div className="card card-failure" role="alert">
          <p className="card-title">The investigation stopped</p>
          <p>{entry.reason}</p>
        </div>
      );
  }
}

export function ChatPanel({ investigationId, state, onSend, onDecide }: Props) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const finished = state.phase === "failed";
  const placeholder = !investigationId ? PLACEHOLDER_NEW
    : state.rca ? "Ask the Supervisor a follow-up question" : "Add context for the desks (they read it at review)";

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [state.timeline.length]);

  const entries = useMemo(() => state.timeline, [state.timeline]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = text.trim();
    if (!value) return;
    setBusy(true);
    setError(null);
    try {
      await onSend(value);
      setText("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The message could not be sent. Check that the API is running.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="chat" aria-label="Chat with the Supervisor">
      <div className="chat-scroll" ref={scroller} aria-live="polite">
        {entries.length === 0 && (
          <div className="chat-empty">
            <p className="chat-empty-title">Describe the problem</p>
            <p className="muted">Paste the symptom, an error message or a URL. The Supervisor plans the investigation and the desks start working in parallel.</p>
          </div>
        )}
        {entries.map((entry) => (
          <Entry key={`${entry.kind}-${entry.seq}`} entry={entry} state={state} investigationId={investigationId} onDecide={onDecide} />
        ))}
      </div>
      {finished ? (
        <div className="composer composer-closed">
          <p className="muted">This investigation stopped. <Link to="/">Start a new one</Link>.</p>
        </div>
      ) : (
        <form className="composer" onSubmit={submit}>
          <label htmlFor="chat-input" className="sr-only">Message</label>
          <textarea id="chat-input" rows={3} value={text} placeholder={placeholder} maxLength={4000}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} />
          <button type="submit" className="primary send" disabled={busy || !text.trim()} aria-label="Send">
            <Send size={16} aria-hidden />
          </button>
          {error && <p role="alert" className="error">{error}</p>}
        </form>
      )}
    </section>
  );
}
