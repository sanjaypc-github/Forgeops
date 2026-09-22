import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { findPath, waypoints, type Cell } from "./layout";
import type { AgentView } from "./officeState";
import { PERSONAS } from "./personas";
import { WALK_MS_PER_TILE, spritePosition, standCell } from "./placement";
import { sceneFrameUrl } from "./art/portraitArt";

const MODE_LABEL: Record<AgentView["mode"], string> = {
  offline: "no connector", idle: "idle", skipped: "not needed", assigned: "assigned", working: "working",
  calling: "using a tool", asking: "asking a colleague", answering: "answering a colleague",
  done: "done", failed: "failed",
};

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

interface Props {
  agent: AgentView;
  selected: boolean;
  onSelect: (id: AgentView["id"]) => void;
}

export function AgentSprite({ agent, selected, onSelect }: Props) {
  const persona = PERSONAS[agent.id];
  const target = standCell(agent.id, agent.location);
  const seated = agent.location === agent.id;
  const ref = useRef<HTMLButtonElement>(null);
  const [cell, setCell] = useState<Cell>(target);
  const [walking, setWalking] = useState(false);
  const [facing, setFacing] = useState<"front" | "back">(seated ? "back" : "front");
  const [phase, setPhase] = useState<0 | 1 | 2>(0);

  // Walk to the new place along the corridors (or jump when motion is reduced).
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || (cell.x === target.x && cell.y === target.y)) return;
    const points = waypoints(findPath(cell, target));
    if (prefersReducedMotion() || points.length < 2 || typeof el.animate !== "function") {
      setCell(target);
      return;
    }
    const tiles = points.slice(1).reduce((n, p, i) => n + Math.abs(p.x - points[i].x) + Math.abs(p.y - points[i].y), 0);
    const frames = points.map((p) => {
      const { x, y } = spritePosition(p);
      return { transform: `translate(${x}px, ${y}px)` };
    });
    setWalking(true);
    setFacing(target.y < cell.y ? "back" : "front");
    const animation = el.animate(frames, { duration: tiles * WALK_MS_PER_TILE, easing: "linear" });
    animation.onfinish = () => {
      setCell(target);
      setWalking(false);
    };
    return () => animation.cancel();
  }, [target.x, target.y]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!walking) {
      setPhase(0);
      setFacing(seated ? "back" : "front");
      return;
    }
    const timer = window.setInterval(() => setPhase((p) => (p === 1 ? 2 : 1)), 140);
    return () => window.clearInterval(timer);
  }, [walking, seated]);

  const { x, y } = spritePosition(cell);
  const src = sceneFrameUrl(agent.id, facing, phase);
  const busy = agent.mode === "working" || agent.mode === "calling" || agent.mode === "asking" || agent.mode === "answering";

  return (
    <button
      ref={ref}
      type="button"
      className={`sprite mode-${agent.mode}${selected ? " is-selected" : ""}${busy && !walking ? " is-busy" : ""}`}
      style={{ transform: `translate(${x}px, ${y}px)` }}
      onClick={() => onSelect(agent.id)}
      aria-label={`${persona.title}: ${MODE_LABEL[agent.mode]}${agent.objective ? `. ${agent.objective}` : ""}`}
      aria-pressed={selected}
    >
      {src ? <img src={src} alt="" width={18} height={32} draggable={false} /> : <span className="sprite-fallback" />}
      {agent.bubble && !walking && (
        <span className={`bubble bubble-${agent.bubble.kind}`} key={agent.bubble.seq}>
          {agent.bubble.text}
        </span>
      )}
    </button>
  );
}
