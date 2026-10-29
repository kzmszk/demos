// node --test shared/move/move.test.mjs   (a bare directory runs as one script on node 24, not these tests; proposal §4.0 "shared/move/ の最初の中身")
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  MOVE_SCHEMA, createState, toPlain, fromPlain, step, command, flyMode, Input, DRAG_SIGN, zUpView, Mover, AXES,
} from './index.js';

const near = (a, b, e = 1e-12) => assert.ok(Math.abs(a - b) <= e, `${a} ≉ ${b}`);
const ev = (type, props = {}) => Object.assign(new Event(type, { cancelable: true }), props);
class Target extends EventTarget { setPointerCapture() {} }
class Cam {
  constructor() { this.position = { x: 0, y: 0, z: 0, set(x, y, z) { this.x = x; this.y = y; this.z = z; } }; this.dir = { x: 1, y: 0, z: 0 }; this.up = { set() { throw new Error('up touched'); } }; }
  lookAt(x, y, z) { const p = this.position, d = [x - p.x, y - p.y, z - p.z], l = Math.hypot(...d); this.dir = { x: d[0] / l, y: d[1] / l, z: d[2] / l }; }
}
const BIND = { forward: ['KeyW'], back: ['KeyS'], left: ['KeyA'], right: ['KeyD'], up: ['KeyE'], down: ['KeyQ'], fast: ['ShiftLeft'], turnLeft: ['ArrowLeft'], turnRight: ['ArrowRight'] };
function rig(opts = {}) {
  const win = new Target(), dom = new Target(), cam = new Cam();
  const m = new Mover({ win, dom, view: zUpView(cam, { readDir: (c) => c.dir, setUp: false }), mode: 'fly', speed: 10,
    speedRange: [2, 400], modes: { fly: flyMode({ smooth: 3 }), ...opts.modes }, input: { bindings: BIND, ...opts.input }, migration: opts.migration });
  const key = (t, code) => win.dispatchEvent(ev(t, { code, key: code }));
  const ptr = (t, x, y, o = {}) => dom.dispatchEvent(ev(t, { clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse', button: 0, ...o }));
  return { win, dom, cam, m, key, ptr };
}

test('DRAG_SIGN is +1 (grab the scene, owner decision ②)', () => assert.equal(DRAG_SIGN, 1));

// Keys bound to one action OR together under both modes (W+↑ is 1, as in alhambra main.js:177); 'sum' only differs
// once a stick adds to the key axis, which Input does not take yet.
test('compose: keys bound to one action count once, opposite keys cancel', () => {
  for (const compose of ['clampEach', 'sum']) {
    const win = new Target(), inp = new Input({ win, dom: new Target(), options: { compose, bindings: { forward: ['KeyW', 'ArrowUp'], back: ['KeyS'] } }, hooks: { enabled: () => true } });
    win.dispatchEvent(ev('keydown', { code: 'KeyW' })); win.dispatchEvent(ev('keydown', { code: 'ArrowUp' }));
    assert.equal(inp.read(1 / 60).f, 1, compose);
    win.dispatchEvent(ev('keydown', { code: 'KeyS' }));
    assert.equal(inp.read(1 / 60).f, 0, compose);
  }
});

test('blur and resetInput release keys and the drag; keyup over a text field still lifts', () => {
  const { win, m, key, ptr } = rig();
  key('keydown', 'KeyW'); ptr('pointerdown', 0, 0);
  win.dispatchEvent(ev('blur'));
  assert.equal(m.keys.size, 0); assert.equal(m.input.drag, null);
  key('keydown', 'KeyW'); m.resetInput(); assert.equal(m.keys.size, 0);
  const inField = (type) => { const e = ev(type, { code: 'KeyS' }); Object.defineProperty(e, 'target', { value: { tagName: 'INPUT' } }); win.dispatchEvent(e); };
  inField('keydown'); assert.equal(m.keys.size, 0, 'keydown in a text field is ignored');
  key('keydown', 'KeyS'); inField('keyup'); assert.equal(m.keys.size, 0, 'keyup in a text field still lifts');
});

test('zUp view: forward/right in the four directions and apply → read round trip', () => {
  const ax = AXES.zUp;
  for (const [yaw, fw, rt] of [[0, [1, 0], [0, -1]], [Math.PI / 2, [0, 1], [1, 0]], [Math.PI, [-1, 0], [0, 1]], [-Math.PI / 2, [0, -1], [-1, 0]]]) {
    ax.forward(yaw).forEach((v, i) => near(v, fw[i])); ax.right(yaw).forEach((v, i) => near(v, rt[i]));
    const cam = new Cam(), v = zUpView(cam, { readDir: (c) => c.dir, setUp: false }), s = createState({ pos: { x: 3, y: -4, z: 5 }, yaw, pitch: 0.3 });
    v.apply(s); const r = v.read();
    near(r.pos.x, 3); near(r.pos.y, -4); near(r.pos.z, 5); near(Math.cos(r.yaw), Math.cos(yaw)); near(Math.sin(r.yaw), Math.sin(yaw)); near(r.pitch, 0.3);
  }
});

test('fly: smooth lerps, smooth:null takes want at once, fast multiplies', () => {
  const cfg = (m) => ({ axes: 'zUp', modes: { fly: m } });
  const frame = { f: 1, r: 0, u: 1, fast: false, yaw: 0, pitch: 0 };
  const a = createState({ speed: 10 }); step(a, frame, 0.5, {}, cfg(flyMode({ smooth: null })));
  near(a.vel.x, 10); near(a.vel.z, 10); near(a.pos.x, 5);
  const b = createState({ speed: 10 }); step(b, { ...frame, fast: true }, 0.5, {}, cfg(flyMode({ smooth: 3 })));
  near(b.vel.x, 40 * (1 - Math.exp(-1.5))); near(b.pos.x, b.vel.x * 0.5);
  const c = createState({ speed: 10 }); step(c, { ...frame, r: 1 }, 1, {}, cfg(flyMode({ smooth: null, normalizeXY: true })));
  near(Math.hypot(c.vel.x, c.vel.y), 10);
  assert.throws(() => flyMode({ followPitch: true }));
});

test('wheel: queues setSpeed (clamped), works while disabled, wheel.modes limits it', () => {
  const { dom, m } = rig({ input: { wheel: { min: 2, max: 400, modes: null } } });
  m.enabled = false;
  dom.dispatchEvent(ev('wheel', { deltaY: 1 }));
  near(m.speed, 8.5); near(m.state.speed, 10);
  for (let i = 0; i < 40; i++) dom.dispatchEvent(ev('wheel', { deltaY: 1 }));
  assert.equal(m.speed, 2);
  m.update(1 / 60); assert.equal(m.state.speed, 2);
  const w = ev('wheel', { deltaY: -1 }); dom.dispatchEvent(w); assert.ok(w.defaultPrevented);
  const r2 = rig({ input: { wheel: { modes: ['walk'] } } }), w2 = ev('wheel', { deltaY: 1 });
  r2.dom.dispatchEvent(w2); assert.equal(r2.m.speed, 10); assert.ok(!w2.defaultPrevented);
  assert.equal(command(createState(), { type: 'setSpeed', value: 1e9 }, {}, { speedRange: [2, 400] }).speed, 400);
  assert.throws(() => command(createState(), { type: 'setSpeed', value: NaN }, {}, {}));
});

test('drag: sign, coefficient, per-event pitch clamp, ignored while disabled (origin kept)', () => {
  const { m, ptr } = rig({ input: { drag: { mouse: 0.01, touch: 0.02, pitchLimit: 1 } } });
  m.yaw = 0; m.pitch = 0;
  ptr('pointerdown', 0, 0); ptr('pointermove', 10, 0);
  near(m.yaw, 0.1, 1e-15);                    // right drag → yaw grows (turns left)
  ptr('pointermove', 10, 200); assert.equal(m.pitch, 1);   // down 2 rad → clamped at +1 (looks up)
  ptr('pointermove', 10, 150); near(m.pitch, 0.5);         // and back: clamped per event, not once per frame
  m.enabled = false; ptr('pointermove', 50, 150); near(m.yaw, 0.1);
  m.enabled = true; ptr('pointermove', 60, 150); near(m.yaw, 0.6);         // resumes from the old point (10, 150)
  ptr('pointermove', 70, 150, { pointerId: 2 }); near(m.yaw, 0.6);         // other pointers are ignored
  ptr('pointerup', 70, 150); ptr('pointerdown', 0, 0, { pointerType: 'touch' }); ptr('pointermove', 10, 0, { pointerType: 'touch' });
  near(m.yaw, 0.8);
  const old = rig({ migration: { dragSign: -1 }, input: { drag: { mouse: 0.01 } } });
  old.m.yaw = 0; old.ptr('pointerdown', 0, 0); old.ptr('pointermove', 10, 0); near(old.m.yaw, -0.1, 1e-15);
});

test('client-only modes get look (signed, scaled) and wheel; enter/exit on setMode', () => {
  const seen = [];
  const boat = { enter: (ctx, prev) => seen.push(['enter', prev]), exit: () => seen.push(['exit']), update: () => seen.push(['update']),
    look: (dx, dy) => seen.push(['look', dx, dy]), wheel: () => seen.push(['wheel']) };
  const { dom, m, ptr } = rig({ modes: { boat }, input: { drag: { mouse: 0.01 } } });
  const yaw0 = m.yaw;
  m.setMode('boat'); m.update(1 / 60);
  ptr('pointerdown', 0, 0); ptr('pointermove', 10, -10); dom.dispatchEvent(ev('wheel', { deltaY: 1 }));
  m.update(1 / 60); m.setMode('fly'); m.update(1 / 60);
  assert.deepEqual(seen.map((s) => s[0]), ['enter', 'update', 'look', 'wheel', 'update', 'exit']);
  near(seen[2][1], 0.1); near(seen[2][2], -0.1); assert.equal(m.yaw, yaw0); assert.equal(m.speed, 10);
});

test('turn keys: rad/s by default, per frame under migration.turnPerFrame', () => {
  const a = rig({ input: { turnRate: 1.5 } }); a.m.yaw = 0; a.key('keydown', 'ArrowLeft'); a.m.update(0.5); near(a.m.yaw, 0.75);
  const b = rig({ migration: { turnPerFrame: 0.025 } }); b.m.yaw = 0; b.key('keydown', 'ArrowRight'); b.m.update(0.5); near(b.m.yaw, -0.025);
  b.m.enabled = false; b.m.update(0.5); near(b.m.yaw, -0.025);
});

test('toPlain / fromPlain through JSON and structured clone; rejects non-finite, stray null, other schema', () => {
  const s = createState({ pos: { x: 1, y: 2, z: 3 }, yaw: 0.5, speed: 25 }); s.vel.set(1, -2, 0.5);
  for (const copy of [JSON.parse(JSON.stringify(toPlain(s))), structuredClone(toPlain(s))]) {
    const t = fromPlain(copy); assert.deepEqual(toPlain(t), toPlain(s)); t.vel.lerp({ x: 0, y: 0, z: 0 }, 1); assert.equal(t.vel.x, 0);
  }
  const bad = (f) => { const p = toPlain(s); f(p); assert.throws(() => fromPlain(JSON.parse(JSON.stringify(p)))); };
  bad((p) => { p.pos.x = NaN; }); bad((p) => { p.vel.y = Infinity; }); bad((p) => { p.speed = null; }); bad((p) => { p.v = MOVE_SCHEMA + 1; });
  const w = toPlain(s); w.walk.z = null; assert.equal(fromPlain(w).walk.z, null);
});

test('core sources use no three / DOM / time / randomness', () => {
  for (const f of ['state.js', 'step.js', 'vec.js', 'fly.js']) {
    const src = readFileSync(new URL('./' + f, import.meta.url), 'utf8').replace(/\/\/.*$/gm, '');
    for (const bad of [/['"]three/, /\bdocument\b/, /\bwindow\b/, /\bperformance\b/, /\bDate\b/, /Math\.random/, /globalThis/]) assert.ok(!bad.test(src), `${f} uses ${bad}`);
    assert.ok(!/^(let|var)\s/m.test(src), `${f} has module-level mutable state`);
  }
});

test('the same step on N states: no cross-talk, identical inputs give identical states', () => {
  const cfg = { axes: 'zUp', modes: { fly: flyMode({ smooth: 3 }) } };
  const states = Array.from({ length: 4 }, (_, i) => createState({ speed: 10 + i }));
  const twin = fromPlain(toPlain(states[0]));
  for (let t = 0; t < 100; t++) for (const [i, s] of states.entries()) step(s, { f: 1, r: i % 2, u: 0, fast: false, yaw: 0.01 * t, pitch: 0 }, 1 / 60, {}, cfg);
  for (let t = 0; t < 100; t++) step(twin, { f: 1, r: 0, u: 0, fast: false, yaw: 0.01 * t, pitch: 0 }, 1 / 60, {}, cfg);
  assert.deepEqual(toPlain(twin), toPlain(states[0]));
  assert.notDeepEqual(toPlain(states[1]), toPlain(states[2]));
});

test('Mover: replaying the tick log on the core reproduces the camera path', () => {
  const { cam, m, key, ptr } = rig({ migration: { dragSign: -1 } });
  const rec = m.startRecording(), path = [];
  m.syncFromCamera(); key('keydown', 'KeyW');
  for (let i = 0; i < 60; i++) { if (i === 20) { ptr('pointerdown', 0, 0); ptr('pointermove', 30, 10); } if (i === 30) cam.position.set(5, 5, 5); m.update(1 / 60); path.push({ ...cam.position }); }
  const log = JSON.parse(JSON.stringify(rec)), s = fromPlain(log.initial);
  log.ticks.forEach((t, i) => { for (const c of t.cmds) command(s, c, m.world, m.cfg); if (t.frame) step(s, t.frame, t.dt, m.world, m.cfg); near(s.pos.x, path[i].x); near(s.pos.y, path[i].y); near(s.pos.z, path[i].z); });
});
