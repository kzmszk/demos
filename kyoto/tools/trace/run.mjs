// Movement trace (proposal §4.0, comparison A): drives web/controls.js through real listeners with trace/script.mjs on
// the synthetic world (trace/world.mjs) and writes the sampled state sequence as JSON.
//   node trace/run.mjs [--orig] [out.json]     (default: web/controls.js → trace/out.json)
//   node trace/compare.mjs trace/golden.json trace/out.json
// --orig drives trace/controls.orig.js, a byte-for-byte copy of web/controls.js before the shared/move migration;
// trace/golden.json is recorded from it and kept as the reference.  When the controls are a shared/move Mover, the
// run also records the {dt, cmds, frame} log, sends it through JSON, replays it on the pure core (command/step) on a
// fresh world that follows the same script, and checks that the replay lands on the same positions.
import './three-hook.mjs';
import { writeFileSync } from 'node:fs';

const args = process.argv.slice(2), orig = args.includes('--orig');
const { FakeTarget, FakeCamera, installWindow, event } = await import('./fake.mjs');
const { makeApp } = await import('./app.mjs');
const { makeWorld } = await import('./world.mjs');
const { SCRIPT } = await import('./script.mjs');
const { Controls } = await import(orig ? './controls.orig.js' : '../web/controls.js');

const out = args.find((a) => !a.startsWith('--')) || new URL(orig ? './golden.json' : './out.json', import.meta.url).pathname;
const win = installWindow(), canvas = new FakeTarget(), camera = new FakeCamera(), world = makeWorld();
const A = makeApp({ camera, tiles: world, ground: world.farGround,
  createControls: () => new Controls(camera, canvas, { tiles: world, ground: world.farGround }) });
const c = A.controls;
const rec = typeof c.startRecording === 'function' ? c.startRecording() : null, ticks = [];

const samples = [];
let label = '';
const v3 = (v) => [v.x, v.y, v.z];
const sample = (op) => samples.push({ n: samples.length, label, op, mode: A.app.mode, cmode: c.mode, enabled: c.enabled,
  pos: v3(camera.position), dir: v3(camera.dir), yaw: c.yaw, pitch: c.pitch, vel: v3(c.vel), speed: c.speed, walkZ: c.walkZ });

for (const op of SCRIPT) {
  const [type, ...a] = op;
  if (type === 'label') { label = a[0]; continue; }
  if (type === 'step') {
    for (let i = 0; i < a[0]; i++) {
      A.step(a[1]);
      if (A.app.mode !== 'title') ticks.push({ pos: v3(camera.position), gate: world.gate, late: world.late });
      sample(`step ${a[1].toPrecision(4)}`);
    }
    continue;
  }
  if (type === 'keydown' || type === 'keyup') win.dispatchEvent(event(type, { code: a[0], key: a[0] }));
  else if (type === 'blur') win.dispatchEvent(event('blur'));
  else if (type.startsWith('pointer')) {
    const [x, y, o] = a;
    canvas.dispatchEvent(event(type, { clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse', button: 0, ...o }));
  } else if (type === 'wheel') canvas.dispatchEvent(event('wheel', { deltaY: a[0] }));
  else if (type === 'gate' || type === 'late') world[type] = a[0];
  else if (type === 'start') A.start(a[0]);
  else if (type === 'stick') A.stick(a[0], a[1]);
  else if (type === 'fast') A.fastToggle();
  else if (typeof A[type] === 'function') A[type](...a);
  else throw new Error('unknown op ' + type);
  sample(op.map((x) => (typeof x === 'object' ? JSON.stringify(x) : x)).join(' '));
}

const impl = rec ? 'shared/move Mover' : 'hand-written Controls';
writeFileSync(out, JSON.stringify({ impl, ops: SCRIPT.length, samples }, null, 0).replace(/\},\{/g, '},\n{') + '\n');
console.log(`${impl}: ${samples.length} samples → ${out}`);

if (rec) {
  // replay the recorded ticks on the pure core, after a round trip through JSON; the world's switches are set as they
  // were at each tick
  const { fromPlain, command, step } = await import('../../../shared/move/index.js');
  const log = JSON.parse(JSON.stringify(rec)), w2 = makeWorld();
  const cw = { sample: (x, y) => w2.sample(x, y), ground: (x, y) => { const s = w2.sample(x, y); return s.z !== undefined ? s.z : w2.farGround(x, y); } };
  if (log.ticks.length !== ticks.length) throw new Error(`replay: ${log.ticks.length} ticks recorded, ${ticks.length} updates run`);
  const s = fromPlain(log.initial);
  let worst = 0;
  log.ticks.forEach((t, i) => {
    w2.gate = ticks[i].gate; w2.late = ticks[i].late;
    for (const cmd of t.cmds) command(s, cmd, cw, c.cfg);
    if (t.frame) step(s, t.frame, t.dt, cw, c.cfg);
    if (s.status === 'hold') return;
    worst = Math.max(worst, ...[s.pos.x, s.pos.y, s.pos.z].map((v, j) => Math.abs(v - ticks[i].pos[j])));
  });
  console.log(`replay of ${log.ticks.length} ticks on the core: max |Δpos| = ${worst.toExponential(2)}`);
  if (!(worst <= 1e-6)) { console.error('replay does not match'); process.exitCode = 1; }
}
