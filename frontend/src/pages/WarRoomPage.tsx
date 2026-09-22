import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router";
import { decide, getInvestigation, listDesks, sendChat } from "../api/investigations";
import { useEventStream } from "../investigations/eventStream";
import { ChatPanel } from "../war-room/ChatPanel";
import { Office } from "../war-room/Office";
import { initialOfficeState, reduceEvents, type Phase } from "../war-room/officeState";
import type { Persona } from "../war-room/personas";
import { ActivityPanel, AgentCard, EvidencePanel } from "../war-room/SidePanels";

const PHASE_LABEL: Record<Phase, string> = {
  idle: "Ready", planning: "Planning", investigating: "Investigating", reviewing: "Reviewing evidence",
  analyzing: "Finding the root cause", awaiting_approval: "Waiting for your decision", acting: "Carrying out actions",
  completed: "Complete", rejected: "Closed", failed: "Stopped",
};

const REFETCH_ON = new Set(["rca_completed", "approval_requested", "action_completed", "investigation_completed", "evidence_added"]);

function useClock(start: string | null, end: string | null): string {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!start || end) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [start, end]);
  if (!start) return "00:00";
  const seconds = Math.max(0, Math.floor(((end ? Date.parse(end) : now) - Date.parse(start)) / 1000));
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

type Tab = "chat" | "evidence" | "activity";

export function WarRoomPage() {
  const { id = null } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const desks = useQuery({ queryKey: ["desks"], queryFn: listDesks });
  const stream = useEventStream(id);
  const detail = useQuery({ queryKey: ["investigation", id], queryFn: () => getInvestigation(id!), enabled: !!id });
  const [tab, setTab] = useState<Tab>("chat");
  const [selected, setSelected] = useState<Persona | null>(null);
  const pollTimer = useRef<number | null>(null);

  const state = useMemo(() => reduceEvents(initialOfficeState(desks.data ?? []), stream.events), [desks.data, stream.events]);
  const clock = useClock(state.startedAt, state.endedAt);

  // refresh the evidence/RCA details when the investigation reaches a milestone
  const lastMilestone = [...stream.events].reverse().find((e) => REFETCH_ON.has(e.type))?.seq ?? 0;
  useEffect(() => {
    if (id && lastMilestone) queryClient.invalidateQueries({ queryKey: ["investigation", id] });
  }, [id, lastMilestone, queryClient]);
  useEffect(() => () => { if (pollTimer.current) window.clearInterval(pollTimer.current); }, []);

  async function onSend(text: string) {
    const result = await sendChat(id ? { text, investigation_id: id } : { text });
    if (!id) {
      navigate(`/investigations/${result.investigation_id}`);
      return;
    }
    if (stream.done) {
      // the live stream has ended; pick up the Supervisor's answer as it is stored
      let tries = 0;
      if (pollTimer.current) window.clearInterval(pollTimer.current);
      pollTimer.current = window.setInterval(() => {
        stream.refresh();
        if (++tries >= 20 && pollTimer.current) window.clearInterval(pollTimer.current);
      }, 2000);
    }
  }

  async function onDecide(kind: "approve" | "reject" | "investigate_more", ids: string[], note?: string) {
    if (!id) return;
    await decide(id, { kind, approved_recommendation_ids: ids, note });
    queryClient.invalidateQueries({ queryKey: ["investigation", id] });
  }

  const latest = state.feed.at(-1);
  const live = !!id && !stream.done && stream.connected;

  return (
    <div className="war-room">
      <header className="incident-bar">
        <div className="incident-text">
          <h1>{state.incident ?? "War Room"}</h1>
          <p className="muted">
            {id ? PHASE_LABEL[state.phase] : "Connected desks are ready. Describe a problem to start an investigation."}
            {detail.data?.status === "failed" && state.phase !== "failed" ? " · stopped" : ""}
          </p>
        </div>
        {id && (
          <div className="incident-meta">
            <span className={`status-pill phase-${state.phase}`}>{live && <span className="live-dot" aria-hidden />}{live ? "Live" : PHASE_LABEL[state.phase]}</span>
            <span className="clock" aria-label={`Elapsed ${clock}`}>{clock}</span>
          </div>
        )}
      </header>

      <div className="war-room-grid">
        <div className="office-column">
          <Office state={state} selected={selected} onSelect={setSelected} onOpenEvidence={() => setTab("evidence")} />
          {selected && <AgentCard state={state} id={selected} onClose={() => setSelected(null)} />}
          <p className="ticker" aria-live="polite">
            {latest ? latest.text : desks.isPending ? "Loading desks…" : "The office is quiet."}
          </p>
          <p className="credits muted">Office art: Tiny Town by Kenney (CC0) · character engine adapted from Munder Difflin (MIT)</p>
        </div>

        <aside className="side">
          <div className="tabs" role="tablist" aria-label="War Room panels">
            {(["chat", "evidence", "activity"] as Tab[]).map((t) => (
              <button key={t} type="button" role="tab" aria-selected={tab === t} className={tab === t ? "tab is-active" : "tab"}
                      onClick={() => setTab(t)}>
                {t === "chat" ? "Chat" : t === "evidence" ? `Evidence${state.evidence.length ? ` ${state.evidence.length}` : ""}` : "Activity"}
              </button>
            ))}
          </div>
          <div className="tab-body" role="tabpanel">
            {tab === "chat" && <ChatPanel investigationId={id} state={state} onSend={onSend} onDecide={onDecide} />}
            {tab === "evidence" && <EvidencePanel state={state} details={detail.data?.details ?? null} />}
            {tab === "activity" && <ActivityPanel state={state} />}
          </div>
        </aside>
      </div>
    </div>
  );
}
