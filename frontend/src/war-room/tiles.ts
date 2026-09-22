/**
 * Kenney "Tiny Town" (CC0) tiles used on the office floor, by index in the packed 12 x 11 sheet
 * (index = row * 12 + column). Verified against the sheet visually.
 */
export const SHEET_COLS = 12;
export const SRC_TILE = 16;

export const T = {
  // light stone slab, 9-slice (rows 8-10, cols 0-2)
  floorTL: 96, floorT: 97, floorTR: 98,
  floorL: 108, floorC: 109, floorR: 110,
  floorBL: 120, floorB: 121, floorBR: 122,
  // wooden wall: upper row 72-75, lower row with window / door 84-85
  wallLeft: 72, wallPlain: 73, wallRight: 75, wallWindow: 84, wallDoor: 85,
  // plants and props
  bush: 5,
  smallTree: 16,
  sprout: 17,
  sign: 83,
  target: 95,
  basket: 107,
  bucket: 130,
  waterBucket: 131,
} as const;

export function tileSource(index: number): { sx: number; sy: number } {
  return { sx: (index % SHEET_COLS) * SRC_TILE, sy: Math.floor(index / SHEET_COLS) * SRC_TILE };
}
