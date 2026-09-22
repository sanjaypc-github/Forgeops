import { useEffect, useMemo, useRef, useState } from "react";
import { BOARDS, DESKS, HEIGHT, TILE, WIDTH } from "./layout";
import { paintFloor } from "./floor";
import type { OfficeState } from "./officeState";
import { PERSONAS, type Persona } from "./personas";
import { AgentSprite } from "./AgentSprite";
import { standCell } from "./placement";
import sheetUrl from "./assets/tiny-town.png";

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

function useStageScale(ref: React.RefObject<HTMLDivElement | null>): number {
  const [scale, setScale] = useState(1.5);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => {
      const raw = entry.contentRect.width / WIDTH;
      // quarter steps keep pixels even; never shrink below 0.75 (the viewport scrolls instead)
      setScale(Math.max(0.75, Math.floor(raw * 4) / 4));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return scale;
}

function FloorCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext?.("2d");
    if (!canvas || !ctx) return;
    const sheet = new Image();
    sheet.onload = () => paintFloor(ctx, sheet);
    sheet.src = sheetUrl;
  }, []);
  return <canvas ref={ref} className="floor" width={WIDTH} height={HEIGHT} aria-hidden="true" />;
}

interface Props {
  state: OfficeState;
  selected: Persona | null;
  onSelect: (id: Persona | null) => void;
  onOpenEvidence: () => void;
}

export function Office({ state, selected, onSelect, onOpenEvidence }: Props) {
  const viewport = useRef<HTMLDivElement>(null);
  const scale = useStageScale(viewport);
  // draw people further down the room in front of people further up
  const people = useMemo(
    () => (Object.values(state.agents)).slice().sort(
      (a, b) => standCell(a.id, a.location).y - standCell(b.id, b.location).y),
    [state.agents],
  );
  const cards = useMemo(
    () => state.evidence.slice().sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)).slice(0, 12),
    [state.evidence],
  );
  const wb = BOARDS.whiteboard, ev = BOARDS.evidenceWall, rb = BOARDS.rcaBoard;

  return (
    <div className="office-viewport" ref={viewport}>
      <div className="office-stage" style={{ width: WIDTH, height: HEIGHT, zoom: scale }}
           role="group" aria-label="War Room office floor">
        <FloorCanvas />

        {/* whiteboard: the Supervisor's plan */}
        <div className="board board-plan" style={{ left: wb.x * TILE + 6, top: wb.y * TILE - 8, width: wb.w * TILE - 12 }}>
          {state.plan ? (
            <>
              <strong>Plan</strong>
              {state.plan.tasks.slice(0, 2).map((t) => (
                <span key={t.agent} className="plan-line"><i style={{ background: PERSONAS[t.agent].accent }} />{PERSONAS[t.agent].short}</span>
              ))}
              {state.plan.tasks.length > 2 && <span className="plan-line">+{state.plan.tasks.length - 2}</span>}
            </>
          ) : <span className="board-empty">No plan yet</span>}
        </div>

        {/* evidence wall: pinned findings */}
        <button type="button" className="board board-evidence" onClick={onOpenEvidence}
                style={{ left: ev.x * TILE + 4, top: ev.y * TILE - 8, width: ev.w * TILE - 8 }}
                aria-label={`Evidence wall: ${state.evidence.length} finding${state.evidence.length === 1 ? "" : "s"}. Open the evidence list.`}>
          {cards.length === 0 && <span className="board-empty">Evidence will be pinned here</span>}
          {cards.map((card, i) => (
            <span key={card.id} className={`pin sev-${card.severity}`} title={card.finding}
                  style={{ borderTopColor: PERSONAS[card.agent].accent, transform: `rotate(${(i % 3) - 1}deg)` }} />
          ))}
        </button>

        {/* RCA board */}
        <div className="board board-rca" style={{ left: rb.x * TILE + 6, top: rb.y * TILE - 8, width: rb.w * TILE - 12 }}>
          {state.rca ? (
            <>
              <strong>Root cause · {Math.round(state.rca.confidence * 100)}%</strong>
              <span>{state.rca.failurePoint}</span>
            </>
          ) : <span className="board-empty">Awaiting analysis</span>}
        </div>

        {/* desks: live monitor, lamp and name plate */}
        {DESKS.map((desk) => {
          const view = state.agents[desk.owner];
          const persona = PERSONAS[desk.owner];
          return (
            <div key={desk.owner} className={`desk desk-${view.mode}`}
                 style={{ left: desk.rect.x * TILE, top: desk.rect.y * TILE, width: desk.rect.w * TILE }}>
              <span className="monitor" style={{ ["--accent" as string]: persona.accent }}>
                <span className="screen" />
              </span>
              <span className="plate">
                <span className="lamp" style={{ background: persona.accent }} />
                {persona.short}
                {view.mode === "offline" && <em> · no connector</em>}
                {view.findings > 0 && <b> {view.findings}</b>}
              </span>
            </div>
          );
        })}

        {people.map((agent) => (
          <AgentSprite key={agent.id} agent={agent} selected={selected === agent.id}
                       onSelect={(id) => onSelect(selected === id ? null : id)} />
        ))}
      </div>
    </div>
  );
}
