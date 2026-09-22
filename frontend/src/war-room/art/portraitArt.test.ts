import { expect, test } from "vitest";
import { PERSONAS, type Persona } from "../personas";
import { PORTRAIT_H, PORTRAIT_W, SCENE_H, SCENE_W, portraitBuf, sceneFrames } from "./portraitArt";

const personas = Object.keys(PERSONAS) as Persona[];

test("every persona has a portrait and front/back walk frames of the right size", () => {
  for (const p of personas) {
    expect(portraitBuf(p).length).toBe(PORTRAIT_W * PORTRAIT_H * 4);
    const frames = sceneFrames(p);
    expect(frames.front).toHaveLength(3);
    expect(frames.back).toHaveLength(3);
    for (const f of [...frames.front, ...frames.back]) expect(f.length).toBe(SCENE_W * SCENE_H * 4);
  }
});

test("sprites are drawn (not empty) and every persona looks different", () => {
  const signatures = new Set<string>();
  for (const p of personas) {
    const buf = sceneFrames(p).front[0];
    let opaque = 0;
    for (let i = 3; i < buf.length; i += 4) if (buf[i] === 255) opaque++;
    expect(opaque).toBeGreaterThan(150);
    signatures.add(Array.from(buf).join(","));
  }
  expect(signatures.size).toBe(personas.length);
});

test("walk phases differ so the gait animates", () => {
  const { front } = sceneFrames("code");
  expect(Array.from(front[1]).join()).not.toBe(Array.from(front[2]).join());
});
