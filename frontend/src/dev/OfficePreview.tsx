/**
 * Development-only visual harness for the office (never built into production: see App.tsx).
 * It holds no data of its own; during development, events can be pushed from the browser console with
 * `window.__officeEvents(events)` to check rendering and animation.
 */
import { useEffect, useMemo, useState } from "react";
import type { InvestigationEvent } from "../api/types";
import { ChatPanel } from "../war-room/ChatPanel";
import { Office } from "../war-room/Office";
import { initialOfficeState, reduceEvents } from "../war-room/officeState";
import type { Persona } from "../war-room/personas";
import { ActivityPanel, EvidencePanel } from "../war-room/SidePanels";

declare global {
  interface Window { __officeEvents?: (events: InvestigationEvent[]) => void }
}

export function OfficePreview() {
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [selected, setSelected] = useState<Persona | null>(null);
  const [tab, setTab] = useState<"chat" | "evidence" | "activity">("chat");
  useEffect(() => {
    window.__officeEvents = (next) => setEvents((prev) => [...prev, ...next]);
    return () => { delete window.__officeEvents; };
  }, []);
  const state = useMemo(() => reduceEvents(initialOfficeState([]), events), [events]);
  return (
    <div className="content">
      <div className="war-room">
        <header className="incident-bar"><div className="incident-text"><h1>{state.incident ?? "Office preview (development only)"}</h1>
          <p className="muted">{state.phase}</p></div><span className="clock">00:00</span></header>
        <div className="war-room-grid">
          <div className="office-column">
            <Office state={state} selected={selected} onSelect={setSelected} onOpenEvidence={() => setTab("evidence")} />
            <p className="ticker">{state.feed.at(-1)?.text ?? "The office is quiet."}</p>
          </div>
          <aside className="side">
            <div className="tabs">{(["chat", "evidence", "activity"] as const).map((t) =>
              <button key={t} className={tab === t ? "tab is-active" : "tab"} onClick={() => setTab(t)}>{t}</button>)}</div>
            <div className="tab-body">
              {tab === "chat" && <ChatPanel investigationId={null} state={state} onSend={async () => {}} onDecide={async () => {}} />}
              {tab === "evidence" && <EvidencePanel state={state} details={null} />}
              {tab === "activity" && <ActivityPanel state={state} />}
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
