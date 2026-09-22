import { expect, test } from "vitest";
import { COLS, ROWS, isWalkable, SPOTS, findPath, type Cell } from "./layout";
import { PERSONAS, type Persona } from "./personas";

const allSpots = (): Cell[] => Object.values(SPOTS).flatMap((s) => [s.seat, ...(s.visit ? [s.visit] : [])]);

test("every persona has a seat on a walkable cell inside the room", () => {
  for (const persona of Object.keys(PERSONAS) as Persona[]) {
    const { seat } = SPOTS[persona];
    expect(seat.x).toBeGreaterThan(0);
    expect(seat.x).toBeLessThan(COLS - 1);
    expect(seat.y).toBeGreaterThan(1);
    expect(seat.y).toBeLessThan(ROWS - 1);
    expect(isWalkable(seat)).toBe(true);
  }
});

test("paths exist between every pair of spots and never cross furniture", () => {
  const spots = allSpots();
  for (const a of spots) {
    for (const b of spots) {
      const path = findPath(a, b);
      expect(path.length, `${a.x},${a.y} -> ${b.x},${b.y}`).toBeGreaterThan(0);
      expect(path[0]).toEqual(a);
      expect(path.at(-1)).toEqual(b);
      for (const cell of path) expect(isWalkable(cell)).toBe(true);
      for (let i = 1; i < path.length; i++) {
        const step = Math.abs(path[i].x - path[i - 1].x) + Math.abs(path[i].y - path[i - 1].y);
        expect(step).toBe(1);
      }
    }
  }
});

test("path between the same cell is just that cell", () => {
  const seat = SPOTS.code.seat;
  expect(findPath(seat, seat)).toEqual([seat]);
});

test("evidence wall offers several standing slots", () => {
  expect(SPOTS.evidenceWall.slots?.length).toBeGreaterThanOrEqual(5);
  for (const slot of SPOTS.evidenceWall.slots ?? []) expect(isWalkable(slot)).toBe(true);
});
