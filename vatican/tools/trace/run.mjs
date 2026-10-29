// Movement trace (proposal §4.0, comparison A): drives web/fly.js through real listeners with trace/script.mjs and
// writes the sampled state sequence as JSON.
//   node trace/run.mjs [--orig] [out.json]     (default: web/fly.js → trace/out.json)
//   node trace/compare.mjs trace/golden.json trace/out.json
// --orig drives trace/fly.orig.js, a byte-for-byte copy of web/fly.js before the shared/move migration (the
// hand-written FlyControls); trace/golden.json is recorded from it and kept as the reference.  When the controls
// are a shared/move Mover, the run also records the {dt, cmds, frame} log, sends it through JSON, replays it on the
// pure core (command/step) and checks that the replay lands on the same positions.
import './three-hook.mjs';
import { writeFileSync } from 'node:fs';

const args = process.argv.slice(2), orig = args.includes('--orig');
const { FakeTarget, FakeCamera, installWindow, event } = await import('./fake.mjs');
const { makeApp } = await import('./app.mjs');
const { SCRIPT } = await import('./script.mjs');
const { FlyControls } = await import(orig ? './fly.orig.js' : '../web/fly.js');

const out = args.find((a) => !a.startsWith('--')) || new URL(orig ? './golden.json' : './out.json', import.meta.url).pathname;
const win = installWindow(), canvas = new FakeTarget(), camera = new FakeCamera();
const app = makeApp({ win, camera, createControls: () => new FlyControls(camera, canvas) });
const c = app.controls;
const rec = typeof c.startRecording === 'function' ? c.startRecording() : null, ticks = [];

const samples = [];
let label = '';
const v3 = (v) => [v.x, v.y, v.z];
const sample = (op) => samples.push({ n: samples.length, label, op, mode: app.mode, enabled: c.enabled,
  pos: v3(camera.position), dir: v3(camera.dir), yaw: c.yaw, pitch: c.pitch, vel: v3(c.vel), speed: c.speed });

for (const op of SCRIPT) {
  const [type, ...a] = op;
  if (type === 'label') { label = a[0]; continue; }
  if (type === 'step') {
    for (let i = 0; i < a[0]; i++) {
      app.step(a[1]);
      if (app.mode === 'free') ticks.push(v3(camera.position));
      sample(`step ${a[1].toPrecision(4)}`);
    }
    continue;
  }
  if (type === 'keydown' || type === 'keyup') win.dispatchEvent(event(type, { code: a[0], key: a[0] }));
  else if (type.startsWith('pointer')) {
    const [x, y, o] = a;
    canvas.dispatchEvent(event(type, { clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse', button: 0, ...o }));
  } else if (type === 'wheel') canvas.dispatchEvent(event('wheel', { deltaY: a[0] }));
  else if (type === 'free') app.setMode('free');
  else if (type === 'look') app.look(a[0], a[1]);
  else if (type === 'stopLoop') app.stopLoop();
  else throw new Error('unknown op ' + type);
  sample(op.map((x) => (typeof x === 'object' ? JSON.stringify(x) : x)).join(' '));
}

const impl = rec ? 'shared/move Mover' : 'hand-written FlyControls';
writeFileSync(out, JSON.stringify({ impl, ops: SCRIPT.length, samples }, null, 0).replace(/\},\{/g, '},\n{') + '\n');
console.log(`${impl}: ${samples.length} samples → ${out}`);

if (rec) {
  // replay the recorded ticks on the pure core, after a round trip through JSON
  const { fromPlain, command, step } = await import('../../../shared/move/index.js');
  const log = JSON.parse(JSON.stringify(rec));
  if (log.ticks.length !== ticks.length) throw new Error(`replay: ${log.ticks.length} ticks recorded, ${ticks.length} updates run`);
  const s = fromPlain(log.initial);
  let worst = 0;
  log.ticks.forEach((t, i) => {
    for (const cmd of t.cmds) command(s, cmd, c.world, c.cfg);
    if (t.frame) step(s, t.frame, t.dt, c.world, c.cfg);
    worst = Math.max(worst, ...[s.pos.x, s.pos.y, s.pos.z].map((v, j) => Math.abs(v - ticks[i][j])));
  });
  console.log(`replay of ${log.ticks.length} ticks on the core: max |Δpos| = ${worst.toExponential(2)}`);
  if (!(worst <= 1e-6)) { console.error('replay does not match'); process.exitCode = 1; }
}
