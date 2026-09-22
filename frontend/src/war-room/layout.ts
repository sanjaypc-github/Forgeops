/**
 * The office floor plan in 16 px tiles: where furniture stands, where each person sits,
 * and how they walk between places (shortest path on the tile grid, around furniture).
 */
import type { Persona } from "./personas";

export const TILE = 16;
export const COLS = 40;
export const ROWS = 24;
export const WIDTH = COLS * TILE;
export const HEIGHT = ROWS * TILE;

export interface Cell {
  x: number;
  y: number;
}

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export type Place = Persona | "whiteboard" | "evidenceWall" | "rcaBoard" | "door";

export interface Spot {
  /** Where the person stands or sits. */
  seat: Cell;
  /** Where a visiting colleague stands to talk. */
  visit?: Cell;
  /** Extra standing positions (evidence wall). */
  slots?: Cell[];
}

export interface DeskPiece {
  owner: Persona;
  /** Desk top, in tiles (blocked). */
  rect: Rect;
}

/** Desks: the character sits on the row just below the desk, facing it. */
export const DESKS: DeskPiece[] = [
  { owner: "supervisor", rect: { x: 3, y: 4, w: 4, h: 2 } },
  { owner: "rca", rect: { x: 33, y: 4, w: 4, h: 2 } },
  { owner: "code", rect: { x: 4, y: 9, w: 4, h: 2 } },
  { owner: "frontend_hosting", rect: { x: 16, y: 9, w: 4, h: 2 } },
  { owner: "backend_services", rect: { x: 28, y: 9, w: 4, h: 2 } },
  { owner: "database", rect: { x: 4, y: 15, w: 4, h: 2 } },
  { owner: "observability", rect: { x: 16, y: 15, w: 4, h: 2 } },
  { owner: "knowledge", rect: { x: 28, y: 15, w: 4, h: 2 } },
  { owner: "action", rect: { x: 4, y: 19, w: 4, h: 2 } },
  { owner: "human", rect: { x: 32, y: 19, w: 4, h: 2 } },
];

/** Wall-mounted boards along the top wall (row 2 is blocked under them). */
export const BOARDS: Record<"whiteboard" | "evidenceWall" | "rcaBoard", Rect> = {
  whiteboard: { x: 2, y: 2, w: 6, h: 1 },
  evidenceWall: { x: 13, y: 2, w: 14, h: 1 },
  rcaBoard: { x: 32, y: 2, w: 6, h: 1 },
};

/** Decorative furniture that also blocks walking. */
export const PROPS: { kind: "plant" | "shelf" | "crate" | "cooler" | "sign"; cell: Cell }[] = [
  { kind: "plant", cell: { x: 1, y: 3 } },
  { kind: "plant", cell: { x: 38, y: 3 } },
  { kind: "plant", cell: { x: 12, y: 9 } },
  { kind: "plant", cell: { x: 24, y: 9 } },
  { kind: "plant", cell: { x: 12, y: 15 } },
  { kind: "plant", cell: { x: 24, y: 15 } },
  { kind: "shelf", cell: { x: 33, y: 15 } },
  { kind: "shelf", cell: { x: 34, y: 15 } },
  { kind: "crate", cell: { x: 9, y: 20 } },
  { kind: "crate", cell: { x: 9, y: 21 } },
  { kind: "cooler", cell: { x: 38, y: 12 } },
  { kind: "sign", cell: { x: 2, y: 21 } },
];

export const DOOR: Cell = { x: 1, y: 22 };

const seatBelow = (owner: Persona): Cell => {
  const desk = DESKS.find((d) => d.owner === owner)!;
  return { x: desk.rect.x + 1, y: desk.rect.y + desk.rect.h };
};
const visitBeside = (owner: Persona): Cell => {
  const desk = DESKS.find((d) => d.owner === owner)!;
  return { x: desk.rect.x + desk.rect.w, y: desk.rect.y + desk.rect.h };
};

export const SPOTS: Record<Place, Spot> = {
  supervisor: { seat: seatBelow("supervisor"), visit: visitBeside("supervisor") },
  code: { seat: seatBelow("code"), visit: visitBeside("code") },
  frontend_hosting: { seat: seatBelow("frontend_hosting"), visit: visitBeside("frontend_hosting") },
  backend_services: { seat: seatBelow("backend_services"), visit: visitBeside("backend_services") },
  database: { seat: seatBelow("database"), visit: visitBeside("database") },
  observability: { seat: seatBelow("observability"), visit: visitBeside("observability") },
  knowledge: { seat: seatBelow("knowledge"), visit: visitBeside("knowledge") },
  rca: { seat: seatBelow("rca"), visit: visitBeside("rca") },
  action: { seat: seatBelow("action"), visit: visitBeside("action") },
  human: { seat: seatBelow("human"), visit: visitBeside("human") },
  whiteboard: { seat: { x: 5, y: 3 } },
  evidenceWall: {
    seat: { x: 20, y: 3 },
    slots: [14, 16, 18, 20, 22, 24].map((x) => ({ x, y: 3 })),
  },
  rcaBoard: { seat: { x: 35, y: 3 } },
  door: { seat: DOOR },
};

// ─── walkability ───────────────────────────────────────────────────────────────
const blocked = new Set<string>();
const key = (c: Cell) => `${c.x},${c.y}`;
const blockRect = (r: Rect) => {
  for (let y = r.y; y < r.y + r.h; y++) for (let x = r.x; x < r.x + r.w; x++) blocked.add(`${x},${y}`);
};
for (const d of DESKS) blockRect(d.rect);
for (const b of Object.values(BOARDS)) blockRect(b);
for (const p of PROPS) blocked.add(key(p.cell));

export function isWalkable(c: Cell): boolean {
  if (c.x === DOOR.x && c.y === DOOR.y) return true;
  // walls: rows 0-1 (top wall), last row, first and last column
  if (c.y <= 1 || c.y >= ROWS - 1 || c.x <= 0 || c.x >= COLS - 1) return false;
  return !blocked.has(key(c));
}

/** Shortest 4-neighbour path from a to b, inclusive; [] when unreachable. */
export function findPath(a: Cell, b: Cell): Cell[] {
  if (a.x === b.x && a.y === b.y) return [a];
  const prev = new Map<string, Cell | null>([[key(a), null]]);
  const queue: Cell[] = [a];
  while (queue.length) {
    const cur = queue.shift()!;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]] as const) {
      const next = { x: cur.x + dx, y: cur.y + dy };
      const k = key(next);
      if (prev.has(k) || !isWalkable(next)) continue;
      prev.set(k, cur);
      if (next.x === b.x && next.y === b.y) {
        const path: Cell[] = [next];
        let back: Cell | null | undefined = cur;
        while (back) {
          path.unshift(back);
          back = prev.get(key(back));
        }
        return path;
      }
      queue.push(next);
    }
  }
  return [];
}

/** Corners only: the points where the path changes direction (plus the ends). */
export function waypoints(path: Cell[]): Cell[] {
  if (path.length <= 2) return path;
  const out: Cell[] = [path[0]];
  for (let i = 1; i < path.length - 1; i++) {
    const [p, c, n] = [path[i - 1], path[i], path[i + 1]];
    if (c.x - p.x !== n.x - c.x || c.y - p.y !== n.y - c.y) out.push(c);
  }
  out.push(path.at(-1)!);
  return out;
}
