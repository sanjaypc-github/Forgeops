import { SPOTS, TILE, type Cell, type Place } from "./layout";
import { PERSONAS, type Persona } from "./personas";

const ORDER = Object.keys(PERSONAS) as Persona[];

/** The cell a person stands on for a given location. */
export function standCell(person: Persona, location: Place): Cell {
  if (location === person) return SPOTS[person].seat;
  const spot = SPOTS[location];
  if (spot.slots?.length) return spot.slots[ORDER.indexOf(person) % spot.slots.length];
  return spot.visit ?? spot.seat;
}

/** Sprite top-left in native pixels for a cell (18 x 32 sprite, feet on the cell's bottom edge). */
export function spritePosition(cell: Cell): { x: number; y: number } {
  return { x: cell.x * TILE - 1, y: cell.y * TILE - 17 };
}

export const WALK_MS_PER_TILE = 130;
