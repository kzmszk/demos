// node --test shared/move/walk.test.mjs — raster walking on small made-up walk maps (0.25 m cells, as venice's).
// glideStep with venice's body (radius 0.24 m, steps up / down to 0.55 m) against strictStep, the rule venice walked by
// before: a slanted calle, an opening, water (z null), a drop, and narrow decks with steps (strict passing ⇒ glide
// passing, so venice/tools/bridge_check.py, which checks the strict rule, still vouches for every bridge).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createState, step, rasterWalkMode, glideStep, strictStep } from './index.js';

const RES = 0.25;
// fn(x, y) at a cell's centre → { z } (z null: not walkable, as venice's walk map)
const raster = (fn) => ({ sample(x, y) { return fn((Math.floor(x / RES) + 0.5) * RES, (Math.floor(y / RES) + 0.5) * RES); } });
const VENICE = { radius: 0.24 };
const STRICT = strictStep({ ...VENICE, step: 0.55 }), GLIDE = glideStep({ ...VENICE, up: 0.55, down: 0.55 });
const cfgOf = (strategy) => ({ axes: 'zUp', modes: { walk: rasterWalkMode({ strategy, eye: 1.62, speed: 1.45, runSpeed: 3.6, smooth: 8, follow: 12, searchRadius: 4, bob: null }) } });

function walk(strategy, world, { x = 0, y = 0, yaw = 0, seconds = 6, dt = 1 / 60, onStep = null } = {}) {
  const s = createState({ mode: 'walk', pos: { x, y, z: 0 }, yaw }), cfg = cfgOf(strategy);
  for (let t = 0; t < seconds / dt; t++) { step(s, { f: 1, r: 0, u: 0, fast: false, yaw, pitch: 0 }, dt, world, cfg); if (onStep) onStep(s); }
  return s;
}

test('a calle slanted off the way: glide follows it, strict sticks in the stair-stepped walls', () => {
  // a 1.6 m street at 25° (water / houses either side), walked straight along x for 6 s (ideal 1.45·6·cos25° = 7.9 m)
  const A = 25 * Math.PI / 180, n = [-Math.sin(A), Math.cos(A)];
  const world = raster((x, y) => ({ z: Math.abs(x * n[0] + y * n[1]) < 0.8 ? 0.5 : null }));
  const along = (s) => s.pos.x * Math.cos(A) + s.pos.y * Math.sin(A);
  const g = walk(GLIDE, world), st = walk(STRICT, world);
  assert.ok(along(g) > 6, `glide went ${along(g).toFixed(2)} m along the street`);
  assert.ok(along(st) < 3, `strict went ${along(st).toFixed(2)} m (the case this change is for)`);
});

test('an opening 0.9 m wide, met a little off its middle: glide slips through, strict stops at the jamb', () => {
  const world = raster((x, y) => ({ z: x > 3 && x < 3.5 && Math.abs(y) > 0.45 ? null : 0.5 }));
  for (const off of [0.3, 0.6]) {
    assert.ok(walk(GLIDE, world, { y: off }).pos.x > 4, `glide stuck ${off} m off`);
    assert.ok(walk(STRICT, world, { y: off }).pos.x < 3.5, `strict got through ${off} m off`);
  }
});

test('water (z null) next to low ground is never entered, at any ground height', () => {
  for (const ground of [0.05, 0.3, 0.5, 1.0]) {
    const world = raster((x) => ({ z: x < 2 ? ground : null }));
    let worst = -Infinity;
    walk(GLIDE, world, { onStep: (s) => { worst = Math.max(worst, s.pos.x); } });
    assert.ok(worst < 2, `ground ${ground}: the walker's centre reached x ${worst.toFixed(3)} (water from x 2)`);
  }
});

test('a drop of more than 0.55 m stops the walk; a 0.5 m step down does not', () => {
  const at = (drop) => walk(GLIDE, raster((x) => ({ z: x < 3 ? 2 : 2 - drop }))).pos.x;
  assert.ok(at(0.8) < 3, 'stepped off 0.8 m');
  assert.ok(at(0.5) > 5, 'did not take a 0.5 m step down');
});

test('narrow decks with steps: wherever strict gets across, glide gets across too', () => {
  // decks along x, width 0.6–1.2 m, water either side, a few steps of 0–0.7 m (a fixed pseudo-random series)
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  let both = 0;
  for (let n = 0; n < 40; n++) {
    const width = 0.6 + rnd() * 0.6, steps = [2, 4, 6, 8].map(() => (rnd() < 0.5 ? 0 : rnd() * 0.7)), skew = (rnd() - 0.5) * 0.3;
    const z = (x) => { let h = 0.5; for (let i = 0; i < 4; i++) if (x > 2 + 2 * i) h += steps[i]; return h; };
    const world = raster((x, y) => ({ z: x < -1 || x > 13 || Math.abs(y - skew * x) > width / 2 ? null : z(x) }));
    const yaw = Math.atan(skew);
    const s = walk(STRICT, world, { yaw, seconds: 14 }).pos.x, g = walk(GLIDE, world, { yaw, seconds: 14 }).pos.x;
    if (s > 11) { both++; assert.ok(g > 11, `deck ${n}: strict reached x ${s.toFixed(2)}, glide only ${g.toFixed(2)}`); }
  }
  assert.ok(both >= 8, `only ${both} decks were crossable by strict: the test proves little`);
});
