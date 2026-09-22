/**
 * Draws the static office floor (walls, floor, desks, chairs, boards, props) at native size.
 * Kenney Tiny Town tiles for the building; office furniture drawn here in the same pixel style.
 */
import { BOARDS, COLS, DESKS, DOOR, PROPS, ROWS, SPOTS, TILE, type Rect } from "./layout";
import { T, tileSource } from "./tiles";

type Ctx = CanvasRenderingContext2D;

const C = {
  outline: "#2b2430",
  woodTop: "#b9804b",
  woodTopHi: "#cf9860",
  woodFront: "#8a5733",
  woodDark: "#6b4127",
  chair: "#3d4350",
  chairHi: "#565e70",
  keyboard: "#d9dde4",
  paper: "#f5f2ea",
  whiteboard: "#f4f6f8",
  frame: "#8d96a3",
  cork: "#c79c68",
  corkDot: "#b3875a",
  slate: "#2f4a42",
  slateHi: "#3c5a51",
  trim: "#5a3a26",
  trimHi: "#74502f",
  shadow: "rgba(43,36,48,0.18)",
};

function tile(ctx: Ctx, sheet: CanvasImageSource, index: number, cx: number, cy: number): void {
  const { sx, sy } = tileSource(index);
  ctx.drawImage(sheet, sx, sy, 16, 16, cx * TILE, cy * TILE, TILE, TILE);
}

function px(ctx: Ctx, color: string, x: number, y: number, w: number, h: number): void {
  ctx.fillStyle = color;
  ctx.fillRect(x, y, w, h);
}

function drawFloor(ctx: Ctx, sheet: CanvasImageSource): void {
  const top = 2, bottom = ROWS - 2, left = 1, right = COLS - 2;
  for (let y = top; y <= bottom; y++) {
    for (let x = left; x <= right; x++) {
      const v = y === top ? "T" : y === bottom ? "B" : "";
      const h = x === left ? "L" : x === right ? "R" : "";
      const name = (v || h ? `floor${v}${h}` : "floorC") as keyof typeof T;
      tile(ctx, sheet, (T[name] ?? T.floorC) as number, x, y);
    }
  }
}

function drawWalls(ctx: Ctx, sheet: CanvasImageSource): void {
  for (let x = 0; x < COLS; x++) {
    tile(ctx, sheet, x === 0 ? T.wallLeft : x === COLS - 1 ? T.wallRight : T.wallPlain, x, 0);
    const window = x % 5 === 3 && !(x >= 12 && x <= 27);
    tile(ctx, sheet, window ? T.wallWindow : T.wallPlain, x, 1);
    tile(ctx, sheet, T.wallPlain, x, ROWS - 1);
  }
  tile(ctx, sheet, T.target, 10, 1); // dartboard on the wall
  tile(ctx, sheet, T.wallDoor, DOOR.x, ROWS - 1);
  // side walls: wooden trim
  for (const x of [0, COLS - 1]) {
    for (let y = 2; y < ROWS - 1; y++) {
      px(ctx, C.trim, x * TILE, y * TILE, TILE, TILE);
      px(ctx, C.trimHi, x * TILE + (x === 0 ? 11 : 2), y * TILE, 3, TILE);
    }
  }
}

function frameRect(ctx: Ctx, r: Rect, pad: number, frame: string, fill: string): { x: number; y: number; w: number; h: number } {
  const x = r.x * TILE + pad, y = r.y * TILE - 10, w = r.w * TILE - pad * 2, h = 24;
  px(ctx, C.shadow, x + 1, y + 2, w, h);
  px(ctx, C.outline, x - 1, y - 1, w + 2, h + 2);
  px(ctx, frame, x, y, w, h);
  px(ctx, fill, x + 2, y + 2, w - 4, h - 4);
  return { x, y, w, h };
}

function drawBoards(ctx: Ctx): void {
  // whiteboard (plan), marker tray
  const wb = frameRect(ctx, BOARDS.whiteboard, 4, C.frame, C.whiteboard);
  px(ctx, C.frame, wb.x + 6, wb.y + wb.h, wb.w - 12, 2);
  // evidence wall: cork board in a wooden frame
  const ev = frameRect(ctx, BOARDS.evidenceWall, 2, C.woodDark, C.cork);
  for (let i = 0; i < 90; i++) {
    const dx = (i * 37) % (ev.w - 6), dy = (i * 17) % (ev.h - 6);
    px(ctx, C.corkDot, ev.x + 3 + dx, ev.y + 3 + dy, 1, 1);
  }
  // RCA board: slate
  const rb = frameRect(ctx, BOARDS.rcaBoard, 4, C.woodDark, C.slate);
  px(ctx, C.slateHi, rb.x + 2, rb.y + 2, rb.w - 4, 2);
}

/** Woven rug in tile units: a border band, a stitched inner edge and a quiet weave. */
function drawRug(ctx: Ctx, r: Rect, body: string, band: string, stitch: string): void {
  const x = r.x * TILE, y = r.y * TILE, w = r.w * TILE, h = r.h * TILE;
  px(ctx, C.shadow, x + 1, y + 2, w, h);
  px(ctx, band, x, y, w, h);
  px(ctx, body, x + 4, y + 4, w - 8, h - 8);
  for (let i = x + 6; i < x + w - 6; i += 4) { px(ctx, stitch, i, y + 2, 2, 1); px(ctx, stitch, i, y + h - 3, 2, 1); }
  for (let j = y + 6; j < y + h - 6; j += 4) { px(ctx, stitch, x + 2, j, 1, 2); px(ctx, stitch, x + w - 3, j, 1, 2); }
  for (let j = y + 8; j < y + h - 8; j += 6) {
    for (let i = x + 8 + ((j / 6) % 2) * 3; i < x + w - 8; i += 6) px(ctx, band, i, j, 1, 1);
  }
}

function drawRugs(ctx: Ctx): void {
  drawRug(ctx, { x: 2, y: 3, w: 8, h: 5 }, "#c9ad86", "#a9875f", "#e2cfb1");        // Supervisor
  drawRug(ctx, { x: 31, y: 3, w: 8, h: 5 }, "#9fb0a6", "#7f9387", "#c4d2c9");       // RCA
  drawRug(ctx, { x: 2, y: 8, w: 33, h: 11 }, "#b3bdc7", "#95a1ad", "#cfd7de");      // bullpen
  drawRug(ctx, { x: 30, y: 19, w: 8, h: 4 }, "#c7a3a0", "#a88380", "#e2c8c6");      // your approval desk
}

function drawDesk(ctx: Ctx, r: Rect): void {
  const x = r.x * TILE, y = r.y * TILE, w = r.w * TILE, h = r.h * TILE;
  px(ctx, C.shadow, x + 2, y + h - 2, w, 4);
  px(ctx, C.outline, x - 1, y + 3, w + 2, h - 2);
  px(ctx, C.woodTop, x, y + 4, w, h - 9);
  px(ctx, C.woodTopHi, x, y + 4, w, 2);
  px(ctx, C.woodFront, x, y + h - 5, w, 4);
  px(ctx, C.woodDark, x, y + h - 2, w, 1);
  // keyboard + papers
  px(ctx, C.outline, x + 13, y + h - 13, 14, 5);
  px(ctx, C.keyboard, x + 14, y + h - 12, 12, 3);
  px(ctx, C.paper, x + w - 14, y + 9, 8, 10);
  px(ctx, "#d4cfc2", x + w - 13, y + 11, 6, 1);
  px(ctx, "#d4cfc2", x + w - 13, y + 13, 5, 1);
}

function drawChair(ctx: Ctx, cx: number, cy: number): void {
  const x = cx * TILE + 3, y = cy * TILE + 4;
  px(ctx, C.outline, x - 1, y - 1, 12, 12);
  px(ctx, C.chair, x, y, 10, 10);
  px(ctx, C.chairHi, x + 1, y + 1, 8, 3);
}

function drawProp(ctx: Ctx, sheet: CanvasImageSource, kind: string, cx: number, cy: number): void {
  const x = cx * TILE, y = cy * TILE;
  if (kind === "plant") {
    px(ctx, C.outline, x + 3, y + 10, 10, 6);
    px(ctx, "#a4623a", x + 4, y + 11, 8, 4);
    tile(ctx, sheet, T.bush, cx, cy - 0.35);
  } else if (kind === "shelf") {
    px(ctx, C.outline, x - 1, y - 9, TILE + 2, 25);
    px(ctx, C.woodDark, x, y - 8, TILE, 23);
    const spines = ["#b43c3c", "#2f5fb4", "#9a7418", "#2f7d4f", "#6f4fa8", "#c4621f"];
    for (let row = 0; row < 3; row++) {
      for (let i = 0; i < 4; i++) px(ctx, spines[(row * 4 + i + cx) % spines.length], x + 1 + i * 4, y - 7 + row * 7, 3, 6);
      px(ctx, C.woodFront, x, y - 1 + row * 7, TILE, 1);
    }
  } else if (kind === "crate") {
    px(ctx, C.outline, x + 1, y + 1, 14, 14);
    px(ctx, "#b07a45", x + 2, y + 2, 12, 12);
    px(ctx, "#8a5733", x + 2, y + 7, 12, 2);
    px(ctx, "#8a5733", x + 7, y + 2, 2, 12);
  } else if (kind === "cooler") {
    px(ctx, C.outline, x + 3, y - 10, 10, 26);
    px(ctx, "#8fc7e8", x + 4, y - 9, 8, 9);
    px(ctx, "#cfe8f5", x + 5, y - 8, 2, 6);
    px(ctx, "#dfe3e8", x + 4, y, 8, 15);
    px(ctx, "#2f5fb4", x + 7, y + 3, 2, 2);
    tile(ctx, sheet, T.waterBucket, cx - 1, cy);
  } else if (kind === "sign") {
    tile(ctx, sheet, T.sign, cx, cy);
  }
}

/** Paint the whole static floor; `sheet` is the loaded Tiny Town image. */
export function paintFloor(ctx: Ctx, sheet: CanvasImageSource): void {
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, COLS * TILE, ROWS * TILE);
  px(ctx, C.outline, 0, 0, COLS * TILE, ROWS * TILE);
  drawWalls(ctx, sheet);
  drawFloor(ctx, sheet);
  drawRugs(ctx);
  drawBoards(ctx);
  for (const d of DESKS) drawDesk(ctx, d.rect);
  for (const d of DESKS) drawChair(ctx, SPOTS[d.owner].seat.x, SPOTS[d.owner].seat.y);
  for (const p of PROPS) drawProp(ctx, sheet, p.kind, p.cell.x, p.cell.y);
}
